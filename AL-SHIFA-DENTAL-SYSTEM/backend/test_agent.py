
import os
import sys
from dotenv import load_dotenv

# Force load .env
load_dotenv()

print(f"DEBUG: GEMINI_API_KEY from env: {os.getenv('GEMINI_API_KEY')[:5]}...")

from database import SessionLocal
try:
    print("DEBUG: Importing ClinicAgent...")
    from agent.brain import ClinicAgent
    print("DEBUG: Imported ClinicAgent.")
except Exception as e:
    print(f"DEBUG: Import Error: {e}")
    sys.exit(1)

# Setup
print("DEBUG: Creating DB Session...")
db = SessionLocal()
print("DEBUG: DB Session created.")

try:
    print("DEBUG: Initializing ClinicAgent...")
    agent = ClinicAgent(db, doctor_id=1)
    print("DEBUG: ClinicAgent initialized.")
except Exception as e:
    print(f"DEBUG: Init Error: {e}")
    sys.exit(1)

queries = [
    "What treatments do we offer?",
    "Check if we have gloves in stock",
    "How much money have we made?"
]

print("--- TESTING AI AGENT ---")
for q in queries:
    print(f"\nUser: {q}")
    try:
        res = agent.process(q)
        print(f"AI: {res}")
    except Exception as e:
        print(f"Error: {e}")

db.close()
