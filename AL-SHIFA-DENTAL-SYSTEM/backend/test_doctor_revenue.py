"""Test doctor agent revenue query directly"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.brain import ClinicAgent

db = SessionLocal()

# Assuming doctor ID 15 (d1@d.d)
agent = ClinicAgent(doctor_id=15)

print("Testing: 'how much revenue are we expecting this week?'")
print("=" * 70)

try:
    response = agent.process("how much revenue are we expecting this week?", db)
    print(f"\nAgent Response:\n{response}")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

db.close()
