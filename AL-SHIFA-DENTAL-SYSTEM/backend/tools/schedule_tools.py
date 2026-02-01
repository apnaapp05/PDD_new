from sqlalchemy.orm import Session
from models import Appointment, Patient, User
from datetime import datetime, timedelta

class ScheduleTools:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_upcoming_appointments(self, limit=5):
        appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.status != 'cancelled',
            Appointment.start_time >= datetime.now()
        ).order_by(Appointment.start_time).limit(limit).all()
        
        if not appts: return "No upcoming appointments."
        
        # Schema Fix: Handle blocked slots (no patient) vs booked slots
        results = []
        for a in appts:
            name = a.patient.user.full_name if a.patient and a.patient.user else "Blocked/Unknown"
            results.append(f"📅 {a.start_time.strftime('%Y-%m-%d %H:%M')} - {name} ({a.treatment_type})")
            
        return "\n".join(results)

    def block_slot(self, date_str: str, time_str: str, reason: str):
        try:
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=30)
            
            # Check overlap logic could go here
            
            self.db.add(Appointment(
                doctor_id=self.doc_id, start_time=start_dt, end_time=end_dt, 
                status="blocked", notes=reason, treatment_type="Blocked"
            ))
            self.db.commit()
            return f"✅ Blocked schedule on {date_str} at {time_str}."
        except: return "❌ Invalid format. Use YYYY-MM-DD HH:MM"

    def cancel_appointment(self, patient_name: str):
        """Cancels the NEXT appointment for a specific patient."""
        # Find patient by User name
        p = self.db.query(Patient).join(User).filter(
            User.full_name.ilike(f"%{patient_name}%")
        ).first()
        
        if not p: return "❌ Patient not found."

        appt = self.db.query(Appointment).filter(
            Appointment.patient_id == p.id,
            Appointment.doctor_id == self.doc_id,
            Appointment.status == "pending", # Changed from 'scheduled' to 'pending' to match models
            Appointment.start_time >= datetime.now()
        ).order_by(Appointment.start_time).first()

        if not appt: return f"❌ No pending appointments found for {patient_name}."

        appt.status = "cancelled"
        self.db.commit()
        return f"✅ Cancelled appointment for **{p.user.full_name}** on {appt.start_time}."
