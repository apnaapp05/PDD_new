from sqlalchemy.orm import Session
from models import InventoryItem, TreatmentInventoryLink, Treatment
import pandas as pd

class InventoryTools:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doctor_id = doctor_id # Future proofing if inventory becomes doctor-specific

    def check_stock_levels(self):
        """Returns a Pandas DataFrame of current stock."""
        items = self.db.query(InventoryItem).all()
        if not items: return "No inventory found."
        
        # Create DataFrame for Analysis
        df = pd.DataFrame([{
            "Item": i.name, 
            "Qty": i.quantity, 
            "Threshold": i.min_threshold,
            "Status": "CRITICAL" if i.quantity <= i.min_threshold else "OK"
        } for i in items])
        
        return df

    def update_stock(self, item_name: str, change_by: int):
        """Updates stock. Positive to add, negative to deduct."""
        item = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(f"%{item_name}%")).first()
        if not item: return f"❌ Item '{item_name}' not found."
        
        item.quantity += change_by
        if item.quantity < 0: item.quantity = 0
        self.db.commit()
        return f"✅ Updated '{item.name}'. New Quantity: {item.quantity}"
