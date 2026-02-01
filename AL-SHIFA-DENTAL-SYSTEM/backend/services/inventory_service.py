from sqlalchemy.orm import Session
from models import InventoryItem, Treatment

class InventoryService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def update_stock(self, item_name: str, qty_change: int):
        item = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(f"%{item_name}%")).first()
        if not item: raise ValueError(f"Item '{item_name}' not found.")
        
        if item.quantity + qty_change < 0:
            raise ValueError(f"Cannot deduct {abs(qty_change)}. Only {item.quantity} in stock.")
            
        item.quantity += qty_change
        self.db.commit()
        return item

    def get_low_stock(self):
        """REAL LOGIC: Returns items <= threshold"""
        return self.db.query(InventoryItem).filter(
            InventoryItem.quantity <= InventoryItem.min_threshold
        ).all()

    def update_treatment_price(self, treatment_name: str, new_price: float):
        t = self.db.query(Treatment).filter(
            Treatment.doctor_id == self.doc_id, 
            Treatment.name.ilike(f"%{treatment_name}%")
        ).first()
        if not t: raise ValueError(f"Treatment '{treatment_name}' not found.")
        t.cost = new_price
        self.db.commit()
        return t
