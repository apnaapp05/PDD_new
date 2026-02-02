import spacy
import pandas as pd
from rapidfuzz import process, fuzz
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Doctor, Appointment, Patient, User
from services.appointment_service import AppointmentService

try:
    nlp = spacy.load("en_core_web_sm")
except:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class PatientBrain:
    _sessions = {}

    def __init__(self, db: Session, patient_id: int):
        self.db = db
        self.patient_id = patient_id
        if patient_id not in self._sessions:
            self._sessions[patient_id] = {
                "intent": None, 
                # Shared slots + specific appointment_id for cancel/reschedule
                "slots": {"doctor": None, "doctor_id": None, "treatment": None, "date": None, "time": None, "appointment_id": None}
            }
        
        self.session = self._sessions[patient_id]
        self.appt_service = AppointmentService(db, None) 

    # --- PARSERS ---
    def _parse_time(self, time_str):
        if not time_str: return None
        time_str = time_str.strip().upper()
        formats = ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p", "%I%p"]
        for fmt in formats:
            try: return datetime.strptime(time_str, fmt).strftime("%H:%M")
            except ValueError: continue
        return None

    def _parse_date(self, date_str):
        if not date_str: return datetime.now().strftime("%Y-%m-%d")
        today = datetime.now().date()
        d_str = date_str.lower()
        if "today" in d_str: return today.strftime("%Y-%m-%d")
        if "tomorrow" in d_str: return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        return date_str

    # --- SCANNER ---
    def _scan_for_slots(self, text: str):
        doc = nlp(text)
        found = {}
        for ent in doc.ents:
            if ent.label_ == "TIME": found["time"] = ent.text
            if ent.label_ == "DATE": found["date"] = ent.text

        # Doctor Match
        doctors = self.db.query(Doctor).join(User).all()
        doc_map = {d.user.full_name: d.id for d in doctors if d.user}
        if doc_map:
            match = process.extractOne(text, doc_map.keys(), scorer=fuzz.token_set_ratio)
            if match and match[1] > 60: 
                found["doctor"] = match[0]
                found["doctor_id"] = doc_map[match[0]]

        # Treatment Match
        treatments = ["Root Canal", "Checkup", "Cleaning", "Extraction", "Whitening"]
        t_match = process.extractOne(text, treatments, scorer=fuzz.partial_ratio)
        if t_match and t_match[1] > 70: found["treatment"] = t_match[0]
        
        return found

    # --- INTENT DETECTOR ---
    def _detect_intent(self, text: str):
        q = text.lower()
        # High Priority: Cancel
        if any(w in q for w in ["cancel", "delete", "remove", "not coming"]):
            return "cancel"
        # High Priority: Reschedule
        if any(w in q for w in ["reschedule", "move", "change time", "delay", "postpone"]):
            return "reschedule"
        # Lower Priority: Book
        if any(w in q for w in ["book", "schedule", "appointment", "visit"]):
            return "book"
        return None

    def process(self, query: str):
        q = query.lower()
        
        # 1. Update Intent if keywords present
        detected = self._detect_intent(query)
        if detected:
            self.session["intent"] = detected
            # Clear slots if switching intents (except doctor maybe)
            if detected != self.session.get("last_intent"):
                self.session["slots"] = {"doctor": None, "doctor_id": None, "treatment": None, "date": None, "time": None, "appointment_id": None}
            self.session["last_intent"] = detected

        intent = self.session["intent"]
        
        # 2. Update Slots
        new_slots = self._scan_for_slots(query)
        self.session["slots"].update(new_slots)
        slots = self.session["slots"]

        # --- BRANCH: CANCEL ---
        if intent == "cancel":
            # Step 1: Identify Appointment
            if not slots["appointment_id"]:
                # Fetch upcoming
                upcoming = self.appt_service.get_patient_upcoming(self.patient_id)
                if not upcoming:
                    return {"text": "You don't have any upcoming appointments to cancel."}
                
                # Check if user selected one via text match (e.g. "cancel the one with Dr Ali")
                # Simple logic: If only 1 exists, auto-select
                if len(upcoming) == 1:
                    slots["appointment_id"] = upcoming[0].id
                    slots["doctor"] = upcoming[0].doctor.user.full_name
                    # Fall through to confirmation
                else:
                    # Logic to matching user selection from list would go here.
                    # For now, ask user to pick:
                    options = [f"Dr. {u.doctor.user.full_name} ({u.start_time.strftime('%b %d %H:%M')})" for u in upcoming]
                    # Also need to map selection back to ID. In a real app we'd use a map.
                    # Hack: Store map in session for next turn? 
                    # Simpler: Just showing text. If user types "Dr Ali", the scanner finds "Doctor".
                    
                    # We will rely on scanner finding "Doctor" to filter the list
                    if slots["doctor"]:
                        # Filter by doctor name
                        filtered = [u for u in upcoming if slots["doctor"] in u.doctor.user.full_name]
                        if len(filtered) == 1:
                            slots["appointment_id"] = filtered[0].id
                        else:
                            return {"text": f"You have multiple appointments with Dr. {slots['doctor']}. Which date?", "actions": [u.start_time.strftime('%Y-%m-%d') for u in filtered]}
                    else:
                        return {"text": "Which appointment would you like to cancel?", "actions": options}

            # Step 2: Confirm & Execute
            if slots["appointment_id"]:
                if any(w in q for w in ["confirm", "yes", "ok"]):
                    try:
                        self.appt_service.cancel_appointment_by_id(slots["appointment_id"], self.patient_id)
                        self.session["intent"] = None
                        self.session["slots"]["appointment_id"] = None
                        return {"text": "✅ Appointment cancelled successfully.", "redirect": "/patient/dashboard"}
                    except Exception as e:
                        return {"text": f"Error canceling: {str(e)}"}
                
                return {"text": "Are you sure you want to cancel this appointment?", "actions": ["Yes, Confirm", "No, Keep it"]}

        # --- BRANCH: RESCHEDULE ---
        if intent == "reschedule":
            # Step 1: Identify Appointment (Same logic as cancel)
            if not slots["appointment_id"]:
                upcoming = self.appt_service.get_patient_upcoming(self.patient_id)
                if not upcoming: return {"text": "No upcoming appointments to reschedule."}
                
                if len(upcoming) == 1:
                    slots["appointment_id"] = upcoming[0].id
                    # Pre-fill doctor for context
                    slots["doctor"] = upcoming[0].doctor.user.full_name 
                elif slots["doctor"]:
                     filtered = [u for u in upcoming if slots["doctor"] in u.doctor.user.full_name]
                     if len(filtered) == 1: slots["appointment_id"] = filtered[0].id
                
                if not slots["appointment_id"]:
                     options = [f"Dr. {u.doctor.user.full_name} ({u.start_time.strftime('%b %d')})" for u in upcoming]
                     return {"text": "Which appointment do you want to move?", "actions": options}

            # Step 2: Get New Time
            if not slots["date"] or not slots["time"]:
                return {"text": "When would you like to move it to?", "actions": ["Tomorrow 10am", "Tomorrow 2pm"]}

            # Step 3: Confirm & Execute
            if any(w in q for w in ["confirm", "yes", "ok"]):
                try:
                    final_date = self._parse_date(slots["date"])
                    final_time = self._parse_time(slots["time"])
                    if not final_time: return {"text": "Invalid time format."}

                    self.appt_service.reschedule_appointment(
                        slots["appointment_id"], self.patient_id, final_date, final_time
                    )
                    self.session["intent"] = None
                    self.session["slots"] = {"doctor": None, "doctor_id": None, "treatment": None, "date": None, "time": None, "appointment_id": None}
                    return {"text": f"✅ Rescheduled to **{final_date}** at **{final_time}**.", "redirect": "/patient/dashboard"}
                except Exception as e:
                    return {"text": f"Could not reschedule: {str(e)} (Maybe slot is taken?)"}

            return {"text": f"Confirm move to **{slots['date']}** at **{slots['time']}**?", "actions": ["Yes, Confirm", "No"]}

        # --- BRANCH: BOOK (Legacy + Chips) ---
        if intent == "book":
            if not slots["doctor"]:
                docs = self.db.query(Doctor).join(User).limit(5).all()
                return {"text": "Which doctor?", "actions": [d.user.full_name for d in docs if d.user]}
            
            if not slots["treatment"]:
                return {"text": f"Treatment for Dr. {slots['doctor']}?", "actions": ["Checkup", "Root Canal", "Cleaning"]}
            
            if not slots["time"]:
                return {"text": "When would you like to come?", "actions": ["Today 10am", "Tomorrow 2pm"]}

            if any(w in q for w in ["confirm", "yes", "ok"]):
                try:
                    final_date = self._parse_date(slots["date"])
                    final_time = self._parse_time(slots["time"])
                    if not final_time: return {"text": "Please provide a valid time (e.g. 10:00 AM)."}
                    
                    self.appt_service.doc_id = slots["doctor_id"]
                    self.appt_service.book_appointment(self.patient_id, final_date, final_time, slots["treatment"])
                    
                    self.session["intent"] = None
                    self.session["slots"] = {"doctor": None, "doctor_id": None, "treatment": None, "date": None, "time": None, "appointment_id": None}
                    return {"text": f"✅ Booked {slots['treatment']} with {slots['doctor']}.", "redirect": "/patient/dashboard"}
                except Exception as e:
                    return {"text": f"Error: {str(e)}"}

            return {"text": f"Book **{slots['treatment']}** with **{slots['doctor']}** at **{slots['time']}**?", "actions": ["Yes", "No"]}

        # DEFAULT
        return {
            "text": "Salam! I can help you **Book**, **Cancel**, or **Reschedule** appointments.",
            "actions": ["Book Appointment", "Cancel Appointment", "Reschedule"]
        }
