from sqlalchemy.orm import Session
from models import Doctor
import json

class SettingsService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def update_availability(self, start_time: str, end_time: str):
        """Updates the working hours."""
        doc = self.db.query(Doctor).filter(Doctor.id == self.doc_id).first()
        if not doc: raise ValueError("Doctor not found.")

        # Logic: Parse existing config or create new
        config = {}
        if doc.scheduling_config:
            try: config = json.loads(doc.scheduling_config)
            except: config = {}
        
        config["work_hours"] = {"start": start_time, "end": end_time}
        doc.scheduling_config = json.dumps(config)
        self.db.commit()
        return f"✅ Availability updated: {start_time} to {end_time}"
