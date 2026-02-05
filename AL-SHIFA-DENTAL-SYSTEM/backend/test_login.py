import requests
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000/auth/login"

def test_login():
    print("🔐 Testing Login Endpoint...")
    
    # Test Data from seed_login_users_only.py
    test_cases = [
        # (Description, Email, Password, Expected Status)
        ("Admin Login", "login_admin@test.com", "password123", 200),
        ("Org Login", "login_org@test.com", "password123", 200),
        ("Doctor Login", "login_doc@test.com", "password123", 200),
        ("Patient Login", "login_patient@test.com", "password123", 200),
        
        # Standard Seed Data (User Provided)
        ("Seed Org 1", "o1@o.o", "o", 200),
        ("Seed Doctor 1", "d1@d.d", "d", 200),
        ("Seed Patient 1", "p1@p.p", "p", 200),

        ("Unverified User", "login_unverified@test.com", "password123", 403), # Expect 403 Forbidden
        ("Wrong Password", "login_admin@test.com", "wrongpass", 403),
        ("Non-existent User", "nobody@test.com", "password123", 403),
    ]

    passed = 0
    failed = 0

    for desc, email, password, expected_status in test_cases:
        payload = {
            "username": email,
            "password": password
        }
        
        try:
            res = requests.post(BASE_URL, data=payload) # OAuth2 form data
            
            if res.status_code == expected_status:
                print(f"✅ {desc}: Passed ({res.status_code})")
                passed += 1
            else:
                print(f"❌ {desc}: Failed! Expected {expected_status}, got {res.status_code}")
                # print(res.text)
                failed += 1
                
        except Exception as e:
            print(f"❌ {desc}: Error {e}")
            failed += 1

    print("\n" + "="*30)
    print(f"Summary: {passed} Passed, {failed} Failed")
    print("="*30)

if __name__ == "__main__":
    test_login()
