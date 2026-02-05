
from openai import OpenAI
import config
import os

# Initialize Groq Client (using OpenAI SDK)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=config.GROQ_API_KEY
)

def get_llm_response(messages: list, model: str = "llama-3.3-70b-versatile", tools=None) -> str:
    """
    Helper to get response from LLM.
    """
    try:
        if tools:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            return response.choices[0].message
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {e}")
        return f"Error generating response: {str(e)}"
