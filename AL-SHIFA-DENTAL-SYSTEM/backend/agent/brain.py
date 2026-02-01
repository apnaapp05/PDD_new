from sqlalchemy.orm import Session
from services.appointment_service import AppointmentService
from services.analytics_service import AnalyticsService
from services.inventory_service import InventoryService
from services.patient_service import PatientService
from services.settings_service import SettingsService
from services.clinical_service import ClinicalService
from services.response_generator import ResponseGenerator
from utils.nlp_parser import DateParser
from rapidfuzz import process as fuzz_process, fuzz
import re
import random

class ClinicAgent:
    def __init__(self, db: Session, doctor_id: int):
        # --- THE TOOLBOX ---
        self.appt = AppointmentService(db, doctor_id)
        self.fin = AnalyticsService(db, doctor_id)
        self.inv = InventoryService(db, doctor_id)
        self.pat = PatientService(db, doctor_id)
        self.settings = SettingsService(db, doctor_id)
        self.clinical = ClinicalService(db, doctor_id)
        
        # --- CONTEXT MEMORY ---
        self.context = {"last_patient": None}

        # --- THE KNOWLEDGE MAP (Intent -> Keywords) ---
        self.INTENTS = {
            "schedule_view": ["schedule", "calendar", "appointments", "plan", "agenda", "shedule", "show me my day", "what is on today"],
            "schedule_block": ["block", "close slot", "busy", "reserve", "hold off"],
            "schedule_cancel": ["cancel", "delete appointment", "remove", "clear slot"],
            "inventory_check": ["stock", "inventory", "supplies", "gloves", "masks", "how many", "materials", "check stock"],
            "inventory_add": ["add stock", "update stock", "buy", "order", "increase", "received"],
            "finance_view": ["revenue", "money", "income", "earnings", "finance", "profit", "how much did i make", "sales"],
            "patient_search": ["who is", "patient history", "find patient", "search patient", "records", "details of"],
            "clinical_start": ["start", "begin", "consultation"],
            "clinical_complete": ["complete", "finish", "done", "finalize", "bill him"],
            "clinical_record": ["add record", "diagnosis", "prescription", "note", "write down"]
        }

    def process(self, query: str):
        q = query.lower().strip()
        
        # 1. HANDLE MEMORY (Contextual Pronouns)
        if (" him" in q or " her" in q or " it" in q) and self.context["last_patient"]:
            # We assume the user refers to the last person
            pass 

        # 2. FUZZY ROUTING (The "Brain")
        # We flat-map intents to find the best match score
        best_score = 0
        best_intent = None
        
        for intent, keywords in self.INTENTS.items():
            match = fuzz_process.extractOne(q, keywords, scorer=fuzz.partial_ratio)
            if match and match[1] > best_score:
                best_score = match[1]
                best_intent = intent

        # Threshold: If < 60% match, we are unsure.
        if best_score < 60:
            return ResponseGenerator.simple("I'm not sure I understood. Are you asking about Schedule, Patients, or Stock?")

        # 3. EXECUTE INTENT
        try:
            # --- SCHEDULE ---
            if best_intent == "schedule_view":
                date_str, _ = DateParser.parse_datetime(q)
                appts = self.appt.get_schedule(date_str)
                return ResponseGenerator.success_schedule(appts, date_str)

            if best_intent == "schedule_block":
                date_str, time_str = DateParser.parse_datetime(q)
                if not time_str: return ResponseGenerator.error("To block a slot, I need a time (e.g., 'Block today 5pm').")
                self.appt.block_slot(date_str, time_str, "Agent Block")
                return ResponseGenerator.success_block(date_str, time_str)

            if best_intent == "schedule_cancel":
                name = self._extract_name(q, ["cancel appointment for", "cancel", "remove"])
                if not name: return ResponseGenerator.error("Who should I cancel?")
                self.appt.cancel_appointment(name)
                return ResponseGenerator.simple(f"✅ Cancelled appointment for {name}.")

            # --- INVENTORY ---
            if best_intent == "inventory_check":
                # Check if specific item mentioned
                if "low" in q:
                    items = self.inv.get_low_stock()
                    return ResponseGenerator.success_inventory_alert(items)
                return ResponseGenerator.success_inventory_alert([]) # Default view

            if best_intent == "inventory_add":
                match_qty = re.search(r'\d+', q)
                if not match_qty: return ResponseGenerator.error("How many items?")
                qty = int(match_qty.group())
                # Extract item name by removing keywords
                clean_q = q
                for k in ["add", "stock", "update", str(qty)]: clean_q = clean_q.replace(k, "")
                item_name = clean_q.strip()
                updated = self.inv.update_stock(item_name, qty)
                return ResponseGenerator.simple(f"✅ Added {qty} to {updated.name}.")

            # --- FINANCE ---
            if best_intent == "finance_view":
                period = "week" if "week" in q else "today"
                data = self.fin.get_financial_summary(period)
                return ResponseGenerator.success_finance(data['revenue'], data['pending'])

            # --- PATIENTS ---
            if best_intent == "patient_search":
                name = self._extract_name(q, ["who is", "history of", "search", "details"])
                p = self.pat.find_patient(name)
                if not p: return ResponseGenerator.error("Patient not found.")
                self.context["last_patient"] = p.user.full_name # MEMORY SET
                
                history = self.pat.get_history(p.id)
                return {
                    "text": f"👤 **{p.user.full_name}**\nAge: {p.age} | {len(history)} Visits",
                    "buttons": [
                        { "label": "📂 View History", "action": f"/doctor/patients/{p.id}", "type": "navigate" },
                        { "label": "Start Visit", "action": f"Start appointment for {p.user.full_name}", "type": "chat" }
                    ]
                }

            # --- CLINICAL ---
            if best_intent == "clinical_start":
                name = self._extract_name(q, ["start appointment for", "start"])
                res = self.clinical.start_appointment(name)
                self.context["last_patient"] = name
                return ResponseGenerator.simple(res)

            if best_intent == "clinical_complete":
                name = self._extract_name(q, ["complete appointment for", "finish"])
                # Use memory if name missing
                if not name and self.context["last_patient"]: name = self.context["last_patient"]
                res = self.clinical.complete_appointment(patient_name=name)
                return ResponseGenerator.simple(res)

            if best_intent == "clinical_record":
                # Fallback simple parser for now
                if ":" in q:
                    parts = q.split(":")
                    name_part = parts[0].replace("add record for", "").strip()
                    if not name_part and self.context["last_patient"]: name_part = self.context["last_patient"]
                    
                    details = parts[1].split(",")
                    diagnosis = details[0].strip()
                    rx = details[1].strip() if len(details) > 1 else ""
                    self.clinical.add_record(name_part, diagnosis, rx)
                    return ResponseGenerator.simple(f"✅ Record saved for {name_part}.")
                return ResponseGenerator.error("Format: 'Add record: Diagnosis, Prescription'")

        except Exception as e:
            return ResponseGenerator.error(f"Something went wrong: {str(e)}")

        return ResponseGenerator.simple("I understood your intent but couldn't execute it.")

    def _extract_name(self, query, trigger_phrases):
        """Helper to strip trigger words and return the name"""
        clean = query
        for phrase in trigger_phrases:
            clean = clean.replace(phrase, "")
        return clean.strip()
