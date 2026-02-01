from sqlalchemy.orm import Session
from models import Appointment, Patient, User, Doctor
from datetime import datetime, timedelta
from fastapi import HTTPException

class AppointmentService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_schedule(self, date_str: str = None, range_days: int = 0):
        """Fetches schedule for a specific date or a range."""
        query = self.db.query(Appointment).filter(Appointment.doctor_id == self.doc_id)
        
        if date_str:
            try:
                start_date = datetime.strptime(date_str, "%Y-%m-%d")
                end_date = start_date + timedelta(days=range_days + 1)
                query = query.filter(Appointment.start_time >= start_date, Appointment.start_time < end_date)
            except ValueError:
                pass # Return all if date invalid
                
        return query.order_by(Appointment.start_time).all()

    def block_slot(self, date_str: str, time_str: str, reason: str):
        """Blocks a slot. Used by Portal AND Chatbot."""
        try:
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=30)
            
            # 1. Check for Overlap (The Logic Rule)
            overlap = self.db.query(Appointment).filter(
                Appointment.doctor_id == self.doc_id,
                Appointment.start_time < end_dt,
                Appointment.end_time > start_dt,
                Appointment.status != 'cancelled'
            ).first()
            
            if overlap:
                raise ValueError(f"Slot {time_str} is already occupied by {overlap.treatment_type}.")

            # 2. Save
            appt = Appointment(
                doctor_id=self.doc_id, start_time=start_dt, end_time=end_dt,
                status="blocked", notes=reason, treatment_type="Blocked"
            )
            self.db.add(appt)
            self.db.commit()
            return appt
        except ValueError as e:
            raise e

    def cancel_appointment(self, patient_name: str):
        """Cancels upcoming appointment."""
        # Find patient via User table (Correct Logic)
        p = self.db.query(Patient).join(User).filter(User.full_name.ilike(f"%{patient_name}%")).first()
        if not p: raise ValueError(f"Patient '{patient_name}' not found.")

        appt = self.db.query(Appointment).filter(
            Appointment.patient_id == p.id,
            Appointment.doctor_id == self.doc_id,
            Appointment.status == "pending",
            Appointment.start_time >= datetime.now()
        ).first()

        if not appt: raise ValueError(f"No pending appointment found for {patient_name}.")
        
        appt.status = "cancelled"
        self.db.commit()
        return appt
