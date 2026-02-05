
import sys
import os
from datetime import datetime, timedelta
# Init DB
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
import models
from services.appointment_service import AppointmentService
from services.inventory_service import InventoryService
from notifications.service import NotificationService
from unittest.mock import MagicMock

# Mock Notification Service to avoid actual emails
NotificationService.send_shortage_forecast_alert = MagicMock()
mock_send = NotificationService.send_shortage_forecast_alert

def clean_db(db):
    try:
        db.query(models.Invoice).delete()
        db.query(models.Appointment).delete()
        db.query(models.TreatmentInventoryLink).delete()
        db.query(models.Treatment).delete()
        db.query(models.InventoryItem).delete()
        db.query(models.Doctor).delete()
        db.query(models.Hospital).delete()
        db.query(models.Patient).delete()
        db.query(models.User).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Cleanup failed: {e}")

def verify_proactive_alert():
    db = SessionLocal()
    clean_db(db)
    
    print("🚀 Starting Proactive Alert Verification...")

    try:
        # 1. Setup User/Doctor/Patient
        u_doc = models.User(email="doc@test.com", full_name="Dr. Test", role="doctor", is_email_verified=True)
        u_pat = models.User(email="pat@test.com", full_name="Patient Test", role="patient", is_email_verified=True)
        db.add_all([u_doc, u_pat])
        db.commit()

        hosp = models.Hospital(owner_id=u_doc.id, name="Test Clinic", is_verified=True)
        db.add(hosp)
        db.commit()

        doc = models.Doctor(user_id=u_doc.id, hospital_id=hosp.id, specialization="General", is_verified=True)
        pat = models.Patient(user_id=u_pat.id, age=30, gender="M")
        db.add_all([doc, pat])
        db.commit()
        
        # 2. Setup Inventory (Gloves: 10 pairs)
        inv_service = InventoryService(db, doc.id)
        gloves = models.InventoryItem(hospital_id=hosp.id, name="Test Gloves", quantity=10, unit="Pairs", min_threshold=2)
        db.add(gloves)
        db.commit()
        print(f"📦 Inventory initialized: {gloves.name} = {gloves.quantity}")

        # 3. Setup Treatment (Needs 4 pairs per session)
        treat = models.Treatment(hospital_id=hosp.id, doctor_id=doc.id, name="Surgery", cost=100)
        db.add(treat)
        db.commit()
        
        link = models.TreatmentInventoryLink(treatment_id=treat.id, item_id=gloves.id, quantity_required=4)
        db.add(link)
        db.commit()
        
        # 4. Book Appointments
        # Appt 1: Needs 4. Remaining virtual stock: 6. (Alert? No, 10 > 4)
        print("\n📅 Booking Appointment 1 (Needs 4)...")
        # Start tomorrow 10am
        t1 = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        appt_service = AppointmentService(db, doc.id)
        appt_service.book_appointment(pat.id, t1, "10:00", "Surgery")
        
        if mock_send.called:
             print("❌ Unexpected Alert triggered on Appt 1!")
        else:
             print("✅ No alert yet (Expected).")

        # Appt 2: Needs 4. Total Needed: 8. Remaining virtual: 2. (Alert? No, 10 > 8)
        print("\n📅 Booking Appointment 2 (Needs 4)...")
        # Day after tomorrow
        t2 = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        appt_service.book_appointment(pat.id, t2, "10:00", "Surgery", allow_multiple=True)

        if mock_send.called:
             print("❌ Unexpected Alert triggered on Appt 2!")
        else:
             print("✅ No alert yet (Expected).")

        # Appt 3: Needs 4. Total Needed: 12. Stock: 10. (Alert? YES! 12 > 10)
        print("\n📅 Booking Appointment 3 (Needs 4)...")
        # 3 days from now
        t3 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        appt_service.book_appointment(pat.id, t3, "10:00", "Surgery", allow_multiple=True)

        # 5. Verify Mock Call
        if mock_send.called:
            print("✅ SUCCESS! Shortage Forecast Alert Triggered.")
            args = mock_send.call_args[1]
            print(f"   📧 Email sent to: {args.get('doctor_email') or mock_send.call_args[0][0]}")
            print(f"   ⚠️  Item: {args.get('item_name') or mock_send.call_args[0][2]}")
            needed = args.get('needed_quantity') or mock_send.call_args[0][4]
            print(f"   📉 Needed: {needed} (Stock: 10)")
        else:
            print("❌ FAILURE! Alert NOT triggered.")

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        clean_db(db)
        db.close()

if __name__ == "__main__":
    verify_proactive_alert()
