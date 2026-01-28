import ollama
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Using the model you pulled via Ollama
        self.model = 'phi3'
        logger.info(f"✅ Local LLM Service (Ollama) initialized with {self.model}")

    def generate_response(self, prompt: str) -> str:
        try:
            # Direct communication with your local Phi-3 model
            response = ollama.chat(model=self.model, messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            return response['message']['content']
        except Exception as e:
            logger.error(f"Local LLM Error: {e}")
            return "Local AI Error: Ensure the Ollama application is running in your system tray."

llm_client = LLMService()