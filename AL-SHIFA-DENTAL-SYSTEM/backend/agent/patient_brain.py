
import json
import os
import re
from openai import OpenAI
from sqlalchemy.orm import Session
from agent.tools import PatientAgentTools
from models import User, Doctor, Appointment
import config
from datetime import datetime

# Initialize Groq Client (using OpenAI SDK)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=config.GROQ_API_KEY
)

class PatientBrain:
    def __init__(self, db: Session, patient_id: int):
        self.db = db
        self.patient_id = patient_id
        
        current_date = datetime.now().strftime("%Y-%m-%d")

        self.tool_engine = PatientAgentTools(db, patient_id)
        
        self.tools_map = {
            "list_doctors": self.tool_engine.list_doctors,
            "get_doctor_treatments": self.tool_engine.get_doctor_treatments,
            "get_my_appointments": self.tool_engine.get_my_appointments,
            "cancel_appointment": self.tool_engine.cancel_appointment,
            "book_appointment": self.tool_engine.book_appointment,
            "check_availability": self.tool_engine.check_availability,
            "reschedule_appointment": self.tool_engine.reschedule_appointment,
            "book_followup": self.tool_engine.book_followup,
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
                    "name": "get_doctor_treatments",
                    "description": "Get all treatments offered by a specific doctor with prices.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_id": {"type": "string", "description": "ID of the doctor"}
                        },
                        "required": ["doctor_id"]
                    }
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
                            "doctor_id": {"type": "string"},
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
                            "appointment_id": {"type": "string", "description": "ID (e.g. '123') or 'current' for next visit."}
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
                            "doctor_id": {"type": "string", "description": "Doctor ID or name (e.g. '15' or 'Dr. Smith')"},
                            "date": {"type": "string", "description": "YYYY-MM-DD (e.g., 'tomorrow')."},
                            "time": {"type": "string", "description": "HH:MM (24-hour) e.g. 15:30."},
                            "reason": {"type": "string", "description": "Reason/Treatment."}
                        },
                        "required": ["doctor_id", "date", "time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "reschedule_appointment",
                    "description": "Reschedule an existing appointment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {"type": "string", "description": "ID or 'current'."},
                            "new_date": {"type": "string", "description": "YYYY-MM-DD."},
                            "new_time": {"type": "string", "description": "HH:MM."}
                        },
                        "required": ["appointment_id", "new_date", "new_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_followup",
                    "description": "Book a follow-up 2 weeks later.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "appointment_id": {"type": "string", "description": "ID to follow up on."}
                        },
                        "required": ["appointment_id"]
                    }
                }
            }
        ]

        self.system_prompt = f"""
            You are the Patient Assistant for Al-Shifa Dental Clinic.
            
            **CRITICAL: NO HALLUCINATIONS**
            - ONLY use data (doctors, treatments, slots) returned by tools.
            - NEVER invent or manufacture clinic data.
            - If a tool returns an Error or "No data", tell the user exactly that. DO NOT guess.
            
            **Booking Rules:**
            - If you have [Doctor, Date, Time, Reason] → CALL `book_appointment` IMMEDIATELY.
            - Do NOT ask for confirmation first.
            
            **Data Display:**
            - All lists (doctors, slots, treatments) MUST be formatted as numbered text in your response.
            - Always provide clickable buttons in brackets: `[Option Name]`.
            
            Current Date: {current_date}.
            Use tools for every query.
        """
        
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def process(self, query: str) -> dict:
        self.messages.append({"role": "user", "content": query})
        
        # Keep context lean
        if len(self.messages) > 11: 
            self.messages = [self.messages[0]] + self.messages[-10:]
            
        try:
            # 1. First Call (Intent detection)
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=self.messages,
                tools=self.tools_schema,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            content = message.content or ""
            tool_calls = message.tool_calls or []

            # FALLBACK: If model outputs text-based function tags instead of native tool_calls
            if not tool_calls and "<function=" in content:
                print("DEBUG: Detected text-based function tags. Parsing fallback...")
                matches = re.finditer(r'<function=(.*?)>(.*?)</function>', content, re.DOTALL)
                for i, match in enumerate(matches):
                    name = match.group(1).strip()
                    try:
                        args = json.loads(match.group(2).strip())
                        # Create a mock tool call object
                        from types import SimpleNamespace
                        mock_call = SimpleNamespace(
                            id=f"text_call_{i}_{datetime.now().timestamp()}",
                            function=SimpleNamespace(name=name, arguments=json.dumps(args))
                        )
                        tool_calls.append(mock_call)
                    except: continue

            if tool_calls:
                print(f"DEBUG: Agent requested {len(tool_calls)} tools.")
                if message.role: # Only append if it's a real assistant message
                    self.messages.append(message)
                else:
                    self.messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                        
                        # --- DOCTOR RESOLUTION ---
                        if "doctor_id" in args:
                            val = str(args["doctor_id"])
                            doctor = None
                            
                            # Try direct ID lookup first if numeric
                            if val.isdigit():
                                doctor = self.db.query(Doctor).filter(Doctor.id == int(val)).first()
                            
                            # If not found, try name/email search
                            if not doctor:
                                if "@" in val:
                                    user = self.db.query(User).filter(User.email.ilike(val)).first()
                                    if user: doctor = self.db.query(Doctor).filter(Doctor.user_id == user.id).first()
                                else:
                                    doctor = self.db.query(Doctor).join(Doctor.user).filter(
                                        Doctor.user.has(User.full_name.ilike(f"%{val}%"))
                                    ).first()
                                
                                # Fallback: search for digit in name
                                if not doctor and val.isdigit():
                                    doctor = self.db.query(Doctor).join(Doctor.user).filter(
                                        Doctor.user.has(User.full_name.ilike(f"%{val}%"))
                                    ).first()

                                if doctor:
                                    args["doctor_id"] = doctor.id
                                    print(f"DEBUG: Resolved '{val}' to ID {doctor.id}")
                        
                        # --- APPOINTMENT RESOLUTION ---
                        if "appointment_id" in args:
                            val = str(args["appointment_id"]).lower()
                            if val in ["current", "latest", "next", "upcoming"]:
                                next_appt = self.db.query(Appointment).filter(
                                    Appointment.patient_id == self.patient_id,
                                    Appointment.start_time > datetime.now(),
                                    Appointment.status != 'cancelled'
                                ).order_by(Appointment.start_time.asc()).first()
                                if next_appt: args["appointment_id"] = next_appt.id
                            elif val.isdigit():
                                args["appointment_id"] = int(val)

                        # Execution
                        print(f"DEBUG: Executing {func_name} with {args}")
                        if func_name in self.tools_map:
                            result = self.tools_map[func_name](**args)
                        else:
                            result = f"Error: Tool {func_name} not found."
                            
                    except Exception as e:
                        result = f"Error: {str(e)}"
                    
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })

                # 2. Second Call (Resolution)
                final_response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=self.messages
                )
                final_text = final_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_text})
                
                # Cleanup: Ensure no raw tags reach the user
                final_text = re.sub(r'<function=.*?>.*?</function>', '', final_text, flags=re.DOTALL)
                
                actions = re.findall(r'\[(.*?)\]', final_text)
                clean_text = re.sub(r'\[.*?\]', '', final_text).strip()
                return {"response": clean_text, "actions": actions}
            
            # No tools called
            final_text = content
            actions = re.findall(r'\[(.*?)\]', final_text)
            clean_text = re.sub(r'\[.*?\]', '', final_text).strip()
            return {"response": clean_text, "actions": actions}
            
        except Exception as e:
            print(f"DEBUG: Agent Error: {e}")
            return {"response": f"Error: {str(e)}", "actions": []}
