alimport requests

BASE_URL = "http://localhost:8001"
EMAIL = "d1@d.d"
PASSWORD = "d"

def test_login_and_dashboard():
    try:
        # 1. Login
        print(f"🔑 Logging in as {EMAIL}...")
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        
        if resp.status_code != 200:
            print(f"❌ Login failed: {resp.status_code} - {resp.text}")
            return
            
        data = resp.json()
        token = data.get("access_token")
        print(f"✅ Login successful! Token: {token[:10]}...")
        
        # 2. Get Dashboard
        print(f"\n📊 Fetching Dashboard...")
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/doctor/dashboard", headers=headers)
        
        if resp.status_code == 200:
            print("✅ Dashboard loaded successfully!")
            print(resp.json())
        else:
            print(f"❌ Dashboard failed: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_login_and_dashboard()
