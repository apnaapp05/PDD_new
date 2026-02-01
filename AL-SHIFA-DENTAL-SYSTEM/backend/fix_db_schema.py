import sqlite3
import os

db_path = "backend/dental_clinic.db"

def fix_database():
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔧 Checking database schema...")

    # 1. Fix Users Table (Add phone)
    try:
        cursor.execute("SELECT phone FROM users LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'phone' column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN phone VARCHAR")
    
    # 2. Fix Inventory Table (Add buying_cost)
    try:
        cursor.execute("SELECT buying_cost FROM inventory LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'buying_cost' column to inventory table...")
        cursor.execute("ALTER TABLE inventory ADD COLUMN buying_cost FLOAT DEFAULT 0.0")

    conn.commit()
    conn.close()
    print("✅ Database successfully upgraded.")

if __name__ == "__main__":
    fix_database()
