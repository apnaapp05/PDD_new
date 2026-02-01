import sqlite3
import os

db_path = "backend/dental_clinic.db"

def fix_database():
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔧 Checking 'organizations' table schema...")

    try:
        cursor.execute("SELECT is_verified FROM organizations LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'is_verified' column to organizations table...")
        cursor.execute("ALTER TABLE organizations ADD COLUMN is_verified BOOLEAN DEFAULT 0")
    
    conn.commit()
    conn.close()
    print("✅ Database successfully upgraded.")

if __name__ == "__main__":
    fix_database()
