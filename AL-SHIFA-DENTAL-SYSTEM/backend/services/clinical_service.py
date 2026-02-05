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
        if not appts: return None, None
        
        # Check matching name
        targets = [
            a for a in appts 
            if a.patient and a.patient.user and patient_name.lower() in a.patient.user.full_name.lower()
        ]
        if not targets: return None, None       
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
            if t: 
                cost = t.cost
                
                # --- AUTO-DEDUCT INVENTORY ---
                # "Using a material in a Treatment automatically deducts it from stock."
                from models import InventoryItem
                deducted_log = []
                for link in t.required_items:
                    item = self.db.query(InventoryItem).filter(InventoryItem.id == link.item_id).first()
                    if item:
                        item.quantity -= link.quantity_required
                        deducted_log.append(f"{item.name} (-{link.quantity_required})")
                        
                        # Alert if critical (optional, agent can handle)
                        if item.quantity < 0: 
                             print(f"WARNING: Item {item.name} is now negative: {item.quantity}")

                print(f"DEBUG: Auto-deducted: {', '.join(deducted_log)}")
                # -----------------------------
            
        inv = Invoice(
            appointment_id=target.id,
            patient_id=target.patient_id,
            amount=cost,
            status="pending",
            created_at=datetime.now()
        )
        self.db.add(inv)
        self.db.commit()
        return target, inv

    def generate_patient_summary(self, patient_id: int) -> str:
        """
        Generates a 1-paragraph clinical summary for the patient using LLM.
        """
        from models import Patient, MedicalRecord, Appointment
        from llm import get_llm_response

        # 1. Fetch Data
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient: return "Patient not found."
        
        records = self.db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).all()
        appts = self.db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.start_time.desc()).limit(5).all()
        
        # 2. Construct Context
        history_text = "Medical History:\n"
        if not records: history_text += "No records found.\n"
        for r in records:
             history_text += f"- {r.date.strftime('%Y-%m-%d')}: {r.diagnosis} (Rx: {r.prescription})\n"
             
        recent_visits = "Recent Visits:\n"
        for a in appts:
             recent_visits += f"- {a.start_time.strftime('%Y-%m-%d')}: {a.treatment_type} ({a.status})\n"
             
        prompt = f"""
        You are an expert Clinical Dental Assistant. 
        Summarize the following patient history into a concise, professional 1-paragraph summary for the doctor.
        Highlight key treatments, recurring issues, and pending phases.
        
        Patient: {patient.user.full_name} ({patient.age} y/o {patient.gender})
        
        {history_text}
        
        {recent_visits}
        
        Summary:
        """
        
        # 3. Call LLM
        messages = [{"role": "user", "content": prompt}]
        summary = get_llm_response(messages)
        return summary
