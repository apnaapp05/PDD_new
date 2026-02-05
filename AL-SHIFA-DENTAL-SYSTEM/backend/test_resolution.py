"""Check doctor resolution logic"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User, Doctor

db = SessionLocal()
val = "doctor 1"

print(f"Searching for: '{val}'")

# Current logic
from sqlalchemy import or_
doctor = db.query(Doctor).join(User, Doctor.user_id == User.id).filter(
    User.full_name.ilike(f"%{val}%")
).first()

if doctor:
    print(f"✓ Found: ID {doctor.id}, Name: {doctor.user.full_name}")
else:
    print("✗ Not found by name")
    
# Try with Dr prefix
val2 = "Dr. Doctor 1"
doctor2 = db.query(Doctor).join(User, Doctor.user_id == User.id).filter(
    User.full_name.ilike(f"%{val2}%")
).first()

if doctor2:
    print(f"✓ Found with Dr prefix: ID {doctor2.id}")

db.close()
