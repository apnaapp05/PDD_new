from datetime import datetime
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
        
        # Update Quantity
        item.quantity += qty
        self.db.commit()
        
        # Check Low Stock Threshold & Notify
        if item.quantity <= item.min_threshold:
            self._trigger_low_stock_alert(item)
            
        return item

    def consume_item(self, item_id: int, quantity_used: int):
        """
        Deduct stock for usage and check thresholds.
        """
        item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item: return None
        
        item.quantity = max(0, item.quantity - quantity_used)
        self.db.commit()
        
        if item.quantity <= item.min_threshold:
            self._trigger_low_stock_alert(item)
            
        return item

    def _trigger_low_stock_alert(self, item: InventoryItem):
        """Helper to send alert if config matches"""
        try:
            from notifications.service import NotificationService
            from models import Doctor, User
            
            # Find the doctor associated with this inventory item's hospital/context
            # Assuming doctor_id passed to service init is the relevant one to notify
            doctor = self.db.query(Doctor).filter(Doctor.id == self.doc_id).first()
            if doctor and doctor.user:
                notifier = NotificationService()
                notifier.send_low_stock_notification(
                    doctor_email=doctor.user.email,
                    doctor_name=doctor.user.full_name,
                    item_name=item.name,
                    current_quantity=item.quantity,
                    min_threshold=item.min_threshold
                )
                print(f"📧 Low stock alert sent for {item.name}")
        except Exception as e:
            print(f"Failed to send low stock alert: {e}")

    def create_item(self, name: str, quantity: int, unit: str = "Pcs", threshold: int = 10):
        exists = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(name)).first()
        if exists: return None
        
        # Get Hospital ID from Doctor
        from models import Doctor
        doctor = self.db.query(Doctor).filter(Doctor.id == self.doc_id).first()
        hospital_id = doctor.hospital_id if doctor else None
        
        new_item = InventoryItem(name=name, quantity=quantity, unit=unit, min_threshold=threshold, hospital_id=hospital_id)
        self.db.add(new_item)
        self.db.commit()
        return new_item

    def update_quantity(self, item_id: int, new_qty: int):
        """
        Set absolute quantity (e.g. for correcting stock count).
        """
        item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item: return None
        item.quantity = new_qty
        item.last_updated = datetime.utcnow()
        self.db.commit()
        
        # Check Low Stock Threshold & Notify
        if item.quantity <= item.min_threshold:
            self._trigger_low_stock_alert(item)
            
        return item

    def set_threshold(self, name: str, threshold: int):
        item = self.db.query(InventoryItem).filter(InventoryItem.name.ilike(f"%{name}%")).first()
        if not item: return None
        item.min_threshold = threshold
        self.db.commit()
        return item

    def recalculate_thresholds(self):
        """
        Dynamic Inventory Prediction:
        1. Look at last 30 days of completed treatments.
        2. Calculate total usage of each item.
        3. Set Threshold = (Avg Daily Usage * 7) + Buffer.
        """
        from datetime import datetime, timedelta
        from models import Appointment, Treatment, TreatmentInventoryLink

        # 1. Get completed appointments in last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        completed_appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.status == 'completed',
            Appointment.start_time >= thirty_days_ago
        ).all()

        # 2. Map Usage
        usage_map = {} # {item_id: total_qty_used}
        
        for appt in completed_appts:
            if not appt.treatment_type: continue
            
            # Find linked treatment logic (assuming fuzzy match or direct link)
            # In production, Appointment should have treatment_id. Here we search by name.
            treatment = self.db.query(Treatment).filter(
                Treatment.doctor_id == self.doc_id,
                Treatment.name.ilike(appt.treatment_type)
            ).first()
            
            if treatment:
                for link in treatment.required_items:
                    current = usage_map.get(link.item_id, 0)
                    usage_map[link.item_id] = current + link.quantity_required

        # 3. Update Thresholds
        updates = []
        for item_id, total_used in usage_map.items():
            daily_avg = total_used / 30.0
            new_threshold = int(daily_avg * 7) # 1 Week Safety Stock
            if new_threshold < 5: new_threshold = 5 # Minimum sanity floor
            
            item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
            if item:
                old = item.min_threshold
                item.min_threshold = new_threshold
                updates.append(f"{item.name}: {old} -> {new_threshold}")
        
        self.db.commit()
        return "\n".join(updates) if updates else "No threshold changes needed based on recent usage."

    def get_daily_usage_rate(self, item_id: int) -> float:
        """
        Calculate average items used per day over last 30 days.
        """
        from datetime import datetime, timedelta
        from models import Appointment, Treatment, TreatmentInventoryLink
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        completed_appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.status == 'completed',
            Appointment.start_time >= thirty_days_ago
        ).all()
        
        total_used = 0
        for appt in completed_appts:
            if not appt.treatment_type: continue
            treatment = self.db.query(Treatment).filter(
                Treatment.doctor_id == self.doc_id,
                Treatment.name.ilike(appt.treatment_type)
            ).first()
            
            if treatment:
                for link in treatment.required_items:
                    if link.item_id == item_id:
                        total_used += link.quantity_required
                        
        return total_used / 30.0

    def get_projected_usage(self, days=7):
        """
        Calculate projected inventory usage based on confirmed/pending appointments 
        for the next X days.
        Returns: {item_id: quantity_needed}
        """
        from datetime import datetime, timedelta
        from models import Appointment, Treatment, TreatmentInventoryLink

        end_date = datetime.now() + timedelta(days=days)
        
        # Get upcoming appointments
        upcoming_appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.status.in_(['confirmed', 'pending']),
            Appointment.start_time >= datetime.now(),
            Appointment.start_time <= end_date
        ).all()

        projected_usage = {}

        for appt in upcoming_appts:
            if not appt.treatment_type: continue
            
            # Find linked treatment
            treatment = self.db.query(Treatment).filter(
                Treatment.doctor_id == self.doc_id,
                Treatment.name.ilike(appt.treatment_type)
            ).first()

            if treatment:
                for link in treatment.required_items:
                    current = projected_usage.get(link.item_id, 0)
                    projected_usage[link.item_id] = current + link.quantity_required
        
        return projected_usage

    def check_stock_health_for_new_booking(self, treatment_name: str):
        """
        Called after a new booking. Checks if this specific treatment tips the balance
        into a shortage for any item in the next 7 days.
        """
        from models import Treatment
        
        # 1. Get Treatment details
        treatment = self.db.query(Treatment).filter(
            Treatment.doctor_id == self.doc_id, 
            Treatment.name.ilike(treatment_name)
        ).first()
        
        if not treatment: return
        
        # 2. Get Global Projection (including the just-booked appointment)
        projected = self.get_projected_usage(days=7)
        
        # 3. Check specific items involved in THIS treatment
        for link in treatment.required_items:
            item = link.item
            if not item: continue
            
            total_needed = projected.get(item.id, 0)
            
            # CONFLICT CONDITION:
            # If total usage > quantity AND (total usage - this appt usage) <= quantity
            # Meaning: "We were fine before, but THIS appointment broke the camel's back"
            # This logic avoids spamming alerts for existing shortages every time.
            
            if total_needed > item.quantity:
                # Check if it was ALREADY short before this
                previous_need = total_needed - link.quantity_required
                
                # Only alert if this is the *tipping point* or if we want to be safe, alert anyway
                # Let's alert if we are short now
                if previous_need <= item.quantity:
                     self._trigger_forecast_alert(item, total_needed, "Next 7 Days")

    def _trigger_forecast_alert(self, item: InventoryItem, needed: int, horizon: str):
        try:
             from notifications.service import NotificationService
             from models import Doctor
             
             doctor = self.db.query(Doctor).filter(Doctor.id == self.doc_id).first()
             if doctor and doctor.user:
                 notifier = NotificationService()
                 notifier.send_shortage_forecast_alert(
                     doctor_email=doctor.user.email,
                     doctor_name=doctor.user.full_name,
                     item_name=item.name,
                     current_quantity=item.quantity,
                     needed_quantity=needed,
                     date_range=horizon
                 )
                 print(f"📧 Forecast Alert sent for {item.name}")
        except Exception as e:
             print(f"Failed to send forecast alert: {e}")
