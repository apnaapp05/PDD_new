
import os
import sys
from dotenv import load_dotenv

# Add backend to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def check_email_config():
    print("📧 Checking Email Configuration...")
    
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASSWORD")
    email_host = os.getenv("EMAIL_HOST")
    email_port = os.getenv("EMAIL_PORT")
    
    print(f"   - HOST: {email_host}")
    print(f"   - PORT: {email_port}")
    print(f"   - USER: {email_user if email_user else '[NOT SET]'}")
    print(f"   - PASS: {'******' if email_pass else '[NOT SET]'}")
    
    if not email_user or not email_pass:
        print("\n❌ Error: EMAIL_USER or EMAIL_PASSWORD is missing in .env file.")
        print("   Please create a .env file in the backend directory with these values.")
        return

    try:
        from notifications.email import EmailAdapter
        adapter = EmailAdapter()
        print("\n✅ EmailAdapter initialized successfully.")
        
        # Optional: Try sending a test email if user agrees (commented out for safety)
        # print("   Attempting to verify SMTP connection...")
        # adapter.server = smtplib.SMTP_SSL(adapter.smtp_server, adapter.smtp_port)
        # adapter.server.login(adapter.sender_email, adapter.password)
        # adapter.server.quit()
        # print("✅ SMTP Connection Verified.")
        
    except Exception as e:
        print(f"\n❌ Email Service Initialization Failed: {e}")

if __name__ == "__main__":
    check_email_config()
