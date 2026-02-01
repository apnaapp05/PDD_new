from sqlalchemy.orm import Session
from models import Appointment, MedicalRecord, Patient, User
from datetime import datetime

class ClinicalService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def start_appointment(self, patient_name: str):
        # Find today's appointment for this patient
        p = self.db.query(Patient).join(User).filter(User.full_name.ilike(f"%{patient_name}%")).first()
        if not p: raise ValueError("Patient not found.")

        appt = self.db.query(Appointment).filter(
            Appointment.patient_id == p.id,
            Appointment.doctor_id == self.doc_id,
            Appointment.start_time >= datetime.now().replace(hour=0, minute=0),
            Appointment.status == "pending"
        ).first()

        if not appt: raise ValueError("No pending appointment found for today.")
        
        appt.status = "in_progress"
        self.db.commit()
        return f"✅ Appointment started for {patient_name}."

    def add_record(self, patient_name: str, diagnosis: str, prescription: str):
        p = self.db.query(Patient).join(User).filter(User.full_name.ilike(f"%{patient_name}%")).first()
        if not p: raise ValueError("Patient not found.")

        rec = MedicalRecord(
            patient_id=p.id,
            doctor_id=self.doc_id,
            diagnosis=diagnosis,
            prescription=prescription,
            notes="Added via AI Agent",
            date=datetime.now()
        )
        self.db.add(rec)
        self.db.commit()
        return f"✅ Medical Record added for {patient_name}."
