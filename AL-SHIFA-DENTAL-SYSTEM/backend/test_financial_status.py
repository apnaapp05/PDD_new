import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.tools import AgentTools
from models import Doctor

def test_financial_status():
    print("Testing 'Financial Status' Query...")
    
    db = SessionLocal()
    try:
        # 1. Get a Doctor to act as Agent
        doctor = db.query(Doctor).first()
        if not doctor:
            print("No doctor found. Please seed data first.")
            return

        print(f"Context: Dr. {doctor.user.full_name} (ID: {doctor.id})")
        
        # 2. Initialize Tools
        tools = AgentTools(db, doctor_id=doctor.id)
        
        # 3. Simulate the user query "what is our current financial status"
        # The agent maps this to `get_financial_analysis(analysis_type='summary')` typically.
        
        print("\n--- Invoking get_financial_analysis('summary') ---")
        try:
            result = tools.get_financial_analysis(analysis_type="summary")
            print("Result:")
            print(result)
        except Exception as e:
            print(f"Error invoking tool: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"Setup Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_financial_status()
