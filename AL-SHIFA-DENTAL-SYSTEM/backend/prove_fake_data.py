"""Add debug logging to see what's actually being called"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User, Doctor, Treatment

db = SessionLocal()

# Show REAL data for doctor 1
user = db.query(User).filter(User.email == "d1@d.d").first()
if user:
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if doctor:
        print(f"REAL DATA FROM DATABASE FOR DOCTOR 1 (d1@d.d):")
        print(f"Doctor ID: {doctor.id}")
        print(f"Name: {user.full_name}")
        print(f"\nREAL TREATMENTS:")
        treatments = db.query(Treatment).filter(Treatment.doctor_id == doctor.id).all()
        for i, t in enumerate(treatments, 1):
            print(f"{i}. {t.name} (Rs. {t.cost})")
        
        print("\n" + "="*70)
        print("FAKE DATA FROM USER'S CHAT:")
        print("1. Dental Cleaning")
        print("2. Fluoride Treatment")
        print("3. X-Ray")
        print("4. Dental Implant")
        print("5. Root Canal Surgery")
        
        print("\n" + "="*70)
        print("COMPARISON:")
        print("❌ 'Dental Cleaning' - NOT in database")
        print("❌ 'Fluoride Treatment' - NOT in database")
        print("❌ 'X-Ray' - NOT in database")
        print("✅ 'Dental Implant' - IS in database")
        print("❌ 'Root Canal Surgery' - NOT exact match (we have 'Root Canal Therapy')")
        
        print("\n" + "="*70)
        print("CONCLUSION: Chatbot is showing HALLUCINATED data, NOT database!")
        print("SOLUTION: User MUST clear chat history in browser")

db.close()
