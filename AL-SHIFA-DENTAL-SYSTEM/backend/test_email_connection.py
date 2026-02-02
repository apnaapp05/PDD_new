import smtplib
import socket # New import
import config
import time

# Increase timeout to 30 seconds (default is usually too short for slow networks)
socket.setdefaulttimeout(30)

print(f"Testing connection to {config.EMAIL_HOST}:{config.EMAIL_PORT}...")
print(f"User: {config.EMAIL_USER}")

try:
    # Attempting to connect
    print(f"⏳ Connecting... (Timeout set to 30s)")
    
    if config.EMAIL_PORT == 587:
        server = smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT)
        server.set_debuglevel(1) # See exactly where it gets stuck
        server.ehlo()
        server.starttls()
        server.ehlo()
    else:
        server = smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT)
    
    # Login
    print("🔑 Logging in...")
    server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
    print("✅ LOGIN SUCCESSFUL! Credentials are valid.")
    
    # Send
    msg = f"Subject: Test Mail\n\nAl-Shifa System Check."
    server.sendmail(config.EMAIL_USER, config.EMAIL_USER, msg)
    print("✅ TEST EMAIL SENT!")
    server.quit()

except socket.timeout:
    print("❌ ERROR: Connection Timed Out. Your internet is too slow or blocking the port.")
except smtplib.SMTPConnectError:
    print("❌ ERROR: Server refused connection. Port is blocked.")
except Exception as e:
    print(f"❌ ERROR: {e}")