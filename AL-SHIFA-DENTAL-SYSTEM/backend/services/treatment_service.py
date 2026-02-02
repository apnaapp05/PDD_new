from sqlalchemy.orm import Session
from models import Treatment, Appointment

class TreatmentService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_all_treatments(self):
        return self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id).all()

    def update_price(self, name: str, new_price: float):
        t = self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id, Treatment.name.ilike(f"%{name}%")).first()
        if not t: return None
        t.cost = new_price
        self.db.commit()
        return t

    def create_treatment(self, name: str, cost: float):
        exists = self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id, Treatment.name.ilike(name)).first()
        if exists: return None
        new_t = Treatment(name=name, cost=cost, doctor_id=self.doc_id)
        self.db.add(new_t)
        self.db.commit()
        return new_t

    def delete_treatment(self, name: str):
        t = self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id, Treatment.name.ilike(f"%{name}%")).first()
        if not t: return False
        # Safety check: Don't delete if used in appointments? (Optional, skipping for now as per 'manual logic')
        self.db.delete(t)
        self.db.commit()
        return True
