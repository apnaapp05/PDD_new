# dental-ai-system/appointment_agent/orchestrator.py
from appointment_agent.models import AppointmentAgentInput, AppointmentAgentOutput, ToolCall, TOOL_FUNCTIONS_DECLARATION
from appointment_agent.tools.external_apis import TOOL_MANAGER
import json
from typing import List, Dict, Any, Optional
import logging

# Set up basic logging if no tracer is provided
logging.basicConfig(level=logging.INFO)

def run_llm_step(prompt: str, tool_defs: List[Dict]) -> AppointmentAgentOutput:
    """MOCK LLM call for demonstration."""
    if "The previous tool call to schedule_appointment returned" in prompt:
        return AppointmentAgentOutput(
            final_response="Your cleaning appointment is confirmed. I am now routing your co-pay question to the Revenue Agent.",
            status="SUCCESS",
            next_agent_route="RevenueAgent/CoPayLookup"
        )
    elif "book a cleaning next Tuesday" in prompt:
        return AppointmentAgentOutput(
            final_response="One moment while I check availability...",
            status="PENDING_TOOL_CALL",
            tool_call=ToolCall(
                function_name="search_availability",
                arguments={"procedure_type": "cleaning", "requested_datetime_range": "next Tuesday at 3 PM", "doctor_name": "Dr. Jones"}
            )
        )
    elif "The previous tool call to search_availability returned" in prompt:
         # Simulate LLM deciding to book after seeing availability
         return AppointmentAgentOutput(
            final_response="Slot found. Booking now...",
            status="PENDING_TOOL_CALL",
            tool_call=ToolCall(
                function_name="schedule_appointment",
                arguments={"patient_id": "P-45890", "slot_id": "SLOT-123", "procedure_type": "cleaning"}
            )
        )
    return AppointmentAgentOutput(final_response="LLM is not live. Using mock fallback.", status="CLARIFICATION_NEEDED")

class AgentOrchestrator:
    def __init__(self, tracer=None, max_steps: int = 5):
        self.max_steps = max_steps
        self.tracer = tracer 

    def process_request(self, input_data: AppointmentAgentInput) -> AppointmentAgentOutput:
        current_prompt = f"[USER QUERY]: {input_data.user_query}"
        
        for step in range(self.max_steps):
            # In a real app, we would trace this step using self.tracer
            agent_output = run_llm_step(current_prompt, TOOL_FUNCTIONS_DECLARATION)
            
            if agent_output.status != "PENDING_TOOL_CALL":
                return agent_output
            
            if agent_output.tool_call:
                tool_call = agent_output.tool_call
                tool_func = getattr(TOOL_MANAGER, tool_call.function_name, None)
                
                if tool_func:
                    tool_result = tool_func(**tool_call.arguments)
                    observation_str = json.dumps(tool_result)
                    current_prompt = f"CONTINUE: The previous tool call to {tool_call.function_name} returned the following result: {observation_str}. Based on this, what is the next action?"
                else:
                    return AppointmentAgentOutput(final_response="Internal tool error.", status="ERROR")
                    
        return AppointmentAgentOutput(final_response="Max steps reached.", status="ERROR")