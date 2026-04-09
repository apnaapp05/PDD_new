"""
Seed Script - Create ONLY Login Test Accounts
Creates one user for each role specifically for login testing.
USAGE: python seed_login_users_only.py
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User, Hospital, Doctor, Patient
import bcrypt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def seed_login_data():
    db = SessionLocal()
    try:
        print("🌱 Seeding LOGIN ONLY test data...")
        
        # Define Test Users
        test_users = [
            # (Email, Password, Role, Name, Verified)
            ("login_admin@test.com", "password123", "admin", "Login Admin", True),
            ("login_org@test.com", "password123", "organization", "Login Hospital Owner", True),
            ("login_doc@test.com", "password123", "doctor", "Login Doctor", True),
            ("login_patient@test.com", "password123", "patient", "Login Patient", True),
            ("login_unverified@test.com", "password123", "patient", "Unverified Patient", False),
        ]
        
        created_users = []

        for email, pwd, role, name, verified in test_users:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"⚠️ User {email} already exists. Skipping creation.")
                created_users.append(existing)
                continue

            # Create User
            user = User(
                email=email,
                password_hash=hash_password(pwd),
                full_name=name,
                role=role,
                is_email_verified=verified,
                phone_number=f"555-000-{role[:3]}",
                address="123 Test St"
            )
            db.add(user)
            db.flush()
            
            # Create Role Profile
            if role == "organization":
                hospital = Hospital(
                    name="Login Test Hospital",
                    address="123 Hospital Way",
                    owner_id=user.id,
                    is_verified=True
                )
                db.add(hospital)
                
            elif role == "doctor":
                # Need a hospital first
                hospital = db.query(Hospital).first()
                if not hospital:
                    # Create a dummy hospital if none exists
                    hospital = Hospital(name="Default Hospital", address="1 Main St", owner_id=user.id, is_verified=True)
                    db.add(hospital)
                    db.flush()
                    
                doctor = Doctor(
                    user_id=user.id,
                    hospital_id=hospital.id,
                    specialization="General Dentist",
                    license_number=f"LIC-{user.id}",
                    is_verified=True
                )
                db.add(doctor)
                
            elif role == "patient":
                patient = Patient(
                    user_id=user.id,
                    age=30,
                    gender="Male"
                )
                db.add(patient)
            
            created_users.append(user)
            print(f"✅ Created {role}: {email}")

        db.commit()
        
        print("\n" + "="*60)
        print("📋 LOGIN TEST CREDENTIALS")
        print("="*60)
        for email, pwd, role, name, verified in test_users:
            status = "Verified" if verified else "Unverified"
            print(f"[{role.upper()}]".ljust(15) + f" {email} / {pwd} ({status})")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_login_data()
