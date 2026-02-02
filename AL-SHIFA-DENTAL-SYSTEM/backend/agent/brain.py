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
        
        # Tools
        self.appt = AppointmentService(db, doctor_id)
        self.fin = AnalyticsService(db, doctor_id)
        self.inv = InventoryService(db, doctor_id)
        self.pat = PatientService(db, doctor_id)
        self.treat = TreatmentService(db, doctor_id)
        self.clinical = ClinicalService(db, doctor_id)
        self.settings = SettingsService(db, doctor_id)
        self.analyst = AnalystEngine(db, doctor_id)
        
        # AI Components
        self.parser = SmartParser()
        self.vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        self.intent_keys = []
        self._train_intent_model()
        
        self.context = {
            "intent": None,
            "slots": {}, 
            "last_patient": None
        }

    def _train_intent_model(self):
        corpus = []
        for intent, phrases in INTENT_TRAINING_DATA.items():
            for p in phrases:
                corpus.append(p)
                self.intent_keys.append(intent)
        if corpus:
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def predict_intent(self, query):
        if not self.intent_keys: return None
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)
        best_idx = similarities.argmax()
        if similarities[0, best_idx] < 0.35: return None
        return self.intent_keys[best_idx]

    def process(self, query: str):
        q = query.lower().strip()
        
        # 1. Analyst Check
        if self.analyst.is_analysis_query(q):
            return ResponseGenerator.simple(f"📊 **Analysis:**\n{self.analyst.analyze(q)}")

        # 2. Intent Detection
        if self.context["intent"]:
            intent = self.context["intent"]
        else:
            intent = self.predict_intent(q)

        if not intent:
            return ResponseGenerator.simple("I'm not sure. Try 'Dashboard', 'Schedule', or 'Update Price'.")

        try:
            # --- FEATURE: TREATMENT UPDATE ---
            if intent == "treatment_update":
                self.context["intent"] = "treatment_update"
                slots = self.context["slots"]
                
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

                if not slots.get("price"):
                    nums = re.findall(r'\d+', q)
                    if nums: slots["price"] = float(nums[0])
                    else: return ResponseGenerator.simple(f"What is the new price for **{slots['name']}**?")

                updated = self.treat.update_price(slots["name"], slots["price"])
                self.context["intent"] = None
                self.context["slots"] = {}
                if updated: return ResponseGenerator.simple(f"✅ Updated **{updated.name}** to **Rs. {updated.cost}**.")
                return ResponseGenerator.error("Treatment not found.")

            # --- FEATURE: NEW INVENTORY ---
            if intent == "inventory_create":
                self.context["intent"] = "inventory_create"
                slots = self.context["slots"]

                if not slots.get("name"):
                    clean = q.replace("create item", "").replace("new item", "").strip()
                    if len(clean) > 2 and clean != "new item": slots["name"] = clean
                    else: return ResponseGenerator.simple("What is the name of the new item?")

                if not slots.get("quantity"):
                    nums = re.findall(r'\d+', q)
                    if nums: slots["quantity"] = int(nums[0])
                    else: return ResponseGenerator.simple(f"How much initial stock for **{slots['name']}**?")

                created = self.inv.create_item(slots["name"], slots["quantity"])
                self.context["intent"] = None
                self.context["slots"] = {}
                if created: return ResponseGenerator.simple(f"✅ Created **{created.name}** with **{created.quantity}** units.")
                return ResponseGenerator.error(f"Item **{slots['name']}** already exists.")

            # --- EXISTING FEATURES ---

            if intent == "dashboard_stats":
                fin_data = self.fin.get_financial_summary("today")
                inv_items = self.inv.get_low_stock()
                return ResponseGenerator.simple(f"📊 **Overview:**\nRevenue: {fin_data['revenue']}\nAlerts: {len(inv_items)}")

            # === DYNAMIC SCHEDULE LOGIC ===
            if intent == "schedule_view":
                date_str, _ = DateParser.parse_datetime(q)
                appts = self.appt.get_schedule(date_str)
                if not appts: return ResponseGenerator.simple(f"📅 No appointments for {date_str}.")

                # DYNAMIC CHECK: Is the user asking for DETAILS (Treatments/Procedures)?
                if any(w in q for w in ["treatment", "procedure", "doing", "work", "case", "problem"]):
                    summary_lines = []
                    for a in appts:
                        # Handle Null Patients (Blocked slots)
                        p_name = a.patient.user.full_name if (a.patient and a.patient.user) else "Blocked Slot"
                        t_type = a.treatment_type or "General Consultation"
                        time_display = a.start_time.strftime("%I:%M %p")
                        
                        # Add line: "10:30 AM - Ali: Root Canal"
                        summary_lines.append(f"- **{time_display}**: {p_name} — *{t_type}*")
                    
                    return ResponseGenerator.simple(f"📋 **Procedure Plan for {date_str}:**\n\n" + "\n".join(summary_lines))

                # DEFAULT: Return the Visual Card
                return ResponseGenerator.success_schedule(appts, date_str)

            if intent == "schedule_block":
                date_str, time_str = DateParser.parse_datetime(q)
                if not time_str: return ResponseGenerator.simple("Please specify a time to block.")
                self.appt.block_slot(date_str, time_str, "Doctor Blocked")
                return ResponseGenerator.simple(f"🚫 Blocked slot on {date_str} at {time_str}.")

            if intent == "inventory_check":
                low_stock = self.inv.get_low_stock()
                if not low_stock: return ResponseGenerator.simple("✅ Inventory healthy.")
                items = ", ".join([i.name for i in low_stock])
                return ResponseGenerator.simple(f"⚠️ **Low Stock:** {items}")

            if intent == "inventory_add":
                nums = re.findall(r'\d+', q)
                qty = int(nums[0]) if nums else 10
                all_items = self.inv.get_all_items()
                names = [i.name for i in all_items]
                match = process.extractOne(q, names, scorer=fuzz.partial_ratio)
                if match and match[1] > 60:
                    updated = self.inv.update_stock(match[0], qty)
                    return ResponseGenerator.simple(f"✅ Added {qty} to **{match[0]}**. Total: {updated.quantity}")
                return ResponseGenerator.simple("Which item needs stock?")

            if intent == "finance_view":
                period = "week" if "week" in q else "today"
                data = self.fin.get_financial_summary(period)
                return ResponseGenerator.simple(f"💰 **Financials ({period}):**\nRevenue: {data['revenue']}\nPending: {data['pending']}")

            if intent == "patient_search":
                clean = q.replace("search patient", "").replace("who is", "").strip()
                p = self.pat.find_patient(clean)
                if p:
                    self.context["last_patient"] = p.user.full_name
                    return ResponseGenerator.simple(f"👤 **{p.user.full_name}**\nPhone: {p.user.phone_number}\nLast Visit: {p.last_visit_date or 'N/A'}")
                return ResponseGenerator.error("Patient not found.")

            if intent == "settings_availability":
                times = re.findall(r'\d{1,2}:\d{2}', q)
                if len(times) >= 2:
                    self.settings.update_working_hours(times[0], times[1])
                    return ResponseGenerator.simple(f"⏰ Updated hours: {times[0]} - {times[1]}")
                return ResponseGenerator.simple("Specify start and end times (e.g. 09:00 to 17:00).")

            return ResponseGenerator.simple(f"I understood '{intent}' but need more info.")

        except Exception as e:
            self.context["intent"] = None
            return ResponseGenerator.error(f"Error: {str(e)}")
