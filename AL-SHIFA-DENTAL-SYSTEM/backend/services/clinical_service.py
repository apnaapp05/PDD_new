from sqlalchemy.orm import Session
from models import Appointment, MedicalRecord, Patient, User, Invoice, Treatment, TreatmentInventoryLink, InventoryItem
from datetime import datetime

class ClinicalService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def start_appointment(self, patient_name: str):
        # Existing Logic
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
        # Existing Logic
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

    def complete_appointment(self, appointment_id: int = None, patient_name: str = None):
        """
        Quadruple Action: Complete -> Bill -> Deduct Stock -> Pay
        """
        # 1. Find Appointment (by ID or Name)
        appt = None
        if appointment_id:
             appt = self.db.query(Appointment).filter(Appointment.id == appointment_id).first()
        elif patient_name:
             p = self.db.query(Patient).join(User).filter(User.full_name.ilike(f"%{patient_name}%")).first()
             if p:
                 appt = self.db.query(Appointment).filter(
                    Appointment.patient_id == p.id, 
                    Appointment.status == "in_progress"
                 ).first()
        
        if not appt: raise ValueError("Appointment not found or not in progress.")

        # 2. Find Treatment Price & Items
        treatment = self.db.query(Treatment).filter(
            Treatment.name == appt.treatment_type,
            Treatment.doctor_id == self.doc_id
        ).first()

        cost = treatment.cost if treatment else 0.0

        # 3. Deduct Inventory (The Recipe)
        deducted_log = []
        if treatment:
            links = self.db.query(TreatmentInventoryLink).filter(TreatmentInventoryLink.treatment_id == treatment.id).all()
            for link in links:
                item = self.db.query(InventoryItem).filter(InventoryItem.id == link.item_id).first()
                if item and item.quantity >= link.quantity_required:
                    item.quantity -= link.quantity_required
                    deducted_log.append(f"{item.name} (-{link.quantity_required})")
        
        # 4. Generate Invoice (Paid)
        invoice = Invoice(
            appointment_id=appt.id,
            patient_id=appt.patient_id,
            amount=cost,
            status="paid", # Auto-pay for simplicity as requested
            created_at=datetime.now()
        )
        self.db.add(invoice)

        # 5. Complete Status
        appt.status = "completed"
        self.db.commit()

        stock_msg = f" (Stock used: {', '.join(deducted_log)})" if deducted_log else ""
        return f"✅ Completed. Invoice of Rs. {cost} generated & paid.{stock_msg}"
