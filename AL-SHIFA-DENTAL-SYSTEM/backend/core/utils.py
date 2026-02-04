
import random
import string

def generate_otp():
    return "".join(random.choices(string.digits, k=6))

def get_otp_email_template(name: str, otp: str):
    plain_text = f"Subject: Your Code - Al-Shifa\nDear {name},\nCode: {otp}"
    html_content = f"<h1>Verify Account</h1><p>Dear {name},</p><h3>{otp}</h3>"
    return plain_text, html_content
