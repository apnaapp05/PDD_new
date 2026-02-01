from sqlalchemy.orm import Session
from models import Appointment, Patient, User
from datetime import datetime, timedelta
from notifications.service import NotificationService # Connect Notification

class AppointmentService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id
        self.notifier = NotificationService()

    def get_schedule(self, date_str: str = None, range_days: int = 0):
        query = self.db.query(Appointment).filter(Appointment.doctor_id == self.doc_id)
        if date_str:
            try:
                start_date = datetime.strptime(date_str, "%Y-%m-%d")
                end_date = start_date + timedelta(days=range_days + 1)
                query = query.filter(Appointment.start_time >= start_date, Appointment.start_time < end_date)
            except ValueError: pass
        return query.order_by(Appointment.start_time).all()

    def block_slot(self, date_str: str, time_str: str, reason: str):
        try:
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=30)
            
            overlap = self.db.query(Appointment).filter(
                Appointment.doctor_id == self.doc_id,
                Appointment.start_time < end_dt,
                Appointment.end_time > start_dt,
                Appointment.status != 'cancelled'
            ).first()
            
            if overlap: raise ValueError(f"Slot {time_str} is already occupied.")

            appt = Appointment(
                doctor_id=self.doc_id, start_time=start_dt, end_time=end_dt,
                status="blocked", notes=reason, treatment_type="Blocked"
            )
            self.db.add(appt)
            self.db.commit()
            return appt
        except ValueError as e: raise e

    def cancel_appointment(self, patient_name: str):
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
        
        # --- NOTIFICATION TRIGGER ---
        if p.user.phone_number:
            msg = f"Hello {p.user.full_name}, your appointment on {appt.start_time} has been cancelled."
            self.notifier.notify_whatsapp(p.user.phone_number, msg)
        
        if p.user.email:
            self.notifier.notify_email(p.user.email, "Appointment Cancelled", f"Your appointment on {appt.start_time} was cancelled.")

        return appt
