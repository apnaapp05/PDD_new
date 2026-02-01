import sqlite3
import os

db_path = "backend/dental_clinic.db"

def fix_database():
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔧 Running Final Schema Fixes...")

    # 1. Add License Number to Doctors
    try:
        cursor.execute("SELECT license_number FROM doctors LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'license_number' to doctors...")
        cursor.execute("ALTER TABLE doctors ADD COLUMN license_number VARCHAR")

    # 2. Add Scheduling Config to Doctors (for settings page)
    try:
        cursor.execute("SELECT scheduling_config FROM doctors LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'scheduling_config' to doctors...")
        cursor.execute("ALTER TABLE doctors ADD COLUMN scheduling_config TEXT")

    # 3. Add Phone Number to Users (for profile)
    try:
        cursor.execute("SELECT phone_number FROM users LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'phone_number' to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR")

    # 4. Add OTP columns (if missing)
    try:
        cursor.execute("SELECT otp_code FROM users LIMIT 1")
    except sqlite3.OperationalError:
        print("   -> Adding 'otp_code' to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN otp_code VARCHAR")
        cursor.execute("ALTER TABLE users ADD COLUMN otp_expires_at DATETIME")

    conn.commit()
    conn.close()
    print("✅ Database Schema Synced Successfully.")

if __name__ == "__main__":
    fix_database()
