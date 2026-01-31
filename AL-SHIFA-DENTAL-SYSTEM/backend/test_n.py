# backend/test_email_ssl.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

print(f"Testing Email Config using SSL (Port 465)...")
print(f"User: {config.EMAIL_USER}")

# Force Port 465
SMTP_PORT = 465 

try:
    msg = MIMEMultipart()
    msg['Subject'] = "Al-Shifa SSL Test"
    msg['From'] = config.EMAIL_USER
    msg['To'] = config.EMAIL_USER # Send to yourself
    msg.attach(MIMEText("This is a test email sent via SSL port 465.", 'plain'))

    # NOTE: We use SMTP_SSL instead of SMTP
    with smtplib.SMTP_SSL(config.EMAIL_HOST, SMTP_PORT) as server:
        print("✅ Connected to Gmail via SSL. Logging in...")
        server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
        print("✅ Logged in. Sending email...")
        server.sendmail(config.EMAIL_USER, config.EMAIL_USER, msg.as_string())
    
    print("✅ Email Sent Successfully! Check your inbox.")

except Exception as e:
    print(f"❌ FAILED: {e}")