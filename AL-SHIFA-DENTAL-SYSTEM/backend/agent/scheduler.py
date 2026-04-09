from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from services.inventory_service import InventoryService
from services.appointment_service import AppointmentService
from database import SessionLocal
import datetime

class AgentScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.alert_queue = [] # Simple in-memory queue for chat alerts
        self.started = False

    def start(self):
        if not self.started:
            # Run inventory check every 30 minutes
            self.scheduler.add_job(self.check_low_stock, 'interval', minutes=30)
            
            # Run upcoming appointments check every 15 minutes
            self.scheduler.add_job(self.check_upcoming_appointments, 'interval', minutes=15)
            
            # Run auto-cancellation at midnight daily
            self.scheduler.add_job(self.auto_cancel_no_shows, 'cron', hour=0, minute=1)
            
            self.scheduler.start()
            self.started = True
            print("⏰ Proactive Agent Scheduler Started.")
            print("   - Low stock alerts: Every 30 min")
            print("   - Upcoming appointments: Every 15 min")
            print("   - Auto-cancel no-shows: Daily at 12:01 AM")

    def auto_cancel_no_shows(self):
        """Auto-cancel appointments from yesterday that were never started"""
        db: Session = SessionLocal()
        try:
            # We'll loop through all doctors or use a system-wide service
            # For simplicity, we'll query directly without doctor_id
            from models import Appointment, Invoice, Doctor
            from datetime import date
            
            today_start = datetime.datetime.combine(date.today(), datetime.datetime.min.time())
            
            # Find all past appointments still pending/confirmed
            stale_appointments = db.query(Appointment).filter(
                Appointment.end_time < today_start,
                Appointment.status.in_(['confirmed', 'pending'])
            ).all()
            
            cancelled_count = 0
            for appt in stale_appointments:
                appt.status = 'cancelled'
                
                # Cancel invoice
                invoice = db.query(Invoice).filter(
                    Invoice.appointment_id == appt.id,
                    Invoice.status == 'pending'
                ).first()
                
                if invoice:
                    invoice.status = 'cancelled'
                
                cancelled_count += 1
            
            if cancelled_count > 0:
                db.commit()
                print(f"✅ Auto-cancelled {cancelled_count} no-show appointments")
                
        except Exception as e:
            print(f"Auto-cancel error: {e}")
            db.rollback()
        finally:
            db.close()

    def check_low_stock(self):
        """Background task to check inventory"""
        db: Session = SessionLocal()
        try:
            # We hardcode doctor_id=1 for the automated check or loop through all
            # For simplicity in this demo, we check the first doctor found or ID 1
            inv_service = InventoryService(db, 1) 
            low_items = inv_service.get_low_stock()
            if low_items:
                msg = f"⚠️ **Alert:** You have {len(low_items)} items running low (e.g., {low_items[0].name})."
                self.alert_queue.append(msg)
        except Exception as e:
            print(f"Scheduler Error: {e}")
        finally:
            db.close()

    def check_upcoming_appointments(self):
        """Check for appointments in the next hour"""
        db: Session = SessionLocal()
        try:
            svc = AppointmentService(db, 1)
            # Logic to find appts in next 1 hour (simplified)
            # In a real app, we'd query specifically for range [now, now+1hr]
            pass 
        finally:
            db.close()

    def get_pending_alerts(self):
        """Retrieve and clear alerts"""
        alerts = self.alert_queue[:]
        self.alert_queue.clear()
        return alerts

# Global Instance
proactive_system = AgentScheduler()
