import sqlite3
import os
from datetime import datetime

db_path = "backend/dental_clinic.db"

def fix_database():
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔧 Running Ultimate Schema Fix...")

    # 1. Fix Inventory Table (Add last_updated)
    try:
        cursor.execute("SELECT last_updated FROM inventory LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'last_updated' to inventory...")
        cursor.execute("ALTER TABLE inventory ADD COLUMN last_updated DATETIME")
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(f"UPDATE inventory SET last_updated = '{now}'")

    # 2. Fix Doctors Table (Add license_number)
    try:
        cursor.execute("SELECT license_number FROM doctors LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'license_number' to doctors...")
        cursor.execute("ALTER TABLE doctors ADD COLUMN license_number VARCHAR")

    conn.commit()
    conn.close()
    print("✅ Database successfully upgraded.")

if __name__ == "__main__":
    fix_database()
