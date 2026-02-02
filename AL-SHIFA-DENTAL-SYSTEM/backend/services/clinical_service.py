from sqlalchemy.orm import Session
from models import Appointment, Invoice, Treatment
from datetime import datetime

class ClinicalService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def mark_in_progress(self, patient_name: str):
        # Find today's pending appointment for this patient
        today = datetime.now().date()
        appt = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.status == 'confirmed',
            Appointment.start_time >= today
        ).join(Appointment.patient).join(Appointment.patient.user).filter(
            Appointment.patient.has(user_id=Appointment.patient.user_id) # Simplify join
        ).all()
        
        # Fuzzy match logic happens in Brain, here we assume exact ID or filtered list
        # For simplicity in this 'Beast' upgrade, we find by partial name match on the joined user table
        # NOTE: Real production code would use ID. We will use a helper query here.
        targets = [a for a in appt if patient_name.lower() in a.patient.user.full_name.lower()]
        
        if not targets: return None
        target = targets[0] # Pick first match
        
        target.status = "in_progress"
        self.db.commit()
        return target

    def complete_appointment(self, patient_name: str):
        # Find 'in_progress' or 'confirmed' appt
        today = datetime.now().date()
        appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.status.in_(['in_progress', 'confirmed']),
            Appointment.start_time >= today
        ).all()

        targets = [a for a in appts if patient_name.lower() in a.patient.user.full_name.lower()]
        if not targets: return None
        target = targets[0]

        target.status = "completed"
        
        # GENERATE INVOICE AUTOMATICALLY
        # 1. Find cost
        cost = 500.0 # Default
        if target.treatment_type:
            t = self.db.query(Treatment).filter(
                Treatment.doctor_id == self.doc_id,
                Treatment.name.ilike(target.treatment_type)
            ).first()
            if t: cost = t.cost
            
        inv = Invoice(
            appointment_id=target.id,
            patient_id=target.patient_id,
            amount=cost,
            status="pending",
            issue_date=datetime.now()
        )
        self.db.add(inv)
        self.db.commit()
        return target, inv
