
import os
import smtplib
from dotenv import load_dotenv

load_dotenv()

def test_smtp_login():
    print("📧 Testing SMTP Connection & Login...")
    
    host = os.getenv("EMAIL_HOST")
    port = int(os.getenv("EMAIL_PORT", 465))
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not user or not password:
        print("❌ Error: Missing credentials.")
        return

    try:
        if port == 587:
            print(f"   Connecting to {host}:{port} (STARTTLS)...")
            server = smtplib.SMTP(host, port)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            print(f"   Connecting to {host}:{port} (SSL)...")
            server = smtplib.SMTP_SSL(host, port)
            
        print("   Attempting Login...")
        server.login(user, password)
        print("✅ Login Successful! Credentials are valid.")
        server.quit()
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication Failed. Please check your Email or App Password.")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_smtp_login()