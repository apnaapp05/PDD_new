from sqlalchemy.orm import Session
from models import Treatment

class TreatmentService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_all_treatments(self):
        return self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id).all()

    def update_price(self, name: str, new_price: float):
        t = self.db.query(Treatment).filter(
            Treatment.doctor_id == self.doc_id, 
            Treatment.name.ilike(f"%{name}%")
        ).first()
        
        if not t: return None
        t.cost = new_price
        self.db.commit()
        return t
