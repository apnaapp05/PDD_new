
from database import SessionLocal
from models import Appointment, User, Patient
from datetime import datetime

db = SessionLocal()
# Assuming we are looking for the patient from the chat (User ID 2 usually, if seeded)
# Let's just list all appointments for all patients to be sure
appts = db.query(Appointment).order_by(Appointment.start_time).all()

print(f"{'ID':<5} {'Patient':<20} {'Doctor':<10} {'Date':<12} {'Time':<10} {'Status':<10}")
print("-" * 70)
for a in appts:
    p = db.query(Patient).filter(Patient.id == a.patient_id).first()
    p_name = p.user.full_name if p and p.user else "Unknown"
    print(f"{a.id:<5} {p_name:<20} {a.doctor_id:<10} {a.start_time.strftime('%Y-%m-%d'):<12} {a.start_time.strftime('%H:%M'):<10} {a.status:<10}")

db.close()
