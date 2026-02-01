from sqlalchemy.orm import Session
from models import Patient, MedicalRecord, User
from datetime import datetime

class PatientTools:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def search_patient(self, name_query: str):
        """Finds a patient by joining with the User table."""
        # JOIN Patient -> User to filter by name
        patients = self.db.query(Patient).join(User).filter(
            User.full_name.ilike(f"%{name_query}%")
        ).all()
        
        if not patients: return f"❌ No patient found matching '{name_query}'."
        
        if len(patients) > 1:
            names = ", ".join([p.user.full_name for p in patients])
            return f"⚠️ Found multiple: {names}. Be more specific."
        
        p = patients[0]
        # Schema Fix: Access user.full_name and user.phone_number
        return f"👤 **{p.user.full_name}** | 📞 {p.user.phone_number or 'No Phone'} | 🎂 Age: {p.age} | 🩸 {p.blood_group or 'N/A'}"

    def get_medical_history(self, name_query: str):
        """Returns past records using the correct 'notes' column."""
        # Find patient via User table
        p = self.db.query(Patient).join(User).filter(
            User.full_name.ilike(f"%{name_query}%")
        ).first()
        
        if not p: return "❌ Patient not found."

        records = self.db.query(MedicalRecord).filter(MedicalRecord.patient_id == p.id).all()
        if not records: return f"📂 No medical records found for {p.user.full_name}."

        # Schema Fix: Use 'notes' instead of 'treatment_plan'
        history = "\n".join([f"- {r.date.strftime('%Y-%m-%d')}: {r.diagnosis} (Notes: {r.notes})" for r in records])
        return f"📋 **History for {p.user.full_name}:**\n{history}"
