# backend/services/llm_service.py
from google import genai
import logging
import os
import config 

# --- CONFIGURATION ---
DIRECT_API_KEY = "AIzaSyC6fjUWaMF3GWl4UyTWdKAr4JdnnzFKR3s" # Replace with your actual key if needed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = DIRECT_API_KEY
        
        if not self.api_key or "YOUR_GEMINI" in self.api_key:
            logger.warning("⚠️ GEMINI_API_KEY is missing!")
            self.client = None
        else:
            try:
                # Use the new Client from google.genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"✅ Gemini Client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.client = None

    def generate_response(self, prompt: str) -> str:
        try:
            if not self.client: 
                return "System Error: AI Service not configured. Please check backend logs."
            
            # Use the new generate_content method structure
            response = self.client.models.generate_content(
                model='gemini-2.0-flash', # or 'gemini-1.5-flash'
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return "I apologize, but I am having trouble connecting to my brain right now."

llm_client = LLMService()