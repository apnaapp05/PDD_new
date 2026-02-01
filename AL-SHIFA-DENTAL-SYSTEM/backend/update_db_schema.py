import sqlite3
import os

db_path = "backend/dental_clinic.db"

if not os.path.exists(db_path):
    print("⚠️ Database not found, skipping migration.")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(inventory)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "buying_cost" not in columns:
            print("🛠️ Adding 'buying_cost' column to Inventory table...")
            cursor.execute("ALTER TABLE inventory ADD COLUMN buying_cost FLOAT DEFAULT 0.0")
            conn.commit()
            print("✅ Database successfully upgraded.")
        else:
            print("✅ Column 'buying_cost' already exists.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error updating database: {e}")
