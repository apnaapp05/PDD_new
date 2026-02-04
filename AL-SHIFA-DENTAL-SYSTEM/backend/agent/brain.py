
import json
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from agent.tools import AgentTools
import config

# Initialize Groq Client (using OpenAI SDK)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=config.GROQ_API_KEY
)

class ClinicAgent:
    def __init__(self, doctor_id: int, history: list = None):
        self.doc_id = doctor_id
        # We don't store DB in self anymore, we get it per request
        self.tool_engine = None 
        
        self.system_prompt = """
            You are the AI Clinical Manager for Al-Shifa Dental Clinic. 
            Your goal is to help the doctor manage their clinic efficiently.
            
            You have access to real-time data via tools:
            - Check schedule (`get_todays_appointments`)
            - Check inventory (`check_inventory_stock`)
            - Check revenue (`get_revenue_report`)
            - Manage treatments (`list_treatments`, `create_treatment`)
            - Consult Clinical Protocols (`consult_clinical_knowledge`)
            
            ALWAYS check tools before guessing.
            Keep responses professional, concise, and helpful.
        """
        
        if history:
             self.messages = history
        else:
             self.messages = [{"role": "system", "content": self.system_prompt}]
             
        # Tools Schema
        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "get_todays_appointments",
                    "description": "Get all appointments scheduled for today, including patient details and status.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_inventory_stock",
                    "description": "Check the stock level of a specific item or find all low stock items.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_name": {"type": "string", "description": "The name of the item to check (e.g. 'Gloves'). If omitted, checks all low stock."}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_revenue_report",
                    "description": "Get the financial revenue summary report for the current month.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_treatments",
                    "description": "List all available dental treatments and their prices.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_treatment",
                    "description": "Create or add a new dental treatment to the price list.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the treatment"},
                            "cost": {"type": "number", "description": "Cost/Price of the treatment"}
                        },
                        "required": ["name", "cost"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "consult_clinical_knowledge",
                    "description": "Consult the internal clinic knowledge base for clinical protocols, guidelines, or medical questions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The clinical question or topic to search for."}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        


    def process(self, query: str, db: Session) -> str:
        # Initialize tools with current DB session
        self.tool_engine = AgentTools(db, self.doc_id)
        
        # Tool Implementations Map (Need to bind to new tool_engine instance)
        self.tools_map = {
            "get_todays_appointments": self.tool_engine.get_todays_appointments,
            "check_inventory_stock": self.tool_engine.check_inventory_stock,
            "get_revenue_report": self.tool_engine.get_revenue_report,
            "list_treatments": self.tool_engine.list_treatments,
            "create_treatment": self.tool_engine.create_treatment,
            "consult_clinical_knowledge": self.tool_engine.consult_knowledge_base,
        }

        self.messages.append({"role": "user", "content": query})
        
        try:
            # First API Call
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=self.messages,
                tools=self.tools_schema,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            # Append initial response
            self.messages.append(message)

            if message.tool_calls:
                print(f"DEBUG: Agent requested {len(message.tool_calls)} tools.")
                
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    print(f"DEBUG: Executing {func_name} with {args}")
                    
                    if func_name in self.tools_map:
                        try:
                            result = self.tools_map[func_name](**args)
                        except Exception as e:
                            result = f"Error executing tool: {str(e)}"
                        
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result)
                        })
                    else:
                        print(f"DEBUG: Tool {func_name} not found.")

                # Second API Call (Resolution)
                final_response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=self.messages
                )
                final_text = final_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_text})
                return final_text
            
            return message.content
            
        except Exception as e:
            print(f"DEBUG: Groq Error: {e}")
            return f"❌ AI Error: {str(e)}"
