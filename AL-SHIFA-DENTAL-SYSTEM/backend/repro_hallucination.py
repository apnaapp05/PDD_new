"""Simulate the failing query to see if LLM calls tools"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.patient_brain import PatientBrain
from models import Patient

db = SessionLocal()
patient = db.query(Patient).first()

print("=" * 70)
print("TEST: Final Hallucination Check")
print("=" * 70)

brain = PatientBrain(db, patient.id)
query = "book an appointment with doctor 1 at 2 PM today for Root Canal Therapy"
print(f"User: {query}\n")

# Run the process and print everything
response = brain.process(query)
print(f"Agent Response:\n{response['response']}")

db.close()
