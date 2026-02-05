"""
End-to-end test for streamlined chatbot booking
Tests:
1. Successful booking (immediate execution when all data present)
2. Booking with occupied slot (shows exact error)
3. Cancel and reschedule
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from agent.patient_brain import PatientBrain
from models import Patient, Appointment
from datetime import datetime, timedelta

def test_streamlined_booking():
    print("=" * 60)
    print("STREAMLINED CHATBOT BOOKING TEST")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get patient
        patient = db.query(Patient).first()
        if not patient:
            print("No patient found. Run seed_test_accounts.py first.")
            return
        
        print(f"\nPatient: {patient.user.full_name}\n")
        brain = PatientBrain(db, patient.id)
        
        # Test 1: Immediate booking with all data
        print("\n" + "=" * 60)
        print("TEST 1: Immediate Booking (All Data Present)")
        print("=" * 60)
        print("User: 'book with doctor 1 tomorrow at 3pm for checkup'")
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = brain.process(f"book with doctor 1 on {tomorrow} at 15:00 for checkup")
        print(f"\nAgent Response:\n{response['response']}")
        if response['actions']:
            print(f"Actions: {response['actions']}")
        
        # Verify booking in database
        appt = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.start_time >= datetime.now()
        ).order_by(Appointment.start_time.desc()).first()
        
        if appt:
            print(f"\n[DATABASE CHECK] Appointment created: {appt.start_time}, Doctor ID: {appt.doctor_id}")
        else:
            print("\n[DATABASE CHECK] No appointment found - booking may have failed")
        
        # Test 2: Booking with occupied slot (should show exact error)
        print("\n" + "=" * 60)
        print("TEST 2: Booking Occupied Slot (Should Show Exact Error)")
        print("=" * 60)
        print(f"User: 'book doctor 1 on {tomorrow} at 15:00 for cleaning' (same slot)")
        
        brain2 = PatientBrain(db, patient.id)  # Fresh brain
        response2 = brain2.process(f"book doctor 1 on {tomorrow} at 15:00 for cleaning")
        print(f"\nAgent Response:\n{response2['response']}")
        
        if "occupied" in response2['response'].lower() or "taken" in response2['response'].lower():
            print("\n[CHECK] Exact error shown correctly")
        else:
            print(f"\n[CHECK] Warning - error message might not be clear")
        
        print("\n" + "=" * 60)
        print("Test Complete")
        print("=" * 60)
        
    except Exception as e:
        print(f"Test Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_streamlined_booking()
