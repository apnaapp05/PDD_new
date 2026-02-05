"""Final verification of streamlined booking"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.patient_brain import PatientBrain
from models import Patient, Appointment
from datetime import datetime, timedelta

db = SessionLocal()
patient = db.query(Patient).first()

tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

print("FINAL VERIFICATION TEST")
print("=" * 70)

# Test 1: Complete booking in one message
print("\nTest 1: All data provided upfront")
print(f"User: 'book appointment with Dr. Doctor 1 tomorrow at 3pm for checkup'")
print("-" * 70)

brain1 = PatientBrain(db, patient.id)
response1 = brain1.process(f"book appointment with Dr. Doctor 1 on {tomorrow} at 15:00 for checkup")

print(f"\nAgent: {response1['response'][:200]}...")
print(f"Actions: {response1['actions']}")

# Check if appointment was created
appt_count_before = db.query(Appointment).filter(
    Appointment.patient_id == patient.id
).count()

print(f"\n[DATABASE] Total appointments for patient: {appt_count_before}")

print("\n" + "=" * 70)
print("Test Complete")

db.close()
