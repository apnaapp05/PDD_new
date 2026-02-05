"""
Seed Script - Create Test Login Accounts
Creates organizations, doctors, and patients for testing
"""

from database import SessionLocal
from models import User, Hospital, Doctor, Patient
import bcrypt

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def seed_test_data():
    db = SessionLocal()
    try:
        print("🌱 Seeding test data...")
        
        # --- 1. CREATE 5 ORGANIZATIONS ---
        print("\n📍 Creating 5 Organizations...")
        hospitals = []
        for i in range(1, 6):
            # Create organization owner user
            owner_user = User(
                email=f"o{i}@o.o",
                password_hash=hash_password("o"),
                full_name=f"Organization {i} Owner",
                role="organization",
                is_email_verified=True,
                phone_number=f"555-{i:04d}",
                address=f"{i}00 Main St"
            )
            db.add(owner_user)
            db.flush()
            
            # Create hospital
            hospital = Hospital(
                name=f"Hospital {i}",
                address=f"{i}00 Main Street, City {i}",
                owner_id=owner_user.id,
                is_verified=True  # Auto-verify test hospitals
            )
            db.add(hospital)
            db.flush()
            hospitals.append(hospital)
            print(f"  ✅ o{i}@o.o (Hospital {i})")
        
        db.commit()
        print(f"✅ Created 5 organizations")
        
        # --- 2. CREATE 10 DOCTORS ---
        print("\n👨‍⚕️ Creating 10 Doctors...")
        doctors = []
        specializations = ["Orthodontist", "Endodontist", "Periodontist", "Prosthodontist", "General Dentist"]
        
        for i in range(1, 11):
            # Create doctor user
            doc_user = User(
                email=f"d{i}@d.d",
                password_hash=hash_password("d"),
                full_name=f"Dr. Doctor {i}",
                role="doctor",
                is_email_verified=True,
                phone_number=f"555-1{i:03d}",
                address=f"{i} Doctor Lane"
            )
            db.add(doc_user)
            db.flush()
            
            # Assign to hospital (distribute evenly)
            hospital = hospitals[(i - 1) % 5]
            
            # Create doctor profile
            doctor = Doctor(
                user_id=doc_user.id,
                hospital_id=hospital.id,
                specialization=specializations[(i - 1) % 5],
                license_number=f"LIC{i:06d}",
                is_verified=True
            )
            db.add(doctor)
            db.flush()
            doctors.append(doctor)
            print(f"  ✅ d{i}@d.d - {doctor.specialization} at {hospital.name}")
        
        db.commit()
        print(f"✅ Created 10 doctors")
        
        # --- 3. CREATE 20 PATIENTS ---
        print("\n🧑 Creating 20 Patients...")
        for i in range(1, 21):
            # Create patient user
            patient_user = User(
                email=f"p{i}@p.p",
                password_hash=hash_password("p"),
                full_name=f"Patient {i}",
                role="patient",
                is_email_verified=True,
                phone_number=f"555-2{i:03d}",
                address=f"{i} Patient Street"
            )
            db.add(patient_user)
            db.flush()
            
            # Create patient profile
            patient = Patient(
                user_id=patient_user.id,
                age=20 + i,
                gender="M" if i % 2 == 0 else "F"
            )
            db.add(patient)
            db.flush()
            print(f"  ✅ p{i}@p.p - Age {patient.age}, {patient.gender}")
        
        db.commit()
        print(f"✅ Created 20 patients")
        
        print("\n" + "="*60)
        print("✅ TEST DATA SEEDED SUCCESSFULLY!")
        print("="*60)
        print("\n📋 Login Credentials:")
        print("\n🏥 Organizations (5):")
        print("   Email: o1@o.o to o5@o.o")
        print("   Password: o")
        print("\n👨‍⚕️ Doctors (10):")
        print("   Email: d1@d.d to d10@d.d")
        print("   Password: d")
        print("\n🧑 Patients (20):")
        print("   Email: p1@p.p to p20@p.p")
        print("   Password: p")
        print("\n💡 Admin account will be auto-created on backend startup")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_data()
