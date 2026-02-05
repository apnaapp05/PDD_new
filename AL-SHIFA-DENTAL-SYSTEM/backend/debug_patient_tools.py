import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.tools import PatientAgentTools
from models import Patient, User, Doctor

def debug_tools():
    print("Debugging PatientAgentTools...")
    db = SessionLocal()
    try:
        # 1. Get a Patient
        patient = db.query(Patient).first()
        if not patient:
            print("No patient found. Run seed_test_accounts.py.")
            return
            
        print(f"Patient: {patient.user.full_name} (ID: {patient.id})")
        tools = PatientAgentTools(db, patient.id)
        
        # 2. Test list_doctors
        print("\n--- list_doctors() ---")
        docs_json = tools.list_doctors()
        docs = json.loads(docs_json)
        print(f"Found {len(docs)} doctors.")
        if len(docs) > 0:
            print("First 3:")
            for d in docs[:3]:
                print(f" - ID: {d['id']}, Name: {d['name']}, Spec: {d['specialization']}")
        else:
            print("No doctors returned!")

        # 3. Test check_availability (for first doctor)
        if docs:
            doc_id = docs[0]['id']
            print(f"\n--- check_availability(doc_id={doc_id}, date='today') ---")
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            
            slots_json = tools.check_availability(doctor_id=doc_id, date=today)
            slots = json.loads(slots_json)
            
            print(f"Slots for {today}: {slots}")
            if not slots:
                print("No slots found (might be fully booked or past working hours).")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_tools()
