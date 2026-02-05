"""Check exact treatment names for doctor 1"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User, Doctor, Treatment

db = SessionLocal()

user = db.query(User).filter(User.email == "d1@d.d").first()
if user:
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if doctor:
        print(f"Doctor: {user.full_name} (ID: {doctor.id})")
        print("\nEXACT treatment names in database:")
        print("=" * 60)
        treatments = db.query(Treatment).filter(Treatment.doctor_id == doctor.id).all()
        for t in treatments:
            print(f'"{t.name}"')  # Show with quotes to see exact spelling
        
        print("\n" + "=" * 60)
        print("Test case-insensitive lookup:")
        test = db.query(Treatment).filter(
            Treatment.doctor_id == doctor.id,
            Treatment.name.ilike("root canal therapy")
        ).first()
        print(f"Found: {test.name if test else 'NOT FOUND'}")

db.close()
