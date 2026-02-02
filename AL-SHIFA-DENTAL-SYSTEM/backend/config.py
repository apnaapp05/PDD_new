import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_unsafe_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dental_clinic.db")

# AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Agent Settings
MAX_AGENT_STEPS = 5

# EMAIL CONFIGURATION (SMTP)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))
EMAIL_USER = os.getenv("EMAIL_USER")
# Ensure any accidental spaces in the App Password are removed
_raw_password = os.getenv("EMAIL_PASSWORD", "")
EMAIL_PASSWORD = _raw_password.replace(" ", "")

EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Al-Shifa Dental System")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@system.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")