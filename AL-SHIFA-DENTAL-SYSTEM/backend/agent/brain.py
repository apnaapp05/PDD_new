from sqlalchemy.orm import Session
import pandas as pd
from rapidfuzz import process, fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import re

# Internal Services
from services.appointment_service import AppointmentService
from services.analytics_service import AnalyticsService
from services.inventory_service import InventoryService
from services.treatment_service import TreatmentService
from services.patient_service import PatientService
from services.clinical_service import ClinicalService
from services.settings_service import SettingsService
from agent.analyst import AnalystEngine
from services.response_generator import ResponseGenerator
from utils.nlp_parser import DateParser
from utils.smart_parser import SmartParser
from agent.intents import INTENT_TRAINING_DATA

class ClinicAgent:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id
        
        # --- 1. LOAD TOOLS (Services) ---
        self.appt = AppointmentService(db, doctor_id)
        self.fin = AnalyticsService(db, doctor_id)
        self.inv = InventoryService(db, doctor_id)
        self.pat = PatientService(db, doctor_id)
        self.treat = TreatmentService(db, doctor_id)
        self.clinical = ClinicalService(db, doctor_id)
        self.settings = SettingsService(db, doctor_id)
        self.analyst = AnalystEngine(db, doctor_id)
        
        # --- 2. AI MODELS (The Artificial LLM) ---
        self.parser = SmartParser()
        self.vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        self.intent_keys = []
        self._train_intent_model()
        
        # --- 3. CONTEXT MEMORY (For Multi-Turn Checklists) ---
        self.context = {
            "intent": None,
            "slots": {}, 
            "last_patient": None
        }

    def _train_intent_model(self):
        """Trains the local intent classifier on startup"""
        corpus = []
        for intent, phrases in INTENT_TRAINING_DATA.items():
            for p in phrases:
                corpus.append(p)
                self.intent_keys.append(intent)
        if corpus:
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def predict_intent(self, query):
        """Uses Cosine Similarity to find the best intent match"""
        if not self.intent_keys: return None
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)
        best_idx = similarities.argmax()
        if similarities[0, best_idx] < 0.35: return None
        return self.intent_keys[best_idx]

    def process(self, query: str):
        q = query.lower().strip()
        
        # --- A. ANALYST ENGINE (Pandas Logic) ---
        if self.analyst.is_analysis_query(q):
            return ResponseGenerator.simple(f"📊 **Analysis:**\n{self.analyst.analyze(q)}")

        # --- B. INTENT DETECTION ---
        # If we are in a checklist flow (e.g. asking for price), stick to that intent
        if self.context["intent"]:
            intent = self.context["intent"]
        else:
            intent = self.predict_intent(q)

        if not intent:
            return ResponseGenerator.simple("I'm not sure I understand. Try 'Dashboard', 'Schedule', or 'Update Price'.")

        try:
            # =======================================================
            # 1. NEW FEATURES (Treatment & Inventory Creation)
            # =======================================================
            
            # --- TREATMENT UPDATE ---
            if intent == "treatment_update":
                self.context["intent"] = "treatment_update"
                slots = self.context["slots"]
                
                # Check Treatment Name
                if not slots.get("name"):
                    all_treats = self.treat.get_all_treatments()
                    names = [t.name for t in all_treats]
                    match = process.extractOne(q, names, scorer=fuzz.token_set_ratio)
                    
                    if match and match[1] > 65 and "update" not in q:
                        slots["name"] = match[0]
                    else:
                        return {
                            "text": "Which treatment needs a price update?",
                            "buttons": [{"label": n, "action": n, "type": "chat"} for n in names[:5]]
                        }

                # Check Price
                if not slots.get("price"):
                    nums = re.findall(r'\d+', q)
                    if nums:
                        slots["price"] = float(nums[0])
                    else:
                        return ResponseGenerator.simple(f"What is the new price for **{slots['name']}**?")

                # Execute
                updated = self.treat.update_price(slots["name"], slots["price"])
                self.context["intent"] = None
                self.context["slots"] = {}
                if updated:
                    return ResponseGenerator.simple(f"✅ Updated **{updated.name}** to **Rs. {updated.cost}**.")
                return ResponseGenerator.error("Could not find that treatment.")

            # --- NEW INVENTORY ITEM ---
            if intent == "inventory_create":
                self.context["intent"] = "inventory_create"
                slots = self.context["slots"]

                # Check Name
                if not slots.get("name"):
                    clean = q.replace("create item", "").replace("new item", "").strip()
                    if len(clean) > 2 and clean != "new item":
                        slots["name"] = clean
                    else:
                        return ResponseGenerator.simple("What is the name of the new item?")

                # Check Quantity
                if not slots.get("quantity"):
                    nums = re.findall(r'\d+', q)
                    if nums:
                        slots["quantity"] = int(nums[0])
                    else:
                        return ResponseGenerator.simple(f"How much initial stock for **{slots['name']}**?")

                # Execute
                created = self.inv.create_item(slots["name"], slots["quantity"])
                self.context["intent"] = None
                self.context["slots"] = {}
                if created:
                    return ResponseGenerator.simple(f"✅ Created **{created.name}** with **{created.quantity}** units.")
                return ResponseGenerator.error(f"Item **{slots['name']}** already exists.")

            # =======================================================
            # 2. EXISTING FEATURES (Preserved from Manual/Old Logic)
            # =======================================================

            # --- DASHBOARD ---
            if intent == "dashboard_stats":
                fin_data = self.fin.get_financial_summary("today")
                inv_items = self.inv.get_low_stock()
                return ResponseGenerator.simple(f"📊 **Overview:**\nRevenue Today: {fin_data['revenue']}\nLow Stock Alerts: {len(inv_items)}")

            # --- SCHEDULE VIEW ---
            if intent == "schedule_view":
                date_str, _ = DateParser.parse_datetime(q)
                appts = self.appt.get_schedule(date_str)
                if not appts: return ResponseGenerator.simple(f"📅 No appointments found for {date_str}.")
                return ResponseGenerator.success_schedule(appts, date_str)

            # --- SCHEDULE BLOCKING ---
            if intent == "schedule_block":
                date_str, time_str = DateParser.parse_datetime(q)
                if not time_str: return ResponseGenerator.simple("Please specify a time to block.")
                self.appt.block_slot(date_str, time_str, "Doctor Blocked")
                return ResponseGenerator.simple(f"🚫 Blocked slot on {date_str} at {time_str}.")

            # --- INVENTORY CHECK ---
            if intent == "inventory_check":
                low_stock = self.inv.get_low_stock()
                if not low_stock: return ResponseGenerator.simple("✅ Inventory looks good. No low stock items.")
                items = ", ".join([i.name for i in low_stock])
                return ResponseGenerator.simple(f"⚠️ **Low Stock:** {items}")

            # --- INVENTORY ADD STOCK ---
            if intent == "inventory_add":
                # Simple one-shot extraction for adding stock
                # Assumes "Add 50 masks" format
                nums = re.findall(r'\d+', q)
                qty = int(nums[0]) if nums else 10
                
                all_items = self.inv.get_all_items()
                names = [i.name for i in all_items]
                match = process.extractOne(q, names, scorer=fuzz.partial_ratio)
                
                if match and match[1] > 60:
                    updated = self.inv.update_stock(match[0], qty)
                    return ResponseGenerator.simple(f"✅ Added {qty} to **{match[0]}**. New Total: {updated.quantity}")
                return ResponseGenerator.simple("Which item should I add stock to?")

            # --- FINANCE VIEW ---
            if intent == "finance_view":
                period = "week" if "week" in q else "today"
                data = self.fin.get_financial_summary(period)
                return ResponseGenerator.simple(f"💰 **Financials ({period}):**\nRevenue: {data['revenue']}\nPending: {data['pending']}")

            # --- PATIENT SEARCH ---
            if intent == "patient_search":
                clean = q.replace("search patient", "").replace("who is", "").strip()
                p = self.pat.find_patient(clean)
                if p:
                    self.context["last_patient"] = p.user.full_name
                    return ResponseGenerator.simple(f"👤 **Found Patient:**\nName: {p.user.full_name}\nPhone: {p.user.phone_number}\nLast Visit: {p.last_visit_date or 'N/A'}")
                return ResponseGenerator.error("Patient not found.")

            # --- SETTINGS (Availability) ---
            if intent == "settings_availability":
                # Assuming format "from 10:00 to 18:00"
                times = re.findall(r'\d{1,2}:\d{2}', q)
                if len(times) >= 2:
                    self.settings.update_working_hours(times[0], times[1])
                    return ResponseGenerator.simple(f"⏰ Availability updated: {times[0]} - {times[1]}")
                return ResponseGenerator.simple("Please specify start and end times (e.g., 09:00 to 17:00).")

            return ResponseGenerator.simple(f"I understood '{intent}' but need more details to proceed.")

        except Exception as e:
            self.context["intent"] = None
            return ResponseGenerator.error(f"Error: {str(e)}")
