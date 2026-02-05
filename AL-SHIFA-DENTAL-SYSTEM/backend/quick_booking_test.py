"""Simple test to verify booking works"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.patient_brain import PatientBrain
from models import Patient
from datetime import datetime, timedelta

db = SessionLocal()
patient = db.query(Patient).first()
brain = PatientBrain(db, patient.id)

tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

print("Test: User says complete booking request in one message")
print(f"Input: 'book with Dr. Doctor 1 on {tomorrow} at 15:00 for checkup'")
print("-" * 60)

response = brain.process(f"book with Dr. Doctor 1 on {tomorrow} at 15:00 for checkup")
print(f"Response: {response['response']}")
print(f"Actions: {response['actions']}")

db.close()
