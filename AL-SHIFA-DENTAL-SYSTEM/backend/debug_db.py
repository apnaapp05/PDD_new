from database import SessionLocal
import models

db = SessionLocal()

print("\n" + "="*60)
print("🔍 DATABASE DIAGNOSTIC REPORT")
print("="*60)

# 1. CHECK PATIENTS
print(f"\n[👥 REGISTERED PATIENTS]")
pats = db.query(models.Patient).all()
if not pats:
    print("❌ NO PATIENTS FOUND. (You must register a patient first!)")
else:
    for p in pats:
        u = db.query(models.User).filter(models.User.id == p.user_id).first()
        name = u.full_name if u else "Unknown"
        print(f"ID: {p.id} | Name: '{name}'")

# 2. CHECK APPOINTMENTS
print(f"\n[📅 ALL APPOINTMENTS]")
appts = db.query(models.Appointment).all()
if not appts:
    print("❌ DATABASE IS EMPTY (No appointments stored).")
else:
    for a in appts:
        print(f"ID: {a.id} | Date: {a.start_time} | Status: {a.status} | PatientID: {a.patient_id} | Type: {a.treatment_type}")

print("\n" + "="*60 + "\n")
