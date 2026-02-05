import sys
import os
import random
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Invoice, Appointment, Patient, User, Doctor

def seed_financial_data():
    print("💰 Seeding Financial Data (Invoices & Completed Appointments)...")
    db = SessionLocal()
    try:
        # 1. Get Doctor
        doctor = db.query(Doctor).first()
        if not doctor:
            print("❌ No doctor found. Please run seed_test_accounts.py or seed_login_users_only.py first.")
            return

        # 2. Get Patients
        patients = db.query(Patient).all()
        if not patients:
            print("❌ No patients found. Please run seed_test_accounts.py first.")
            return

        print(f"👨‍⚕️ Adding data for Dr. {doctor.user.full_name}")

        treatments = ["Root Canal", "Cleaning", "Extraction", "Whitening"]
        statuses = ["paid", "pending", "cancelled"]

        # Create 10 past appointments with invoices
        for i in range(10):
            patient = random.choice(patients)
            
            # Date in the last 30 days
            days_ago = random.randint(0, 30)
            appt_date = datetime.now() - timedelta(days=days_ago)
            
            # Create Appointment
            appt = Appointment(
                doctor_id=doctor.id,
                patient_id=patient.id,
                start_time=appt_date,
                end_time=appt_date + timedelta(minutes=30),
                status="completed",
                treatment_type=random.choice(treatments),
                notes="Seeded historical data"
            )
            db.add(appt)
            db.flush()

            # Create Invoice
            is_paid = i < 7 # 70% paid
            status = "paid" if is_paid else "pending"
            amount = random.choice([500, 1000, 1500, 2000])
            
            invoice = Invoice(
                appointment_id=appt.id,
                amount=amount,
                status=status,
                created_at=appt_date
            )
            db.add(invoice)
            print(f"  + Added Invoice: Rs. {amount} ({status}) for {appt.treatment_type}")

        db.commit()
        print("✅ Financial data seeded successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_financial_data()
