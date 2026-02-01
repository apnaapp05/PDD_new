from sqlalchemy.orm import Session
from models import Treatment, InventoryItem, TreatmentInventoryLink

class TreatmentService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def list_treatments(self):
        return self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id).all()

    def link_inventory(self, treatment_name: str, item_name: str, qty: int):
        # 1. Find Treatment
        t = self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id, Treatment.name.ilike(f"%{treatment_name}%")).first()
        if not t: raise ValueError(f"Treatment '{treatment_name}' not found.")

        # 2. Find Item
        i = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(f"%{item_name}%")).first()
        if not i: raise ValueError(f"Item '{item_name}' not found.")

        # 3. Create/Update Link
        link = self.db.query(TreatmentInventoryLink).filter_by(treatment_id=t.id, item_id=i.id).first()
        if link:
            link.quantity_required = qty
        else:
            self.db.add(TreatmentInventoryLink(treatment_id=t.id, item_id=i.id, quantity_required=qty))
        
        self.db.commit()
        return f"✅ Linked {qty} {i.unit} of {i.name} to {t.name}."
