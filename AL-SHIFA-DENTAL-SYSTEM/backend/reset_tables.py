import sys
import os

# Add current directory to Python path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
# FIX: Import directly from database.py, not database.db_session
from database import engine, SessionLocal 
from models import Base, User, Hospital, Doctor, Patient, InventoryItem, Treatment
import models 
import bcrypt 

def get_hash(password):
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

def seed_test_data():
    print("🌱 Seeding Test Data...")
    db = SessionLocal()
    try:
        # --- 1. DEFAULT USERS ---
        print("   > Creating Admin Org & Users...")
        
        # Org
        org = models.User(
            email="o@o.o", 
            hashed_password=get_hash("o"), 
            full_name="Default Org", 
            role="organization", 
            is_active=True
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        hospital = models.Hospital(
            name="Default Hospital", 
            address="123 Test St", 
            contact_number="111-222-3333"
        )
        db.add(hospital)
        db.commit()
        db.refresh(hospital)

        # Doctor
        doc = models.User(
            email="d@d.d", 
            hashed_password=get_hash("d"),
            full_name="Default Doctor", 
            role="doctor", 
            is_active=True,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        doc_profile = models.Doctor(
            user_id=doc.id, 
            hospital_id=hospital.id,
            specialization="General Dentist"
        )
        db.add(doc_profile)
        db.commit()

        # Patient
        pat = models.User(
            email="p@p.p", 
            hashed_password=get_hash("p"),
            full_name="Default Patient", 
            role="patient", 
            is_active=True
        )
        db.add(pat)
        db.commit()
        db.refresh(pat)

        pat_profile = models.Patient(
            user_id=pat.id, 
            date_of_birth="1990-01-01", 
            gender="Male",
            medical_history="None"
        )
        db.add(pat_profile)
        db.commit()

        # --- 2. SEED INVENTORY ---
        print("   > Seeding Inventory...")
        inv_data = [
            {"name": "Latex Exam Gloves", "qty": 50, "unit": "Box", "min": 5},
            {"name": "Face Masks", "qty": 30, "unit": "Box", "min": 5},
            {"name": "Local Anesthesia", "qty": 100, "unit": "Vial", "min": 20},
            {"name": "Dental Mirrors", "qty": 25, "unit": "Piece", "min": 5},
            {"name": "Explorer/Probes", "qty": 20, "unit": "Piece", "min": 5},
            {"name": "Cotton Rolls", "qty": 40, "unit": "Pack", "min": 5},
            {"name": "Saliva Ejectors", "qty": 200, "unit": "Piece", "min": 50},
            {"name": "Composite Resin", "qty": 10, "unit": "Syringe", "min": 3},
            {"name": "Etchant Gel", "qty": 15, "unit": "Syringe", "min": 3},
            {"name": "Bonding Agent", "qty": 8, "unit": "Bottle", "min": 2},
            {"name": "Sterilization Pouches", "qty": 5, "unit": "Box", "min": 1},
            {"name": "Disinfectant Wipes", "qty": 12, "unit": "Canister", "min": 3},
            {"name": "Dental Bibs", "qty": 500, "unit": "Piece", "min": 100},
            {"name": "Prophy Paste", "qty": 10, "unit": "Cup", "min": 2},
            {"name": "Alginate Impression", "qty": 6, "unit": "Bag", "min": 2},
            {"name": "Needles (Short)", "qty": 10, "unit": "Box", "min": 2},
            {"name": "Needles (Long)", "qty": 10, "unit": "Box", "min": 2},
            {"name": "Sutures (Silk)", "qty": 20, "unit": "Pack", "min": 5},
            {"name": "Glass Ionomer", "qty": 4, "unit": "Kit", "min": 1},
            {"name": "Topical Anesthetic", "qty": 5, "unit": "Jar", "min": 1}
        ]
        for i in inv_data:
            db.add(InventoryItem(hospital_id=hospital.id, name=i["name"], quantity=i["qty"], unit=i["unit"], min_threshold=i["min"]))

        # --- 3. SEED TREATMENTS ---
        print("   > Seeding Treatments...")
        trt_data = [
            {"name": "Root Canal Therapy", "cost": 5000, "desc": "Complete root canal procedure including anesthesia"},
            {"name": "Dental Implant", "cost": 25000, "desc": "Titanium implant placement excluding crown"},
            {"name": "Teeth Whitening", "cost": 8000, "desc": "Laser teeth whitening session"},
            {"name": "Dental Crown (Ceramic)", "cost": 12000, "desc": "High quality ceramic crown fitting"},
            {"name": "Tooth Extraction (Simple)", "cost": 1500, "desc": "Simple non-surgical extraction"},
            {"name": "Tooth Extraction (Surgical)", "cost": 4500, "desc": "Surgical extraction for impacted teeth"},
            {"name": "Scaling and Polishing", "cost": 2000, "desc": "Full mouth ultrasonic scaling and polishing"},
            {"name": "Braces Consultation", "cost": 1000, "desc": "Initial assessment for orthodontic treatment"}
        ]
        for t in trt_data:
            db.add(Treatment(doctor_id=doc_profile.id, name=t["name"], cost=t["cost"], description=t["desc"]))

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
        # 1. DROP ALL TABLES
        Base.metadata.drop_all(bind=engine)
        print("✅ Old tables dropped.")

        # 2. RECREATE TABLES
        print("🏗️  Recreating tables...")
        Base.metadata.create_all(bind=engine)
        
        # 3. SEED
        seed_test_data()
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")

if __name__ == "__main__":
    reset_tables()
