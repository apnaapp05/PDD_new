"""
Selective Database Reset Script
Clears only transactional data while preserving user accounts and core data.

KEEPS:
- Users (doctors, patients, admin)
- Hospitals
- Doctors
- Patients
- Treatments
- Inventory Items

DELETES:
- Appointments
- Invoices
- Medical Records
- Patient Files
- Treatment-Inventory Links
"""

from database import SessionLocal
from models import Appointment, Invoice, MedicalRecord, PatientFile, TreatmentInventoryLink

def selective_reset():
    """Clear only transactional data, keep users and core data"""
    print("⚠️  This will DELETE:")
    print("   - All appointments")
    print("   - All invoices")
    print("   - All medical records")
    print("   - All patient files")
    print("\n✅ This will KEEP:")
    print("   - User accounts (admin, doctors, patients)")
    print("   - Hospitals")
    print("   - Treatments")
    print("   - Inventory items")
    
    response = input("\nProceed? Type 'YES' to confirm: ")
    
    if response != "YES":
        print("❌ Reset cancelled.")
        return
    
    db = SessionLocal()
    try:
        # Delete appointments
        appt_count = db.query(Appointment).delete()
        print(f"\n🗑️  Deleted {appt_count} appointments")
        
        # Delete invoices
        inv_count = db.query(Invoice).delete()
        print(f"🗑️  Deleted {inv_count} invoices")
        
        # Delete medical records
        rec_count = db.query(MedicalRecord).delete()
        print(f"🗑️  Deleted {rec_count} medical records")
        
        # Delete patient files
        file_count = db.query(PatientFile).delete()
        print(f"🗑️  Deleted {file_count} patient files")
        
        # Delete treatment-inventory links
        link_count = db.query(TreatmentInventoryLink).delete()
        print(f"🗑️  Deleted {link_count} treatment links")
        
        db.commit()
        print("\n✅ Selective reset complete!")
        print("💡 User accounts and core data preserved")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    selective_reset()
