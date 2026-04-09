from sqlalchemy.orm import Session
from models import Treatment, TreatmentInventoryLink, InventoryItem, Doctor, Appointment

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

    def create_treatment(self, name: str, cost: float, description: str = ""):
        doctor = self.db.query(Doctor).filter(Doctor.id == self.doc_id).first()
        hospital_id = doctor.hospital_id if doctor else None
        
        existing = self.db.query(Treatment).filter(
            Treatment.doctor_id == self.doc_id, 
            Treatment.name.ilike(name)
        ).first()
        
        if existing:
            return None # Already exists
            
        new_t = Treatment(
            hospital_id=hospital_id,
            doctor_id=self.doc_id,
            name=name,
            cost=cost,
            description=description
        )
        self.db.add(new_t)
        self.db.commit()
        return new_t

    def delete_treatment(self, name: str):
        t = self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id, Treatment.name.ilike(f"%{name}%")).first()
        if not t: return False
        self.db.delete(t)
        self.db.commit()
        return True

    def link_inventory(self, treatment_name: str, item_name: str, quantity: int):
        """
        Link inventory to treatment by NAME (LLM Friendly).
        """
        # Find Treatment
        t = self.db.query(Treatment).filter(
            Treatment.doctor_id == self.doc_id,
            Treatment.name.ilike(f"%{treatment_name}%")
        ).first()
        if not t: return {"error": f"Treatment '{treatment_name}' not found."}
        
        # Find Inventory Item
        # Assuming doctor -> hospital context
        doctor = self.db.query(Doctor).filter(Doctor.id == self.doc_id).first()
        hospital_id = doctor.hospital_id if doctor else None

        item = self.db.query(InventoryItem).filter(
            InventoryItem.hospital_id == hospital_id,
            InventoryItem.name.ilike(f"%{item_name}%")
        ).first()
        
        if not item: return {"error": f"Inventory item '{item_name}' not found."}
        
        # Check existing link
        link = self.db.query(TreatmentInventoryLink).filter(
            TreatmentInventoryLink.treatment_id == t.id,
            TreatmentInventoryLink.item_id == item.id
        ).first()
        
        if link:
            link.quantity_required = quantity
        else:
            new_link = TreatmentInventoryLink(
                treatment_id=t.id,
                item_id=item.id,
                quantity_required=quantity
            )
            self.db.add(new_link)
            
        self.db.commit()
        return {"message": f"Linked {quantity} {item.unit} of {item.name} to {t.name}"}
