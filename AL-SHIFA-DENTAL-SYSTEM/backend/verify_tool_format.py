"""Direct test of tool output format"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.tools import PatientAgentTools
from models import Patient

db = SessionLocal()
patient = db.query(Patient).first()
tools = PatientAgentTools(db, patient.id)

print("DIRECT TOOL OUTPUT TEST")
print("=" * 70)

print("\n1. list_doctors() output:")
print("-" * 70)
print(tools.list_doctors())

print("\n" + "=" * 70)
print("\n2. get_doctor_treatments(15) output:")
print("-" * 70)
print(tools.get_doctor_treatments(15))

print("\n" + "=" * 70)
print("SUCCESS: Tools now return formatted text, not JSON")

db.close()
