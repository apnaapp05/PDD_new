"""Test direct API call to doctor agent"""
import requests

# Login first to get token
login_response = requests.post(
    "http://localhost:8000/auth/login",
    data={"username": "d1@d.d", "password": "d"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"✓ Logged in, token: {token[:20]}...")
    
    # Test agent chat
    chat_response = requests.post(
        "http://localhost:8000/doctor/agent/chat",
        json={"query": "how much revenue today?"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"\nStatus: {chat_response.status_code}")
    print(f"Response: {chat_response.text}")
else:
    print(f"Login failed: {login_response.text}")
