from sqlalchemy.orm import Session
from models import Treatment
import pandas as pd

class TreatmentTools:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def check_price(self, treatment_name: str):
        t = self.db.query(Treatment).filter(
            Treatment.doctor_id == self.doc_id, 
            Treatment.name.ilike(f"%{treatment_name}%")
        ).first()
        
        if not t: return f"❌ Treatment '{treatment_name}' not found in your list."
        return f"💰 **{t.name}**: Rs. {t.cost}"

    def update_price(self, treatment_name: str, new_price: float):
        t = self.db.query(Treatment).filter(
            Treatment.doctor_id == self.doc_id, 
            Treatment.name.ilike(f"%{treatment_name}%")
        ).first()
        
        if not t: return "❌ Treatment not found."
        
        old_price = t.cost
        t.cost = new_price
        self.db.commit()
        return f"✅ Updated **{t.name}** price from Rs. {old_price} to Rs. {new_price}."
