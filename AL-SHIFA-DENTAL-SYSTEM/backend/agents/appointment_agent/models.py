# dental-ai-system/appointment_agent/models.py
from services_shared.shared_models.agent_io import (
    AppointmentAgentInput, AppointmentAgentOutput, PatientContext, ToolCall
)
from typing import List, Dict

# Define the Tool Declarations for the LLM
TOOL_FUNCTIONS_DECLARATION: List[Dict] = [
    {
        "name": "search_availability",
        "description": "Searches for available appointment slots.",
        "parameters": {
            "type": "object",
            "properties": {
                "procedure_type": {"type": "string"},
                "requested_datetime_range": {"type": "string"},
                "doctor_name": {"type": "string"}
            },
            "required": ["procedure_type", "requested_datetime_range"]
        }
    },
    {
        "name": "schedule_appointment",
        "description": "Books a final appointment slot (WRITE to DB).",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "slot_id": {"type": "string"},
                "procedure_type": {"type": "string"}
            },
            "required": ["patient_id", "slot_id"]
        }
    },
    {
        "name": "send_reminder",
        "description": "Publishes a request to the Message Bus to send a patient reminder (A2A).",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "appointment_id": {"type": "string"},
                "message_type": {"type": "string", "enum": ["confirmation_request", "simple_reminder"]}
            },
            "required": ["patient_id", "appointment_id", "message_type"]
        }
    }
]