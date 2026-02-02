from sqlalchemy.orm import Session
from models import Appointment, Patient, User, Invoice
from datetime import datetime, timedelta
from notifications.service import NotificationService

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

    # --- 1. BOOKING LOGIC (Preserved) ---
    def book_appointment(self, patient_id: int, date_str: str, time_str: str, treatment: str):
        try:
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=30)
            
            # Check for overlaps
            self._check_overlap(start_dt, end_dt)

            # Create Appointment
            appt = Appointment(
                doctor_id=self.doc_id,
                patient_id=patient_id,
                start_time=start_dt,
                end_time=end_dt,
                status="confirmed",
                treatment_type=treatment,
                notes="AI Booking"
            )
            self.db.add(appt)
            self.db.flush() 

            # Create Invoice
            invoice = Invoice(
                appointment_id=appt.id,
                patient_id=patient_id,
                amount=500.0, # Default fee
                status="pending"
            )
            self.db.add(invoice)
            
            self.db.commit()
            self.db.refresh(appt)
            return appt
            
        except ValueError as e:
            self.db.rollback()
            raise e

    # --- 2. CANCEL LOGIC (New) ---
    def get_patient_upcoming(self, patient_id: int):
        """Fetch confirmed/pending appointments in the future"""
        return self.db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.start_time > datetime.now(),
            Appointment.status.in_(["confirmed", "pending"])
        ).order_by(Appointment.start_time).all()

    def cancel_appointment_by_id(self, appointment_id: int, patient_id: int):
        appt = self.db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        ).first()
        
        if not appt:
            raise ValueError("Appointment not found or access denied.")
            
        appt.status = "cancelled"
        self.db.commit()
        return appt

    # --- 3. RESCHEDULE LOGIC (New) ---
    def reschedule_appointment(self, appointment_id: int, patient_id: int, new_date: str, new_time: str):
        """Updates the time of an existing appointment"""
        appt = self.db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        ).first()
        
        if not appt:
            raise ValueError("Appointment not found.")

        try:
            start_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=30)
            
            # Check availability (excluding current appointment ID to allow minor shifts)
            overlap = self.db.query(Appointment).filter(
                Appointment.doctor_id == appt.doctor_id,
                Appointment.start_time < end_dt,
                Appointment.end_time > start_dt,
                Appointment.status != 'cancelled',
                Appointment.id != appointment_id 
            ).first()
            
            if overlap:
                raise ValueError("The new slot is already taken.")
                
            appt.start_time = start_dt
            appt.end_time = end_dt
            self.db.commit()
            return appt
            
        except ValueError as e:
            raise e

    # --- HELPER ---
    def _check_overlap(self, start_dt, end_dt):
        overlap = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.start_time < end_dt,
            Appointment.end_time > start_dt,
            Appointment.status != 'cancelled'
        ).first()
        if overlap: raise ValueError(f"Slot is already occupied.")

    # Legacy/Doctor block
    def block_slot(self, date_str: str, time_str: str, reason: str):
        # Implementation for doctor blocking (simplified here)
        return self.book_appointment(None, date_str, time_str, "Blocked") 
