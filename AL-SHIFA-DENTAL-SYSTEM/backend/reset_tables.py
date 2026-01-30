import sys
import os
import bcrypt
import random

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models import Base, User, Hospital, Doctor, Patient
import models 
import config

def get_hash(password):
    """Securely hash a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

def seed_test_data():
    print("🌱 Seeding Test Data...")
    db = SessionLocal()
    try:
        # --- 0. CREATE SYSTEM ADMIN (From Config) ---
        print(f"   > Creating System Admin ({config.ADMIN_EMAIL})...")
        
        # Check if admin exists to prevent duplicates if tables weren't dropped for some reason
        if not db.query(models.User).filter(models.User.email == config.ADMIN_EMAIL).first():
            db.add(models.User(
                email=config.ADMIN_EMAIL,
                full_name="System Admin",
                role="admin",
                is_email_verified=True,
                password_hash=get_hash(config.ADMIN_PASSWORD),
                phone_number="000-000-0000",
                address="Admin HQ"
            ))
            db.commit()

        # Define default password for all test users
        default_pwd_hash = get_hash("password")

        # --- 1. BULK ORGANIZATIONS (5) ---
        print("   > Creating 5 Organizations (org1..org5)...")
        hospitals = []
        for i in range(1, 6):
            email = f"org{i}@test.com"
            if db.query(models.User).filter(models.User.email == email).first(): continue
            
            # Create User
            org_user = models.User(
                email=email, 
                password_hash=default_pwd_hash,
                full_name=f"Organization {i}", 
                role="organization", 
                is_email_verified=True, 
                is_active=True,
                phone_number=f"555-ORG-{i:04d}",
                address=f"Org Address {i}"
            )
            db.add(org_user)
            db.commit()
            db.refresh(org_user)

            # Create Hospital Profile linked to User
            h_org = models.Hospital(
                owner_id=org_user.id, 
                name=f"Hospital {i}", 
                address=f"{i}00 Health Ave", 
                contact_number=f"555-010-{i:04d}",
                is_verified=True,
                pending_address=None 
            )
            db.add(h_org)
            db.commit()
            db.refresh(h_org)
            hospitals.append(h_org)

        # --- 2. BULK DOCTORS (10) ---
        print("   > Creating 10 Doctors (doc1..doc10)...")
        for i in range(1, 11):
            email = f"doc{i}@test.com"
            if db.query(models.User).filter(models.User.email == email).first(): continue

            # Create User
            doc_user = models.User(
                email=email, 
                password_hash=default_pwd_hash,
                full_name=f"Doctor {i}", 
                role="doctor", 
                is_email_verified=True, 
                is_active=True,
                phone_number=f"555-DOC-{i:04d}",
                address=f"Doc Address {i}"
            )
            db.add(doc_user)
            db.commit()
            db.refresh(doc_user)

            # Assign to hospital (Round Robin)
            # If i=1 -> index 0, i=6 -> index 0 (loops back)
            target_hospital = hospitals[(i - 1) % len(hospitals)] if hospitals else None

            # Create Doctor Profile
            d_prof = models.Doctor(
                user_id=doc_user.id, 
                hospital_id=target_hospital.id if target_hospital else None,
                specialization=random.choice(["General Dentist", "Orthodontist", "Oral Surgeon"]), 
                license_number=f"DOC-{i:03d}",
                is_verified=True
            )
            db.add(d_prof)
            db.commit()

        # --- 3. BULK PATIENTS (20) ---
        print("   > Creating 20 Patients (pat1..pat20)...")
        for i in range(1, 21):
            email = f"pat{i}@test.com"
            if db.query(models.User).filter(models.User.email == email).first(): continue

            # Create User
            pat_user = models.User(
                email=email, 
                password_hash=default_pwd_hash,
                full_name=f"Patient {i}", 
                role="patient", 
                is_email_verified=True, 
                is_active=True,
                phone_number=f"555-PAT-{i:04d}",
                address=f"Patient Address {i}"
            )
            db.add(pat_user)
            db.commit()
            db.refresh(pat_user)

            # Create Patient Profile
            p_prof = models.Patient(
                user_id=pat_user.id, 
                age=random.randint(18, 90), 
                gender="Male" if i % 2 == 0 else "Female",
                blood_group=random.choice(["A+", "B+", "O+", "AB+"]),
                medical_history="None"
            )
            db.add(p_prof)
            db.commit()

        print("✅ Bulk Seeding Complete!")
        print("------------------------------------------------")
        print(f" - Admin:         {config.ADMIN_EMAIL} / {config.ADMIN_PASSWORD}")
        print(" - Organizations: org1@test.com ... org5@test.com (Pass: 'password')")
        print(" - Doctors:       doc1@test.com ... doc10@test.com (Pass: 'password')")
        print(" - Patients:      pat1@test.com ... pat20@test.com (Pass: 'password')")
        print("------------------------------------------------")

    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

def reset_tables():
    print("🔄 STARTING DATABASE RESET...")
    try:
        # 1. DROP ALL TABLES
        Base.metadata.drop_all(bind=engine)
        print("✅ Old tables dropped.")

        # 2. RECREATE TABLES
        print("🏗️  Recreating tables...")
        Base.metadata.create_all(bind=engine)
        
        # 3. SEED DATA
        seed_test_data()
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")

if __name__ == "__main__":
    reset_tables()