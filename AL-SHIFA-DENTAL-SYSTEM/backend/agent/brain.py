
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
            - Check schedule (`get_todays_appointments`, `get_schedule_analysis`)
            - Check inventory (`check_inventory_stock`, `manage_inventory`)
            - Check revenue (`get_financial_analysis`, `get_revenue_comparison`)
            - Manage treatments (`list_treatments`, `create_treatment`, `manage_treatments`)
            - Consult Clinical Protocols (`consult_clinical_knowledge`)
            - Manage patients (`manage_patients`)
            - Check clinical stats (`get_weekly_clinical_stats`)
            - Configure schedule (`update_schedule_config`, `block_schedule_slot`)
            
            ALWAYS check tools before guessing.
            
            CRITICAL INSTRUCTIONS:
            - Answer the user's question DIRECTLY based ONLY on tool outputs.
            - DO NOT invent/hallucinate appointments, patients, or data if the tool returns none.
            - If a tool returns "No data" or an empty list, state that clearly.
            - DO NOT explain which tools you are using or what you are about to do.
            - Just perform the action and report the result.
            - Keep responses professional, concise, and helpful.
            
            EXAMPLE QUERIES & INTENT:
            
            **Schedule:**
            - "Who is coming today?" -> get_todays_appointments()
            - "Show my weekly schedule" -> get_schedule_analysis(period="weekly")
            - "Block 2-4 PM today" -> block_schedule_slot(date="...", time="14:00", reason="...")
            
            **Financials:**
            - "What is today's revenue?" -> get_financial_analysis(analysis_type="summary")
            - "How much did we earn this week vs last week?" -> get_revenue_comparison()
            - "Show me most profitable treatments" -> get_financial_analysis(analysis_type="profitability")
            
            **Inventory:**
            - "Are we low on gloves?" -> check_inventory_stock(item_name="Gloves")
            - "List everything in stock" -> check_inventory_stock(item_name="ALL")
            - "Add 50 masks to inventory" -> manage_inventory(action="add", item_name="Masks", quantity=50)
            
            **Treatments:**
            - "What treatments do I offer?" -> list_treatments()
            - "How much is a Root Canal?" -> list_treatments()
            - "Add a new treatment for Scaling at 3000" -> create_treatment(name="Scaling", cost=3000)
            
            **Patients:**
            - "Find patient John Doe" -> manage_patients(action="search", query="John Doe")
            - "Add a checkup record for patient 15" -> manage_patients(action="add_record", patient_id=15, diagnosis="Routine Checkup")
            
            **Knowledge:**
            - "Protocol for extraction?" -> consult_clinical_knowledge(query="extraction protocol")
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
                    "description": "Check the stock level of a specific item, list all items, or find all low stock items.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_name": {"type": "string", "description": "The name of the item (e.g. 'Gloves'), or 'ALL' to list everything. If omitted, checks for low stock."}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_financial_analysis",
                    "description": "Get financial reports: 'summary' (revenue), 'trend' (growth graph), 'profitability' (margins).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "analysis_type": {
                                "type": "string", 
                                "enum": ["summary", "trend", "profitability"],
                                "description": "Type of report to generate."
                            }
                        },
                        "required": ["analysis_type"]
                    }
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
            },
            {
                "type": "function",
                "function": {
                    "name": "get_schedule_analysis",
                    "description": "Analyze the schedule. Can check a specific day or a full week.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_str": {"type": "string", "description": "Date to analyze (YYYY-MM-DD) if period is daily."},
                            "period": {
                                "type": "string", 
                                "enum": ["daily", "weekly"],
                                "description": "Analysis period."
                            },
                            "week_offset": {
                                "type": "integer",
                                "description": "For weekly analysis: 0 for this week, -1 for last week, 1 for next week."
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weekly_clinical_stats",
                    "description": "Get a breakdown of treatments performed this week or in past weeks (case tracking).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                             "week_offset": {
                                "type": "integer",
                                "description": "0 for this week, -1 for last week (for comparison)."
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_revenue_comparison",
                    "description": "Compare this week's revenue with last week's revenue to check growth.",
                    "parameters": {
                        "type": "object", 
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_inventory",
                    "description": "Manage clinic inventory. Add new items or update stock levels.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["add_item", "update_stock"], "description": "Action to perform"},
                            "name": {"type": "string", "description": "Item name"},
                            "quantity": {"type": "integer", "description": "Quantity to add or set"},
                            "unit": {"type": "string", "description": "Unit (e.g. 'Pcs', 'Box') [Optional]", "default": "Pcs"},
                            "threshold": {"type": "integer", "description": "Minimum threshold alert [Optional]", "default": 10}
                        },
                        "required": ["action", "name", "quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_patients",
                    "description": "Manage patients: Search, View Details, Add Medical Records.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["search", "get_details", "add_record"], "description": "Action to perform"},
                            "query": {"type": "string", "description": "Search query (Name/Email) for 'search'"},
                            "patient_id": {"type": "integer", "description": "Patient ID for details/record"},
                            "diagnosis": {"type": "string", "description": "Diagnosis for 'add_record'"},
                            "notes": {"type": "string", "description": "Internal notes for 'add_record'"}
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_treatments",
                    "description": "Manage treatments: Create new services or link inventory items.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["create", "link_inventory"], "description": "Action to perform"},
                            "name": {"type": "string", "description": "Treatment Name"},
                            "cost": {"type": "number", "description": "Cost for 'create'"},
                            "item_name": {"type": "string", "description": "Inventory Item Name for 'link_inventory'"},
                            "quantity": {"type": "integer", "description": "Quantity used per treatment"}
                        },
                        "required": ["action", "name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_schedule_config",
                    "description": "Update clinic working hours and slot duration.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "string", "description": "Work Start Time (e.g. '09:00')"},
                            "end_time": {"type": "string", "description": "Work End Time (e.g. '17:00')"},
                            "slot_duration": {"type": "integer", "description": "Slot duration in minutes (e.g. 30)", "default": 30}
                        },
                        "required": ["start_time", "end_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "block_schedule_slot",
                    "description": "Block a time slot in the schedule.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                            "time": {"type": "string", "description": "Time (HH:MM)"},
                            "reason": {"type": "string", "description": "Reason for blocking"}
                        },
                        "required": ["date", "time", "reason"]
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
            "get_financial_analysis": self.tool_engine.get_financial_analysis,
            "list_treatments": self.tool_engine.list_treatments,
            "create_treatment": self.tool_engine.create_treatment,
            "consult_clinical_knowledge": self.tool_engine.consult_knowledge_base,
            "get_schedule_analysis": self.tool_engine.get_schedule_analysis,
            "block_schedule_slot": self.tool_engine.block_schedule_slot,
            "get_weekly_clinical_stats": self.tool_engine.get_weekly_clinical_stats,
            "get_revenue_comparison": self.tool_engine.get_revenue_comparison,
            # New Tools
            "manage_inventory": self.tool_engine.manage_inventory,
            "manage_patients": self.tool_engine.manage_patients,
            "manage_treatments": self.tool_engine.manage_treatments,
            "update_schedule_config": self.tool_engine.update_schedule_config,
        }

        self.messages.append({"role": "user", "content": query})
        
        try:
            # First API Call
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=self.messages,
                tools=self.tools_schema,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Check for finish_reason indicating tool use issues
            if response.choices[0].finish_reason == "tool_use_failed":
                print(f"DEBUG: Groq tool_use_failed. Retrying without tools...")
                # Retry without tools
                fallback_response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=self.messages
                )
                fallback_text = fallback_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": fallback_text})
                return fallback_text
            
            # Append initial response
            self.messages.append(message)

            if message.tool_calls:
                print(f"DEBUG: Agent requested {len(message.tool_calls)} tools.")
                
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: Failed to parse tool arguments: {e}")
                        continue
                        
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
                    model="llama-3.1-8b-instant",
                    messages=self.messages
                )
                final_text = final_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_text})
                return final_text
            
            return message.content
            
        except Exception as e:
            print(f"DEBUG: Groq Error Details: {type(e).__name__}: {e}")
            # More helpful error message
            error_str = str(e)
            if "tool_use_failed" in error_str:
                return "⚠️ The AI encountered an issue with function calling. Please try rephrasing your question or ask something simpler."
            return f"❌ AI Error: {str(e)}"
