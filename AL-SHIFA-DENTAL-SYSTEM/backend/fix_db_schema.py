# backend/fix_db_schema.py
import sqlite3
import os

DB_FILE = "dental_clinic.db"

def fix_schema():
    if not os.path.exists(DB_FILE):
        print(f"Database {DB_FILE} not found. Starting server will create it automatically.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("Checking database schema...")

    # 1. Fix Users Table (Add phone_number)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR")
        print("✅ Added 'phone_number' to users table.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("ℹ️ 'phone_number' already exists in users.")
        else:
            print(f"⚠️ Error updating users: {e}")

    # 2. Fix Hospitals Table (Add pending location fields)
    hospital_fields = [
        ("pending_address", "VARCHAR"),
        ("pending_pincode", "VARCHAR"),
        ("pending_lat", "FLOAT"),
        ("pending_lng", "FLOAT")
    ]

    for field, type_ in hospital_fields:
        try:
            cursor.execute(f"ALTER TABLE hospitals ADD COLUMN {field} {type_}")
            print(f"✅ Added '{field}' to hospitals table.")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"ℹ️ '{field}' already exists in hospitals.")
            else:
                print(f"⚠️ Error updating hospitals ({field}): {e}")

    conn.commit()
    conn.close()
    print("\nDatabase schema update complete! You can now start the server.")

if __name__ == "__main__":
    fix_schema()