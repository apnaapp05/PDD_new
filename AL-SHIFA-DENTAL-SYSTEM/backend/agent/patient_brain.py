import spacy
import pandas as pd
from rapidfuzz import process, fuzz
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from models import Doctor, Appointment, Patient, Treatment, Hospital

# Load NLP Model (Lightweight English model)
try:
    nlp = spacy.load("en_core_web_sm")
except:
    # Fallback if model isn't downloaded yet
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class PatientBrain:
    def __init__(self, db: Session):
        self.db = db
        # Valid Intents mapped to fuzzy keywords
        self.intents = {
            "book_appointment": ["book", "schedule", "appointment", "visit", "see a doctor", "reservation"],
            "cancel_appointment": ["cancel", "delete", "remove", "not coming"],
            "reschedule_appointment": ["reschedule", "move", "change time", "postpone", "delay"],
            "check_availability": ["available", "slots", "openings", "when is", "free time"]
        }

    def _detect_intent(self, text: str):
        """Uses RapidFuzz to find the closest matching intent."""
        # Flatten the intent list for matching
        all_keywords = []
        key_map = {}
        for intent, keys in self.intents.items():
            for k in keys:
                all_keywords.append(k)
                key_map[k] = intent
        
        # Extract best match
        best_match = process.extractOne(text.lower(), all_keywords, scorer=fuzz.partial_ratio)
        if best_match and best_match[1] > 70:  # 70% confidence threshold
            return key_map[best_match[0]]
        return "unknown"

    def _extract_entities(self, text: str):
        """Uses SpaCy to extract Dates, Times, and Doctor Names."""
        doc = nlp(text)
        entities = {"date": None, "time": None, "doctor_name": None}
        
        for ent in doc.ents:
            if ent.label_ == "DATE":
                entities["date"] = ent.text
            elif ent.label_ == "TIME":
                entities["time"] = ent.text
            elif ent.label_ == "PERSON":
                entities["doctor_name"] = ent.text
        
        # Fallback: Look for specific words if SpaCy misses
        if not entities["doctor_name"]:
            # Check DB for doctor names in the text (using Pandas for speed)
            doctors = self.db.query(Doctor).all()
            doc_names = [d.user.full_name.lower() for d in doctors if d.user]
            match = process.extractOne(text.lower(), doc_names, score_cutoff=80)
            if match:
                entities["doctor_name"] = match[0]
                
        return entities

    def _get_doctor_slots_pandas(self, doctor_name: str, date_str: str):
        """Uses Pandas to calculate available slots efficiently."""
        # 1. Find Doctor
        # Assuming doctor_name is partial, we search DB
        doc_query = self.db.query(Doctor).join(Doctor.user).all()
        # Find best match ID
        name_map = {d.user.full_name.lower(): d.id for d in doc_query}
        match = process.extractOne(doctor_name.lower(), name_map.keys(), score_cutoff=80)
        
        if not match:
            return None, "I couldn't find a doctor with that name."
        
        doctor_id = name_map[match[0]]
        
        # 2. Parse Date
        try:
            # Simple parser (in real app, use dateparser library)
            target_date = datetime.now().date() 
            if "tomorrow" in date_str.lower():
                target_date = target_date + timedelta(days=1)
            # (Logic for specific dates like 'next monday' requires more NLP, keeping simple for now)
            
            fmt_date = target_date.strftime("%Y-%m-%d")
        except:
            return None, "I couldn't understand the date."

        # 3. Fetch Booked Slots (Using standard SQL)
        start_day = datetime.combine(target_date, datetime.min.time())
        end_day = datetime.combine(target_date, datetime.max.time())
        
        appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time >= start_day,
            Appointment.start_time <= end_day,
            Appointment.status.in_(["confirmed", "pending", "blocked"])
        ).all()

        # 4. Use Pandas for Slot Logic
        # Create a DataFrame of busy slots
        busy_data = [{"start": a.start_time, "end": a.end_time} for a in appts]
        df_busy = pd.DataFrame(busy_data)

        # Generate All Potential Slots (e.g. 9 to 5)
        # We assume standard hours if not found in settings
        start_work = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time())
        end_work = datetime.combine(target_date, datetime.strptime("17:00", "%H:%M").time())
        
        # Generate range every 30 mins
        all_slots = pd.date_range(start=start_work, end=end_work, freq="30min")
        
        # Filter: Drop slots that overlap with busy dataframe
        available = []
        for slot in all_slots:
            slot_end = slot + timedelta(minutes=30)
            is_taken = False
            if not df_busy.empty:
                # Vectorized check: overlapping ranges
                # (StartA < EndB) and (EndA > StartB)
                overlaps = (df_busy["start"] < slot_end) & (df_busy["end"] > slot)
                if overlaps.any():
                    is_taken = True
            
            if not is_taken:
                available.append(slot.strftime("%I:%M %p"))

        return available, f"I checked for {match[0]} on {fmt_date}."

    def process_message(self, user_msg: str, user_id: int = None):
        """Main Entry Point"""
        intent = self._detect_intent(user_msg)
        entities = self._extract_entities(user_msg)
        
        response = {
            "text": "",
            "intent": intent,
            "detected_entities": entities,
            "data": None
        }

        if intent == "book_appointment" or intent == "check_availability":
            if not entities["doctor_name"]:
                response["text"] = "I can help with that. Which doctor would you like to see?"
                # In frontend, we can show a list of doctors as 'chips'
            elif not entities["date"]:
                response["text"] = f"Checking availability for Dr. {entities['doctor_name']}. What date works for you?"
            else:
                slots, msg = self._get_doctor_slots_pandas(entities["doctor_name"], entities["date"])
                if slots:
                    response["text"] = f"{msg} Here are the available slots:\n" + ", ".join(slots[:5])
                    response["data"] = {"slots": slots, "doctor": entities["doctor_name"], "date": entities["date"]}
                else:
                    response["text"] = f"{msg} Unfortunately, there are no slots available."
        
        elif intent == "cancel_appointment":
            response["text"] = "I can verify your scheduled appointments. Please provide the booking ID or the date."
            # Logic to fetch user appointments would go here
            
        elif intent == "unknown":
            response["text"] = "I'm still learning! Would you like to book an appointment or check doctor availability?"
            
        else:
            response["text"] = f"I detected you want to {intent.replace('_', ' ')}, but I need more details."

        return response

