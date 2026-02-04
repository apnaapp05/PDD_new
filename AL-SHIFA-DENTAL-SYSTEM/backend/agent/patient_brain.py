
import json
import os
from openai import OpenAI
from sqlalchemy.orm import Session
from agent.tools import PatientAgentTools
import config

# Initialize Groq Client (using OpenAI SDK)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=config.GROQ_API_KEY
)

class PatientBrain:
    def __init__(self, db: Session, patient_id: int):
        self.db = db
        self.patient_id = patient_id
        
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")

        self.tool_engine = PatientAgentTools(db, patient_id)
        
        self.tools_map = {
            "list_doctors": self.tool_engine.list_doctors,
            "get_my_appointments": self.tool_engine.get_my_appointments,
            "cancel_appointment": self.tool_engine.cancel_appointment,
            "book_appointment": self.tool_engine.book_appointment,
            "check_availability": self.tool_engine.check_availability,
        }

        # OpenAI Tool Schema (Groq Compatible)
        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "list_doctors",
                    "description": "List all available doctors at the clinic.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Get available time slots for a doctor on a specific date.",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "doctor_id": {"type": "integer"},
                            "date": {"type": "string", "description": "YYYY-MM-DD"}
                        }, 
                        "required": ["doctor_id", "date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_my_appointments",
                    "description": "Get valid future appointments for this patient.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_appointment",
                    "description": "Cancel a specific appointment by ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {"type": "integer", "description": "The ID of the appointment to cancel."}
                        },
                        "required": ["appointment_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_appointment",
                    "description": "Book a new appointment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_id": {"type": "integer", "description": "The ID of the doctor (ask user to list doctors first if unknown)."},
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format (infer from context e.g., 'tomorrow')."},
                            "time": {"type": "string", "description": "Time in HH:MM (24-hour) format (e.g. 15:30 for 3:30 PM)."},
                            "reason": {"type": "string", "description": "Reason for visit."}
                        },
                        "required": ["doctor_id", "date", "time"]
                    }
                }
            }
        ]

        self.system_prompt = f"""
            You are the Patient Assistant for Al-Shifa Dental Clinic.
            Help patients manage their visits.
            
            Capabilities:
            - List doctors (`list_doctors`)
            - Check slot availability (`check_availability`)
            - Check upcoming appointments (`get_my_appointments`)
            - Cancel appointments (`cancel_appointment`)
            - Book NEW appointments (`book_appointment`)
            
            **CRITICAL RULES:**
            1. **Booking Logic**:
               - **Step 1**: Check if you have: Doctor, Date, Time, Reason.
               - **Step 2**: If you have EVERYTHING -> Book it exactly as requested.
               - **Step 3**: If you are missing something -> Ask for ONLY the missing part.
               
            2. **Smart Defaults**:
               - If user says "Doctor 1", assume ID=1. (Doctor X -> ID X).
               - If user says "today", use {current_date}.

            3. **Interactive Chips (CRITICAL)**:
               - You MUST output clickable buttons for choices in brackets `[Option]`.
               - **Doctors**: After calling `list_doctors`, output: `[Doctor 1] [Doctor 2]`.
               - **Time**: **Call `check_availability(doctor_id, date)` FIRST.** Then output valid slots as buttons: `[09:00] [09:30] [10:00]`.
               - **DO NOT** guess times like [Morning]. Use REAL slots.
               - **Reason**: `[Checkup] [Pain] [Cleaning]`
               
            4. **Clean Output**: NEVER show raw JSON. Be natural.
            5. **Tool Calling**: Use the provided tools interface. Do NOT output XML like <function=...>.
            
            Current Date: {current_date}.
            
            Be polite, concise, and helpful.
        """
        
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def process(self, query: str) -> str:
        self.messages.append({"role": "user", "content": query})
        
        try:
            # 1. First Call
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=self.messages,
                tools=self.tools_schema,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            self.messages.append(message)
            
            # 2. Check for Tool Calls
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
                            result = f"Error: {str(e)}"
                        
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result)
                        })
                    else:
                        print(f"DEBUG: Unknown tool {func_name}")

                # 3. Second Call (Resolution)
                final_response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=self.messages
                )
                final_text = final_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_text})
                
                # Extract Chips [Chip] -> actions list
                import re
                actions = re.findall(r'\[(.*?)\]', final_text)
                clean_text = re.sub(r'\[.*?\]', '', final_text).strip()
                
                return {
                    "response": clean_text,
                    "actions": actions
                }
            
            # Default response if no tools called but message returned
            return {"response": message.content, "actions": []}
            
        except Exception as e:
            print(f"DEBUG: Groq Error: {e}")
            return {
                "response": "I apologize, but I am having trouble connecting to the server right now. Please try again in a moment.",
                "actions": []
            }
