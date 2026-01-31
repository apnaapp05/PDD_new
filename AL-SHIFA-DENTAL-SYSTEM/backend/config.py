# backend/config.py

import os

# Security
SECRET_KEY = "alshifa_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 

# Database Configuration (PostgreSQL)
DATABASE_URL = "sqlite:///./dental_clinic.db"

# AI Configuration
GEMINI_API_KEY = "AIzaSyC6fjUWaMF3GWl4UyTWdKAr4JdnnzFKR3s"

# Agent Settings
MAX_AGENT_STEPS = 5

# --- NEW: EMAIL CONFIGURATION (SMTP) ---
# Use 'smtp.gmail.com' for Gmail, Port 465
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))
EMAIL_USER = os.getenv("EMAIL_USER", "apna.app05@gmail.com")
# IMPORTANT: For Gmail, use an 'App Password', not your login password.
EMAIL_PASSWORD = "jcby crgf pzqy xmlf"
EMAIL_FROM_NAME = "Al-Shifa Dental System"
ADMIN_EMAIL = "admin@system.com" 
ADMIN_PASSWORD = "admin123"