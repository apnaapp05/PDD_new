"""Check doctor d1@d.d details and treatments"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User, Doctor, Treatment

db = SessionLocal()

# Find doctor by email
user = db.query(User).filter(User.email == "d1@d.d").first()
if user:
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if doctor:
        print(f"Doctor Found:")
        print(f"  ID: {doctor.id}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.full_name}")
        print(f"  Specialization: {doctor.specialization}")
        
        print(f"\nTreatments offered by this doctor:")
        treatments = db.query(Treatment).filter(Treatment.doctor_id == doctor.id).all()
        if treatments:
            for t in treatments:
                print(f"  - {t.name} (Rs. {t.cost})")
        else:
            print("  No treatments found")
    else:
        print("User found but not a doctor")
else:
    print("Doctor with email d1@d.d not found")

db.close()
