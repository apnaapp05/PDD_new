from sqlalchemy.orm import Session
from models import InventoryItem

class InventoryService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_low_stock(self):
        return self.db.query(InventoryItem).filter(InventoryItem.quantity <= InventoryItem.min_threshold).all()

    def get_all_items(self):
        return self.db.query(InventoryItem).all()

    def update_stock(self, item_name: str, qty: int):
        item = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(f"%{item_name}%")).first()
        if not item: return None
        item.quantity += qty
        self.db.commit()
        return item

    def create_item(self, name: str, quantity: int, threshold: int = 10):
        exists = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(name)).first()
        if exists: return None
        new_item = InventoryItem(name=name, quantity=quantity, min_threshold=threshold, doctor_id=self.doc_id)
        self.db.add(new_item)
        self.db.commit()
        return new_item

    def set_threshold(self, name: str, threshold: int):
        item = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(f"%{name}%")).first()
        if not item: return None
        item.min_threshold = threshold
        self.db.commit()
        return item
