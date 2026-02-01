import sqlite3
import os

db_path = "backend/dental_clinic.db"

def fix_database():
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔧 Checking 'doctors' table schema...")

    # Fix Doctors Table (Add experience)
    try:
        cursor.execute("SELECT experience FROM doctors LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'experience' column to doctors table...")
        cursor.execute("ALTER TABLE doctors ADD COLUMN experience INTEGER DEFAULT 0")
    
    # Just in case 'specialization' is missing too (common pair)
    try:
        cursor.execute("SELECT specialization FROM doctors LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'specialization' column to doctors table...")
        cursor.execute("ALTER TABLE doctors ADD COLUMN specialization VARCHAR DEFAULT 'General Dentist'")

    conn.commit()
    conn.close()
    print("✅ Database successfully upgraded.")

if __name__ == "__main__":
    fix_database()
