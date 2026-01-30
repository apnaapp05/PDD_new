import sys
import os
import bcrypt
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
# Import Base directly to ensure we drop/create the right metadata
from models import Base, User, Hospital, Doctor, Patient
import models 

def get_hash(password):
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

def seed_test_data():
    print("🌱 Seeding Test Data...")
    db = SessionLocal()
    try:
        default_pwd = get_hash("password")

        # --- 1. DEFAULT USERS ---
        print("   > Creating default users (o@o.o, d@d.d, p@p.p)")
        
        # Org
        org = models.User(
            email="o@o.o", 
            password_hash=get_hash("o"), # FIXED
            full_name="Default Org", 
            role="organization", 
            is_email_verified=True,
            is_active=True,
            phone_number="123-456-7890",
            address="123 Admin St"
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        hospital = models.Hospital(
            owner_id=org.id, name="Default Hospital", 
            address="123 Test St", is_verified=True,
            phone_number="111-222-3333"
        )
        db.add(hospital)
        db.commit()
        db.refresh(hospital)

        # Doctor
        doc = models.User(
            email="d@d.d", 
            password_hash=get_hash("d"), # FIXED
            full_name="Default Doctor", 
            role="doctor", 
            is_email_verified=True,
            is_active=True,
            phone_number="987-654-3210",
            address="456 Medical Lane"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        doc_profile = models.Doctor(
            user_id=doc.id, hospital_id=hospital.id,
            specialization="General Dentist", license_number="DEF-DOC-001",
            is_verified=True
        )
        db.add(doc_profile)
        db.commit()

        # Patient
        pat = models.User(
            email="p@p.p", 
            password_hash=get_hash("p"), # FIXED
            full_name="Default Patient", 
            role="patient", 
            is_email_verified=True,
            is_active=True,
            phone_number="555-555-5555",
            address="789 Patient Blvd"
        )
        db.add(pat)
        db.commit()
        db.refresh(pat)

        pat_profile = models.Patient(
            user_id=pat.id, age=30, gender="Male"
        )
        db.add(pat_profile)
        db.commit()

        # --- 2. BULK ORGANIZATIONS (5) ---
        print("   > Creating 5 Organizations (o1..o5)")
        new_hospital_ids = []
        for i in range(1, 6):
            email = f"o{i}@o.o"
            org_user = models.User(
                email=email, password_hash=default_pwd,
                full_name=f"Org User {i}", role="organization", is_email_verified=True, is_active=True,
                phone_number=f"555-ORG-{i:04d}",
                address=f"Org Address {i}"
            )
            db.add(org_user)
            db.commit()
            db.refresh(org_user)

            h_org = models.Hospital(
                owner_id=org_user.id, name=f"Hospital {i}", 
                address=f"Street {i}, City", is_verified=True,
                phone_number=f"555-000-{i:04d}"
            )
            db.add(h_org)
            db.commit()
            db.refresh(h_org)
            new_hospital_ids.append(h_org.id)

        # --- 3. BULK DOCTORS (10) ---
        print("   > Creating 10 Doctors (d1..d10)")
        for i in range(1, 11):
            email = f"d{i}@d.d"
            doc_user = models.User(
                email=email, password_hash=default_pwd,
                full_name=f"Doctor User {i}", role="doctor", is_email_verified=True, is_active=True,
                phone_number=f"555-DOC-{i:04d}",
                address=f"Doc Address {i}"
            )
            db.add(doc_user)
            db.commit()
            db.refresh(doc_user)

            # Assign round-robin
            target_hospital_id = new_hospital_ids[(i - 1) % len(new_hospital_ids)]

            d_prof = models.Doctor(
                user_id=doc_user.id, hospital_id=target_hospital_id,
                specialization="General Dentist", license_number=f"BULK-DOC-{i:03d}",
                is_verified=True
            )
            db.add(d_prof)
            db.commit()

        # --- 4. BULK PATIENTS (20) ---
        print("   > Creating 20 Patients (p1..p20)")
        for i in range(1, 21):
            email = f"p{i}@p.p"
            pat_user = models.User(
                email=email, password_hash=default_pwd,
                full_name=f"Patient User {i}", role="patient", is_email_verified=True, is_active=True,
                phone_number=f"555-PAT-{i:04d}",
                address=f"Patient Address {i}"
            )
            db.add(pat_user)
            db.commit()
            db.refresh(pat_user)

            p_prof = models.Patient(
                user_id=pat_user.id, age=20 + i, 
                gender="Male" if i % 2 == 0 else "Female"
            )
            db.add(p_prof)
            db.commit()

        print("✅ All test data created successfully!")

    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

def reset_tables():
    print("🔄 STARTING DATABASE RESET...")
    try:
        # DROP ALL
        Base.metadata.drop_all(bind=engine)
        print("✅ Old tables dropped.")

        # RECREATE
        print("🏗️  Recreating tables...")
        Base.metadata.create_all(bind=engine)
        
        # SEED
        seed_test_data()
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")

if __name__ == "__main__":
    reset_tables()
