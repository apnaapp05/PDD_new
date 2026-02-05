"""Test formatted text output for lists"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.patient_brain import PatientBrain
from models import Patient

db = SessionLocal()
patient = db.query(Patient).first()

print("=" * 70)
print("TEST: Formatted Text Display")
print("=" * 70)

brain = PatientBrain(db, patient.id)

print("\n1. Testing doctor list display:")
print("-" * 70)
response1 = brain.process("show me available doctors")
print(f"Agent:\n{response1['response']}")

print("\n" + "=" * 70)
print("\n2. Testing treatment list display:")
print("-" * 70)
response2 = brain.process("what treatments does doctor 1 offer?")
print(f"Agent:\n{response2['response']}")

print("\n" + "=" * 70)

db.close()
