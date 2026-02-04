
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agent.patient_brain import PatientBrain
from database import Base, DATABASE_URL
from dotenv import load_dotenv
import os

load_dotenv()

# Setup DB
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Initialize Brain
brain = PatientBrain(db, patient_id=1) 

print("--- REPRODUCING BUG ---")

# Step 1: Init
msg1 = "I want to book an appointment"
print(f"\nUser: {msg1}")
res1 = brain.process(msg1)
print(f"AI: {res1}")

# Step 2: Select Doctor
msg2 = "Doctor 1"
print(f"\nUser: {msg2}")
res2 = brain.process(msg2)
print(f"AI: {res2}")

# Step 3: Check Availability
msg3 = "What time is free today?"
print(f"\nUser: {msg3}")
res3 = brain.process(msg3)
print(f"AI: {res3}")
