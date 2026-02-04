
from database import SessionLocal
from agent.patient_brain import PatientBrain
from models import Patient

# Setup
db = SessionLocal()
# Get first patient
patient = db.query(Patient).first()
if not patient:
    print("❌ No patients found. Run seed_data.py first.")
    exit(1)

print(f"Testing with Patient ID: {patient.id}")
agent = PatientBrain(db, patient_id=patient.id)

queries = [
    "Who are the doctors here?",
    "Do I have any appointments?",
    "I want to cancel my appointment" # Should ask which one
]

print("--- TESTING PATIENT AGENT ---")
for q in queries:
    print(f"\nUser: {q}")
    try:
        res = agent.process(q)
        print(f"AI: {res}")
    except Exception as e:
        print(f"Error: {e}")

db.close()
