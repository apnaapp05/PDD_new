from database.db_session import engine, SessionLocal
from models import Base, InventoryItem, Treatment, Hospital, Doctor
from sqlalchemy import text
import datetime

print("🔄 Resetting Inventory & Treatment Tables...")

# 1. DROP TABLES (To clear old schema/data)
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS inventory_items CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS treatments CASCADE"))
    conn.commit()

# 2. CREATE TABLES
Base.metadata.create_all(bind=engine)
print("✅ Tables Recreated.")

# 3. SEED DATA
db = SessionLocal()
try:
    # Get ID links
    hospital = db.query(Hospital).first()
    doctor = db.query(Doctor).first()
    
    if not hospital or not doctor:
        print("⚠️ No Hospital/Doctor found. Please register a user first, then run this script again.")
    else:
        hid = hospital.id
        did = doctor.id

        # --- YOUR INVENTORY DATA ---
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
        
        print(f"📦 Seeding {len(inv_data)} Inventory Items...")
        for i in inv_data:
            db.add(InventoryItem(hospital_id=hid, name=i["name"], quantity=i["qty"], unit=i["unit"], min_threshold=i["min"]))

        # --- YOUR TREATMENT DATA ---
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

        print(f"🩺 Seeding {len(trt_data)} Treatments...")
        for t in trt_data:
            db.add(Treatment(doctor_id=did, name=t["name"], cost=t["cost"], description=t["desc"]))

        db.commit()
        print("✅ Data Seeding Complete!")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    db.close()
