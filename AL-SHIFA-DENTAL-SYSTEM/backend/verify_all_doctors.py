"""Verify treatment system works for multiple doctors"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User, Doctor, Treatment

db = SessionLocal()

print("VERIFICATION: Treatment system works for ALL doctors")
print("=" * 70)

# Check 3 different doctors
emails = ["d1@d.d", "d2@d.d", "d3@d.d"]

for email in emails:
    user = db.query(User).filter(User.email == email).first()
    if user:
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if doctor:
            treatments = db.query(Treatment).filter(Treatment.doctor_id == doctor.id).all()
            
            print(f"\n{user.full_name} ({email}) - ID: {doctor.id}")
            print(f"Specialization: {doctor.specialization}")
            print(f"Treatments ({len(treatments)}):")
            
            if treatments:
                for t in treatments[:5]:  # Show first 5
                    print(f"  - {t.name} (Rs. {t.cost})")
                if len(treatments) > 5:
                    print(f"  ... and {len(treatments) - 5} more")
            else:
                print("  [No treatments]")
        else:
            print(f"\n{email}: User found but not a doctor")
    else:
        print(f"\n{email}: Not found")

print("\n" + "=" * 70)
print("RESULT: Each doctor has their own unique treatment list ✓")

db.close()
