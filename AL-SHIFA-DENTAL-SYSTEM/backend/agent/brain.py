from sqlalchemy.orm import Session
from services.appointment_service import AppointmentService
from services.analytics_service import AnalyticsService
from services.inventory_service import InventoryService
from services.patient_service import PatientService
from services.settings_service import SettingsService
from services.clinical_service import ClinicalService
from services.treatment_service import TreatmentService
from services.response_generator import ResponseGenerator
from utils.nlp_parser import DateParser
import re

class ClinicAgent:
    def __init__(self, db: Session, doctor_id: int):
        self.appt = AppointmentService(db, doctor_id)
        self.fin = AnalyticsService(db, doctor_id)
        self.inv = InventoryService(db, doctor_id)
        self.pat = PatientService(db, doctor_id)
        self.settings = SettingsService(db, doctor_id)
        self.clinical = ClinicalService(db, doctor_id)
        self.treat = TreatmentService(db, doctor_id)
        
        # --- SESSION MEMORY ---
        # Note: In a real API, this memory would be stored in Redis/DB per session_id.
        # For this simplified single-class instance, it persists per request but resets on restart.
        self.last_patient_name = None 

    def process(self, query: str):
        q = query.lower()
        try:
            # --- MEMORY RESOLUTION ("Him/Her") ---
            if (" him" in q or " her" in q) and self.last_patient_name:
                 # Replace "him/her" with the name for logic processing
                 # But we keep it simple: Just assume the command applies to last_patient_name
                 pass

            # --- 1. AVAILABILITY ---
            if "availability" in q and "update" in q:
                _, end_time = DateParser.parse_datetime(q)
                if not end_time: return ResponseGenerator.error("Please specify a time, e.g., 'till 8:00 PM'")
                res = self.settings.update_availability("09:00", end_time)
                return ResponseGenerator.simple(res)

            # --- 2. SCHEDULE ---
            if "block" in q:
                date_str, time_str = DateParser.parse_datetime(q)
                if not date_str or not time_str: return ResponseGenerator.error("I didn't understand the time. Try 'Block today 5pm'")
                
                self.appt.block_slot(date_str, time_str, "Agent Block")
                return ResponseGenerator.success_block(date_str, time_str)

            if "schedule" in q or "appointments" in q:
                date_str, _ = DateParser.parse_datetime(q)
                appts = self.appt.get_schedule(date_str)
                return ResponseGenerator.success_schedule(appts, date_str)

            # --- 3. CLINICAL (Start/Complete/Record) ---
            if "start appointment" in q:
                name = self._extract_name(q, "start appointment for")
                res = self.clinical.start_appointment(name)
                self.last_patient_name = name # Remember
                return ResponseGenerator.simple(res)

            if "complete" in q and ("appointment" in q or "treatment" in q):
                name = self._extract_name(q, "complete appointment for")
                res = self.clinical.complete_appointment(patient_name=name)
                return ResponseGenerator.simple(res)
            
            if "add record" in q:
                if ":" in q:
                    parts = q.split(":")
                    name_part = parts[0].replace("add record for", "").strip()
                    
                    # Handle "Him/Her"
                    if ("him" in name_part or "her" in name_part) and self.last_patient_name:
                        name = self.last_patient_name
                    else:
                        name = name_part
                        self.last_patient_name = name

                    details = parts[1].split(",")
                    diagnosis = details[0].strip()
                    rx = details[1].strip() if len(details) > 1 else "None"
                    res = self.clinical.add_record(name, diagnosis, rx)
                    return ResponseGenerator.simple(res)
                return ResponseGenerator.error("Use format: 'Add record for [Name]: [Diagnosis], [Rx]'")

            # --- 4. FINANCE ---
            if "revenue" in q:
                period = "week" if "week" in q else "today"
                data = self.fin.get_financial_summary(period)
                return ResponseGenerator.success_finance(data['revenue'], data['pending'])
            
            # --- 5. INVENTORY ---
            if "stock" in q or "inventory" in q:
                if "low" in q or "check" in q or "status" in q:
                    items = self.inv.get_low_stock()
                    return ResponseGenerator.success_inventory_alert(items)
                
                if "add" in q or "update" in q:
                    match_qty = re.search(r'\d+', q)
                    if not match_qty: return ResponseGenerator.error("Tell me how many.")
                    qty = int(match_qty.group())
                    item = q.split(match_qty.group())[-1].strip()
                    updated = self.inv.update_stock(item, qty)
                    return ResponseGenerator.simple(f"✅ Updated {updated.name}.")

            # --- 6. PATIENTS ---
            if "who is" in q or "history" in q:
                name = q.replace("who is", "").replace("history of", "").strip()
                p = self.pat.find_patient(name)
                if not p: return ResponseGenerator.error("Patient not found.")
                
                self.last_patient_name = p.user.full_name # Remember for context
                
                history = self.pat.get_history(p.id)
                count = len(history)
                return {
                    "text": f"👤 **{p.user.full_name}**\nHas visited {count} times.",
                    "buttons": [
                        { "label": "📂 View History", "action": f"/doctor/patients/{p.id}", "type": "navigate" },
                        { "label": "Start Appointment", "action": f"Start appointment for {p.user.full_name}", "type": "chat" }
                    ]
                }

            return {
                "text": "👋 I am your Unified Clinic Agent. I can manage Schedule, Patients, Clinical Records, and Settings.",
                "buttons": [
                    { "label": "Check Revenue", "action": "Show my revenue", "type": "chat" },
                    { "label": "View Schedule", "action": "Show schedule", "type": "chat" }
                ]
            }

        except Exception as e:
            return ResponseGenerator.error(str(e))

    def _extract_name(self, query, trigger):
        """Helper to safely extract name or use memory"""
        raw = query.replace(trigger, "").strip()
        if ("him" in raw or "her" in raw or "it" in raw) and self.last_patient_name:
            return self.last_patient_name
        return raw
