"""Test email-based doctor selection and treatment display"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.patient_brain import PatientBrain
from models import Patient
from datetime import datetime, timedelta

db = SessionLocal()
patient = db.query(Patient).first()

tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

print("=" * 70)
print("TEST 1: Email-based Doctor Selection")
print("=" * 70)
print(f"User: 'book with d1@d.d tomorrow at 3pm'")
print("-" * 70)

brain1 = PatientBrain(db, patient.id)
response1 = brain1.process(f"book with d1@d.d on {tomorrow} at 15:00")
print(f"\nAgent: {response1['response'][:300]}...")
print(f"Actions: {response1['actions'][:5] if len(response1['actions']) > 5 else response1['actions']}")

print("\n" + "=" * 70)
print("TEST 2: Treatment Display for Doctor")
print("=" * 70)
print("User: 'show me treatments from d2@d.d'")
print("-" * 70)

brain2 = PatientBrain(db, patient.id)
response2 = brain2.process("show me treatments from d2@d.d")
print(f"\nAgent: {response2['response'][:300]}...")
print(f"Actions (treatments): {response2['actions'][:5] if len(response2['actions']) > 5 else response2['actions']}")

print("\n" + "=" * 70)
print("Tests Complete")

db.close()
