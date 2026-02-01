from sqlalchemy.orm import Session
from models import Patient, User, MedicalRecord

class PatientService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def find_patient(self, query: str):
        return self.db.query(Patient).join(User).filter(
            User.full_name.ilike(f"%{query}%")
        ).first()

    def get_history(self, patient_id: int):
        return self.db.query(MedicalRecord).filter(
            MedicalRecord.patient_id == patient_id
        ).all()
