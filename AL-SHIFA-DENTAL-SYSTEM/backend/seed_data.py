
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import bcrypt

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def seed():
    db = SessionLocal()
    try:
        print("🌱 Seeding Organizations...")
        orgs = []
        for i in range(1, 6):
            email = f"o{i}@o.o"
            if db.query(models.User).filter(models.User.email == email).first():
                print(f"  Skipping {email} (exists)")
                continue
            
            user = models.User(
                email=email,
                full_name=f"Org {i}",
                role="organization",
                is_email_verified=True,
                password_hash=get_password_hash("o"),
                address=f"Org Address {i}"
            )
            db.add(user)
            db.flush()
            
            hospital = models.Hospital(
                owner_id=user.id,
                name=f"Hospital {i}",
                address=f"Address {i}",
                is_verified=True
            )
            db.add(hospital)
            db.flush()
            orgs.append(hospital)
        
        db.commit()
        
        # Reload orgs to get IDs ensures we have them if we skipped creation but they existed? 
        # For simplicity, let's assume if we skipped specific ones we fetch all 5 created/existing.
        all_orgs = db.query(models.Hospital).limit(5).all() 

        print("🌱 Seeding Doctors...")
        for i in range(1, 11):
            email = f"d{i}@d.d"
            if db.query(models.User).filter(models.User.email == email).first():
                print(f"  Skipping {email} (exists)")
                continue

            user = models.User(
                email=email,
                full_name=f"Doctor {i}",
                role="doctor",
                is_email_verified=True,
                password_hash=get_password_hash("d")
            )
            db.add(user)
            db.flush()
            
            # Assign d1-d2 to o1, d3-d4 to o2, etc.
            # i-1 // 2 gives index 0, 0, 1, 1, 2, 2...
            org_idx = (i - 1) // 2
            hospital_id = all_orgs[org_idx].id if org_idx < len(all_orgs) else all_orgs[0].id

            doctor = models.Doctor(
                user_id=user.id,
                hospital_id=hospital_id,
                specialization="General Dentist",
                license_number=f"LIC-{1000+i}",
                is_verified=True
            )
            db.add(doctor)
        db.commit()

        print("🌱 Seeding Patients...")
        for i in range(1, 21):
            email = f"p{i}@p.p"
            if db.query(models.User).filter(models.User.email == email).first():
                print(f"  Skipping {email} (exists)")
                continue

            user = models.User(
                email=email,
                full_name=f"Patient {i}",
                role="patient",
                is_email_verified=True,
                password_hash=get_password_hash("p")
            )
            db.add(user)
            db.flush()
            
            patient = models.Patient(
                user_id=user.id,
                age=20 + i,
                gender="Male" if i % 2 == 0 else "Female"
            )
            db.add(patient)
        db.commit()

        print("✅ Seeding Complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
