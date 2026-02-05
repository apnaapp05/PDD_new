import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.tools import AgentTools
from models import Doctor, User

def test_parity():
    db = SessionLocal()
    try:
        # 1. Get a Doctor ID
        doctor = db.query(Doctor).first()
        if not doctor:
            print("❌ No doctor found for testing.")
            return

        print(f"👨‍⚕️ Testing with Doctor: {doctor.user.full_name} (ID: {doctor.id})")
        
        tools = AgentTools(db, doctor_id=doctor.id)
        
        # 2. Test Inventory Management
        print("\n📦 Testing Inventory Management...")
        # Add Item
        res = tools.manage_inventory("add_item", name="Test Mask", quantity=100, unit="Box", threshold=5)
        print(f"Add Item: {res}")
        
        # Test List All (Fix for Hallucination)
        print("Inventory List (ALL):")
        print(tools.check_inventory_stock("ALL"))

        # Update Stock
        res = tools.manage_inventory("update_stock", name="Test Mask", quantity=90)

        print(f"Update Stock: {res}")
        
        # 3. Test Patient Management
        print("\nbusts_in_silhouette Testing Patient Management...")
        # Search
        res = tools.manage_patients("search", query="test") # Assuming some test user exists or empty list
        print(f"Search: {res[:100]}...") # Truncate
        
        # 4. Test Treatment Management
        print("\n🦷 Testing Treatment Management...")
        # Create
        res = tools.manage_treatments("create", name="Laser Whitening AI", cost=500.0)
        print(f"Create Treatment: {res}")
        
        # Link Inventory
        res = tools.manage_treatments("link_inventory", name="Laser Whitening AI", item_name="Test Mask", quantity=2)
        print(f"Link Inventory: {res}")
        
        # 5. Test Schedule Config
        print("\n📅 Testing Schedule Configuration...")
        res = tools.update_schedule_config(start_time="09:00", end_time="18:00", slot_duration=45)
        print(f"Update Config: {res}")
        
        print("\n✅ Verification Complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_parity()
