from services.settings_service import SettingsService
from datetime import datetime
from agent.analyst import AnalystEngine
from sqlalchemy.orm import Session
import pandas as pd
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Internal Modules
from services.appointment_service import AppointmentService
from services.analytics_service import AnalyticsService
from services.inventory_service import InventoryService
from services.patient_service import PatientService
from services.clinical_service import ClinicalService
from services.response_generator import ResponseGenerator
from utils.nlp_parser import DateParser
from utils.smart_parser import SmartParser
from agent.intents import INTENT_TRAINING_DATA
from agent.scheduler import proactive_system

class ClinicAgent:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id
        
        # Tools
        self.appt = AppointmentService(db, doctor_id)
        self.fin = AnalyticsService(db, doctor_id)
        self.inv = InventoryService(db, doctor_id)
        self.pat = PatientService(db, doctor_id)
        self.clinical = ClinicalService(db, doctor_id)
        self.settings = SettingsService(db, doctor_id)
        self.analyst = AnalystEngine(db, doctor_id)
        
        # AI Components
        self.parser = SmartParser()
        self.vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4)) # Char n-grams handle typos!
        self.intents_map = []
        self._train_intent_model()
        
        # Context
        self.context = {"last_patient": None}

        # Ensure Scheduler is running
        proactive_system.start()

    def _train_intent_model(self):
        """Builds the 'Brain' by vectorizing the intent training data"""
        corpus = []
        self.intent_keys = []
        
        for intent, phrases in INTENT_TRAINING_DATA.items():
            for p in phrases:
                corpus.append(p)
                self.intent_keys.append(intent)
        
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def predict_intent(self, query):
        """Uses Cosine Similarity to find the best matching intent"""
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)
        
        best_idx = similarities.argmax()
        best_score = similarities[0, best_idx]
        
        if best_score < 0.35: # Threshold for "I don't know"
            return None
        return self.intent_keys[best_idx]

    def process(self, query: str):
        q = query.lower().strip()
        
        # 1. Check for Proactive Alerts
        alerts = proactive_system.get_pending_alerts()
        alert_prefix = ("\n\n".join(alerts) + "\n\n") if alerts else ""

                # 1.5. ANALYST CHECK (Natural Language Math)
        if self.analyst.is_analysis_query(q):
            result = self.analyst.analyze(q)
            return ResponseGenerator.simple(f"📊 **Analysis:**\n{result}")

        # 2. Predict Intent
        intent = self.predict_intent(q)
        if not intent:
            return ResponseGenerator.simple(f"{alert_prefix}I'm not sure what you mean. Try 'Show Schedule' or 'Check Revenue'.")

        try:
            # --- DASHBOARD & ANALYTICS ---
            if intent == "dashboard_stats":
                # Use Pandas for a quick summary (Simulated)
                fin_data = self.fin.get_financial_summary("today")
                inv_items = self.inv.get_low_stock()
                # Determine Tone
                revenue_mood = "Good start!" if fin_data['revenue'] > 0 else "Quiet day so far."
                return ResponseGenerator.simple(
                    f"{alert_prefix}📊 **Dashboard Summary**\n"
                    f"- **Revenue:** Rs. {fin_data['revenue']} ({revenue_mood})\n"
                    f"- **Alerts:** {len(inv_items)} low stock items.\n"
                    f"Ready for your next command."
                )

            # --- FINANCE ---
            if intent == "finance_view":
                period = "week" if "week" in q else "today"
                data = self.fin.get_financial_summary(period)
                # Pandas Analysis could go here (e.g., comparing to last week)
                return ResponseGenerator.success_finance(data['revenue'], data['pending'])

            # --- SCHEDULE ---
            if intent == "schedule_view":
                date_str, _ = DateParser.parse_datetime(q)
                appts = self.appt.get_schedule(date_str)
                # Smart Summary
                if not appts: return ResponseGenerator.simple(f"{alert_prefix}📅 Your schedule is clear for {date_str}.")
                return ResponseGenerator.success_schedule(appts, date_str)

            if intent == "schedule_block":
                date_str, time_str = DateParser.parse_datetime(q)
                if not time_str: return ResponseGenerator.error("Please specify a time to block.")
                self.appt.block_slot(date_str, time_str, "Agent Block")
                return ResponseGenerator.success_block(date_str, time_str)

            # --- INVENTORY ---
            if intent == "inventory_check":
                items = self.inv.get_low_stock()
                return ResponseGenerator.success_inventory_alert(items)

            if intent == "inventory_add":
                entities = self.parser.extract_entities(q)
                qty = int(entities["QUANTITY"]) if entities["QUANTITY"] else 0
                if qty == 0: return ResponseGenerator.error("I need a quantity (e.g., 'Add 10 gloves').")
                
                # Fuzzy match item name
                all_items = [i.name for i in self.inv.get_all_items()] # Need to implement get_all_items helper or direct DB
                # For now, simplistic extraction
                item_name = self.parser.fuzzy_extract_item(q, all_items) if all_items else "Unknown"
                
                # If fuzzy fail, fallback to raw string stripping
                if not item_name:
                     clean_q = q
                     for k in ["add", "stock", str(qty)]: clean_q = clean_q.replace(k, "")
                     item_name = clean_q.strip()

                updated = self.inv.update_stock(item_name, qty)
                return ResponseGenerator.simple(f"✅ Added {qty} to **{updated.name}**. New Qty: {updated.quantity}")

            # --- PATIENTS ---
            if intent == "patient_search":
                # SpaCy Entity Extraction
                entities = self.parser.extract_entities(q)
                name = entities["PERSON"]
                if not name: name = self._manual_extract_name(q, ["who is", "history", "search"])
                
                p = self.pat.find_patient(name)
                if not p: return ResponseGenerator.error("Patient not found.")
                self.context["last_patient"] = p.user.full_name
                
                return {
                    "text": f"👤 **{p.user.full_name}**\nFound in records. What would you like to do?",
                    "buttons": [
                        { "label": "Start Visit", "action": f"Start appointment for {p.user.full_name}", "type": "chat" },
                        { "label": "View History", "action": f"/doctor/patients/{p.id}", "type": "navigate" }
                    ]
                }

            # --- CLINICAL ---
                        # --- SETTINGS: AVAILABILITY ---
            if intent == "settings_availability":
                # 1. Parse Times using Regex or split
                import re
                # Regex to find time patterns like '11:00 AM', '9 pm', '21:00'
                times = re.findall(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)', q)
                
                if len(times) < 2:
                    return ResponseGenerator.error("I need both a Start Time and End Time (e.g., 'Update availability from 9 AM to 5 PM').")
                
                def parse_time(t_str):
                    t_str = t_str.strip().upper()
                    formats = ["%I %p", "%I:%M %p", "%I%p", "%H:%M", "%H"]
                    for fmt in formats:
                        try:
                            return datetime.strptime(t_str, fmt).strftime("%H:%M")
                        except ValueError:
                            continue
                    return None

                start_str = parse_time(times[0])
                end_str = parse_time(times[1])
                
                if not start_str or not end_str:
                     return ResponseGenerator.error(f"Could not understand the times '{times[0]}' or '{times[1]}'. Try '11:00 AM'.")

                self.settings.update_working_hours(start_str, end_str)
                return ResponseGenerator.simple(f"✅ **Availability Updated**\nNew Hours: **{start_str}** to **{end_str}**.\nThis is now saved in your profile.")

            if intent == "clinical_complete":
                name = self.context["last_patient"]
                if not name: return ResponseGenerator.error("Who are we finishing with?")
                res = self.clinical.complete_appointment(patient_name=name)
                return ResponseGenerator.simple(res)

        except Exception as e:
            return ResponseGenerator.error(f"Brain Freeze: {str(e)}")

        return ResponseGenerator.simple(f"{alert_prefix}Command recognized ({intent}) but logic is pending.")

    def _manual_extract_name(self, query, triggers):
        """Fallback if SpaCy misses the name"""
        clean = query
        for t in triggers: clean = clean.replace(t, "")
        return clean.strip()



