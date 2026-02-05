"""
Database Reset Script
CAUTION: This will DELETE ALL DATA and recreate tables from scratch.
"""

from database import SessionLocal, engine
from models import Base
import models

def reset_database():
    """Drop all tables and recreate them"""
    print("⚠️  WARNING: This will DELETE ALL DATA!")
    response = input("Are you sure you want to reset the database? Type 'YES' to confirm: ")
    
    if response != "YES":
        print("❌ Reset cancelled.")
        return
    
    print("\n🗑️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped")
    
    print("\n🏗️  Creating fresh tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created")
    
    print("\n✅ Database reset complete!")
    print("💡 Tip: Restart your backend server to initialize default admin account")

if __name__ == "__main__":
    reset_database()
