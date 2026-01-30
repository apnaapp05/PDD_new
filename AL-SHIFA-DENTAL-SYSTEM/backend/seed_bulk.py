import sys
import os
import random
from datetime import datetime

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models
import bcrypt

def get_hash(password):
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

def seed_bulk_data():
    db = SessionLocal()
    try:
        print("🌱 Starting Bulk Seeding (Orgs, Doctors, Patients)...")
        print("   (ℹ️  Default Password for all accounts: 'password')")
        
        default_password_hash = get_hash("password")

        # --- 1. Create 5 Organizations & Hospitals ---
        hospitals = []
        print(f"   > Creating 5 Organizations...")
        for i in range(1, 6):
            email = f"org{i}@test.com"
            # Check if exists
            if db.query(models.User).filter(models.User.email == email).first():
                print(f"     Skipping {email} (already exists)")
                continue

            # Create User (Organization)
            # NOTE: Using 'password_hash' to match the fixed models.py. 
            # If your models.py still uses 'hashed_password', rename this field.
            user = models.User(
                email=email,
                password_hash=default_password_hash, 
                full_name=f"Organization {i}",
                role="organization",
                is_active=True,
                is_email_verified=True,
                phone_number=f"555-000{i}",
                address=f"{i}00 Health Ave"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Create Hospital Profile linked to User
            hospital = models.Hospital(
                owner_id=user.id,
                name=f"Hospital {i}",
                address=f"{i}00 Health Ave",
                contact_number=f"555-010{i}",
                is_verified=True
            )
            db.add(hospital)
            db.commit()
            db.refresh(hospital)
            hospitals.append(hospital)

        # Re-query hospitals if some were skipped to ensure we have a list for doctors
        if not hospitals:
            hospitals = db.query(models.Hospital).all()

        # --- 2. Create 10 Doctors (Distributed) ---
        print(f"   > Creating 10 Doctors...")
        for i in range(1, 11):
            email = f"doc{i}@test.com"
            if db.query(models.User).filter(models.User.email == email).first():
                continue

            # Create User (Doctor)
            user = models.User(
                email=email,
                password_hash=default_password_hash,
                full_name=f"Doctor {i}",
                role="doctor",
                is_active=True,
                is_email_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Assign to hospital (Round Robin)
            if hospitals:
                h_index = (i - 1) % len(hospitals)
                assigned_hospital = hospitals[h_index]
            else:
                print("     ⚠️ No hospitals found to assign doctors!")
                assigned_hospital = None

            # Create Doctor Profile
            doctor = models.Doctor(
                user_id=user.id,
                hospital_id=assigned_hospital.id if assigned_hospital else None,
                specialization=random.choice(["General Dentist", "Orthodontist", "Oral Surgeon", "Periodontist"]),
                license_number=f"D-LIC-{1000+i}",
                is_verified=True
            )
            db.add(doctor)
            db.commit()

        # --- 3. Create 20 Patients ---
        print(f"   > Creating 20 Patients...")
        for i in range(1, 21):
            email = f"pat{i}@test.com"
            if db.query(models.User).filter(models.User.email == email).first():
                continue

            # Create User (Patient)
            user = models.User(
                email=email,
                password_hash=default_password_hash,
                full_name=f"Patient {i}",
                role="patient",
                is_active=True,
                is_email_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Create Patient Profile
            patient = models.Patient(
                user_id=user.id,
                age=random.randint(18, 80),
                gender=random.choice(["Male", "Female"]),
                medical_history="None"
            )
            db.add(patient)
            db.commit()

        print("✅ Bulk Seeding Complete!")
        print("------------------------------------------------")
        print("Login Credentials (All passwords: 'password'):")
        print(" - Organizations: org1@test.com ... org5@test.com")
        print(" - Doctors:       doc1@test.com ... doc10@test.com")
        print(" - Patients:      pat1@test.com ... pat20@test.com")
        print("------------------------------------------------")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_bulk_data()
