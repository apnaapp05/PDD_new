import sys
import os
import requests
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://127.0.0.1:8000"

def get_token(email, password):
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    if resp.status_code != 200:
        print(f"Login failed for {email}: {resp.text}")
        return None
    return resp.json()["access_token"]

def chat(token, message):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/doctor/agent/chat", json={"query": message}, headers=headers)
    if resp.status_code != 200:
        return f"Error: {resp.text}"
    return resp.json()["response"]

def test_isolation():
    print("Testing Chatbot Isolation...")

    # 1. Login as Doctor 1 (d1@d.d)
    token1 = get_token("d1@d.d", "d")
    if not token1: return

    # 2. Login as Doctor 2 (d2@d.d)
    token2 = get_token("d2@d.d", "d") 
    if not token2: return

    print("Logged in as Doctor 1 and Doctor 2")

    # 3. Doctor 1 sets context
    print("\n--- Doctor 1 Chat ---")
    msg1 = "My favorite color is Blue."
    print(f"Doctor 1: {msg1}")
    resp1 = chat(token1, msg1)
    print(f"Agent: {resp1.encode('ascii', 'ignore').decode()}")
    
    # 4. Doctor 2 should NOT know this
    print("\n--- Doctor 2 Chat ---")
    msg2 = "What is my favorite color?"
    print(f"Doctor 2: {msg2}")
    resp2 = chat(token2, msg2)
    print(f"Agent: {resp2.encode('ascii', 'ignore').decode()}")

    if "Blue" in resp2:
        print("LEAK DETECTED! Doctor 2 knows Doctor 1's favorite color.")
    else:
        print("Isolation Verified: Doctor 2 does not know Doctor 1's secret.")

    # 5. Doctor 1 SHOULD know this
    print("\n--- Doctor 1 Check ---")
    msg3 = "What is my favorite color?"
    print(f"Doctor 1: {msg3}")
    resp3 = chat(token1, msg3)
    print(f"Agent: {resp3.encode('ascii', 'ignore').decode()}")

    if "Blue" in resp3:
         print("Context Retrieval Verified: Doctor 1 remembers.")
    else:
         print("Doctor 1 forgot (Acceptable if limited context window, but ideally should remember).")

    # 6. Data Isolation test (Appointments)
    # Doctor 1 was just seeded and has NO appointments (seed_financial_data added to 'doctor' (login_doc), not 'd1')
    # Wait, seed_test_accounts created d1/d2.
    # seed_financial_data created data for the FIRST doctor in DB.
    # I need to check which doctor has data.
    
    print("\n--- Data Isolation (Appointments) ---")
    # Let's ask Doctor 2 about their schedule. Should be empty.
    resp_data = chat(token2, "What are my appointments today?")
    print(f"Doctor 2 Agent: {resp_data.encode('ascii', 'ignore').decode()}")
    
    # 7. Patient Isolation Test
    print("\nTesting Patient Chat Isolation...")
    token_p1 = get_token("p1@p.p", "p")
    token_p2 = get_token("p2@p.p", "p")
    
    if not token_p1 or not token_p2:
        print("Skipping Patient test (Missing tokens)")
        return

    def chat_patient(token, msg):
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/patient/agent/chat", json={"query": msg}, headers=headers)
        if resp.status_code != 200: return f"Error: {resp.text}"
        return resp.json()["response"]

    # P1 sets context
    print("\n--- Patient 1 Chat ---")
    msg_p1 = "I have a toothache on the left side."
    print(f"Patient 1: {msg_p1}")
    resp_p1 = chat_patient(token_p1, msg_p1)
    print(f"Agent: {resp_p1.encode('ascii', 'ignore').decode()}")
    
    # P2 checks context
    print("\n--- Patient 2 Chat ---")
    msg_p2 = "Where is my toothache?"
    print(f"Patient 2: {msg_p2}")
    resp_p2 = chat_patient(token_p2, msg_p2)
    print(f"Agent: {resp_p2.encode('ascii', 'ignore').decode()}")

    if "left" in resp_p2.lower():
         print("❌ LEAK DETECTED! Patient 2 knows Patient 1's symptom.")
    else:
         print("✅ Isolation Verified: Patient 2 does not know Patient 1's symptom.")

    # P1 verify context
    print("\n--- Patient 1 Check ---")
    msg_p1_check = "Where is my toothache?"
    print(f"Patient 1: {msg_p1_check}")
    resp_p1_check = chat_patient(token_p1, msg_p1_check)
    print(f"Agent: {resp_p1_check.encode('ascii', 'ignore').decode()}")

    if "left" in resp_p1_check.lower():
         print("✅ Context Retrieval Verified: Patient 1 remembers.")
    else:
         print("⚠️ Patient 1 forgot (Acceptable if limited context window).")
    
if __name__ == "__main__":
    test_isolation()
