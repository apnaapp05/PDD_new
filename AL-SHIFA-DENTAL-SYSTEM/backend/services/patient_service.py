from sqlalchemy.orm import Session
from models import Patient, User, MedicalRecord

class PatientService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def find_patient(self, query: str):
        # Allow search by name, email, or exact ID
        if query.isdigit():
             return self.db.query(Patient).filter(Patient.id == int(query)).first()
             
        return self.db.query(Patient).join(User).filter(
            User.full_name.ilike(f"%{query}%")
        ).first()

    def search_patients(self, query: str):
        """
        Search for patients by name. Returns a list of matches.
        """
        patients = self.db.query(Patient).join(User).filter(
            User.full_name.ilike(f"%{query}%")
        ).all()
        
        results = []
        for p in patients:
            results.append({
                "id": p.id,
                "name": p.user.full_name,
                "age": p.age,
                "gender": p.gender,
                "phone": p.user.phone_number
            })
        return results

    def get_patient_details(self, patient_id: int):
        """
        Get full details including history and files.
        """
        p = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not p: return None
        
        history = self.get_history(patient_id)
        files = self.db.query(models.PatientFile).filter(models.PatientFile.patient_id == patient_id).all()
        
        return {
            "id": p.id,
            "name": p.user.full_name,
            "age": p.age,
            "gender": p.gender,
            "contact": {
                "email": p.user.email,
                "phone": p.user.phone_number
            },
            "history": [
                {
                    "date": h.date.strftime("%Y-%m-%d"),
                    "diagnosis": h.diagnosis,
                    "notes": h.notes
                } for h in history
            ],
            "files": [f.filename for f in files]
        }

    def get_history(self, patient_id: int):
        return self.db.query(MedicalRecord).filter(
            MedicalRecord.patient_id == patient_id
        ).all()

    def add_medical_record(self, patient_id: int, diagnosis: str, notes: str):
        """
        Add a new clinical note/diagnosis.
        """
        record = MedicalRecord(
            patient_id=patient_id,
            doctor_id=self.doc_id,
            diagnosis=diagnosis,
            notes=notes,
            prescription="" # Default empty for now
        )
        self.db.add(record)
        self.db.commit()
        return record
