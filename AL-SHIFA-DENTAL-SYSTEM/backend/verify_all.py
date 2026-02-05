"""
Quick Fix: Verify all existing hospitals
"""

from database import SessionLocal
from models import Hospital, Doctor

db = SessionLocal()

try:
    # Verify all hospitals
    hospitals = db.query(Hospital).all()
    for h in hospitals:
        h.is_verified = True
    
    # Verify all doctors
    doctors = db.query(Doctor).all()
    for d in doctors:
        d.is_verified = True
    
    db.commit()
    print(f"✅ Verified {len(hospitals)} hospitals")
    print(f"✅ Verified {len(doctors)} doctors")
    
except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()
