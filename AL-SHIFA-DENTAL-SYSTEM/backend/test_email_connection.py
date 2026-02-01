import smtplib
import config

print(f"Testing connection to {config.EMAIL_HOST}:{config.EMAIL_PORT}...")
print(f"User: {config.EMAIL_USER}")

try:
    with smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT) as server:
        server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
        print("✅ LOGIN SUCCESSFUL! Your credentials are correct.")
        
        # Try sending a test mail
        msg = f"Subject: Test Mail\n\nIf you see this, Al-Shifa email is working."
        server.sendmail(config.EMAIL_USER, config.EMAIL_USER, msg)
        print("✅ TEST EMAIL SENT! Check your inbox.")
except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
    print("\nTroubleshooting:")
    print("1. Ensure 'EMAIL_PASSWORD' in config.py is a 16-character Google App Password.")
    print("2. Ensure 2-Step Verification is ON in Google Account.")
