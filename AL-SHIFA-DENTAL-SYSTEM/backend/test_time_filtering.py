"""
Test to verify time filtering is working correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.tools import PatientAgentTools
from models import Patient, Doctor
import json
from datetime import datetime

db = SessionLocal()

# Get first patient
patient = db.query(Patient).first()
tools = PatientAgentTools(db, patient.id)

# Get first doctor
doctor = db.query(Doctor).first()

# Get today's date
today = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%H:%M")

print(f"Current Date: {today}")
print(f"Current Time: {current_time}")
print(f"Testing availability for Doctor ID: {doctor.id}\n")

# Call check_availability
slots_json = tools.check_availability(doctor_id=doctor.id, date=today)
slots = json.loads(slots_json)

print(f"Available Slots Returned: {slots}")
print(f"Total Slots: {len(slots)}")

# Verify no past slots
past_slots = []
for slot in slots:
    slot_time = datetime.strptime(f"{today} {slot}", "%Y-%m-%d %H:%M")
    if slot_time <= datetime.now():
        past_slots.append(slot)

if past_slots:
    print(f"\nERROR: Past slots found: {past_slots}")
else:
    print(f"\nSUCCESS: No past slots returned")

db.close()
