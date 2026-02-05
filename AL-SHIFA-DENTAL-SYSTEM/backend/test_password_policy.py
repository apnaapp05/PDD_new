
import requests

BASE_URL = "http://127.0.0.1:8000/auth/register"

def test_password_policy():
    print("🔒 Testing Password Strength Policy...")
    
    # Test Cases
    cases = [
        ("weak", "Password too short", 400),
        ("Weakpass1", "Missing special char", 400),
        ("WEAKPASS1!", "Missing lowercase", 400),
        ("weakpass1!", "Missing uppercase", 400),
        ("Weakpass!", "Missing digit", 400),
        ("StrongP@ss1", "Valid password", 200) # Assuming email is unique, might fail if email exists but we expect 200 on validation or 400 on email exists.
        # Actually, if validation passes, it proceeds to check email.
        # So for "Valid password", we expect either 200 (OTP sent) or 400 (Email exists). 
        # But DEFINITELY NOT "Password must be..." error.
    ]
    
    for pwd, desc, expected_status in cases:
        payload = {
            "email": f"test_{pwd}@example.com",
            "password": pwd,
            "full_name": "Test User",
            "role": "patient",
            "age": 30,
            "gender": "Male"
        }
        
        try:
            res = requests.post(BASE_URL, json=payload)
            success = False
            
            if expected_status == 400:
                # We expect failure
                if res.status_code == 400:
                    err = res.json().get("detail", "")
                    if "Password must" in err:
                        print(f"✅ {desc}: Rejected as expected ({err})")
                        success = True
                    elif "Email already registered" in err:
                         print(f"⚠️ {desc}: Skipped (Email exists), but password validation likely passed.")
                    else:
                        print(f"❌ {desc}: Failed with unexpected error: {err}")
                else:
                    print(f"❌ {desc}: Unexpected status {res.status_code}")
                    
            elif expected_status == 200:
                # We expect success (or at least passing the password check)
                if res.status_code == 200:
                    print(f"✅ {desc}: Accepted")
                    success = True
                elif res.status_code == 400 and "Email" in res.json().get("detail", ""):
                     print(f"✅ {desc}: Password Valid (but email exists)")
                     success = True
                else:
                     print(f"❌ {desc}: Failed with {res.status_code} - {res.text}")
                     
        except Exception as e:
            print(f"❌ {desc}: Error {e}")

if __name__ == "__main__":
    test_password_policy()
