# case_tracking_agent/orchestrator.py
from services_shared.shared_models.agent_io import CaseTrackingAgentOutput, ClinicalSummaryData, ToolCall
from case_tracking_agent.tools.external_apis import TOOL_MANAGER, CASE_TOOL_DECLARATIONS
import json
from typing import List, Dict, Any

class AgentOrchestrator:
    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps

    def run_llm_step(self, prompt: str, tool_defs: List[Dict]) -> CaseTrackingAgentOutput:
        """MOCK LLM Logic for Clinical Synthesis."""
        
        # 1. Retrieval Step
        if "Generate case summary" in prompt and "PENDING_TOOL_CALL" not in prompt:
            return CaseTrackingAgentOutput(
                final_response="Retrieving clinical history...",
                status="PENDING_TOOL_CALL",
                tool_call=ToolCall(function_name="retrieve_clinical_notes", arguments={"patient_id": "P-123", "case_focus": "Implant #30"})
            )

        # 2. Synthesis & Routing Step
        if "raw_notes" in prompt:
            return CaseTrackingAgentOutput(
                final_response="Case summary generated. Follow-up scheduling requested.",
                status="SUCCESS",
                next_agent_route="AppointmentAgent/MilestoneSchedule",
                clinical_summary_data=ClinicalSummaryData(
                    summary_type="SOAP_NOTE",
                    subjective="Patient reports pain.",
                    objective="Stable bone integration.",
                    assessment="Ready for Crown."
                )
            )
            
        return CaseTrackingAgentOutput(final_response="Request processed.", status="SUCCESS")

    def process_request(self, input_data: Dict[str, Any]) -> CaseTrackingAgentOutput:
        # Allow passing raw dict or Pydantic model
        user_query = input_data.get('user_query_or_intent', '') if isinstance(input_data, dict) else input_data.user_query_or_intent
        current_prompt = f"[USER QUERY]: {user_query}"

        for step in range(self.max_steps):
            agent_output = self.run_llm_step(current_prompt, CASE_TOOL_DECLARATIONS)
            
            if agent_output.status != "PENDING_TOOL_CALL":
                return agent_output
            
            if agent_output.tool_call:
                tool_call = agent_output.tool_call
                tool_func = getattr(TOOL_MANAGER, tool_call.function_name, None)
                if tool_func:
                    tool_result = tool_func(**tool_call.arguments)
                    observation_str = json.dumps(tool_result)
                    current_prompt = f"CONTINUE: Tool {tool_call.function_name} result: {observation_str}"
                else:
                    return CaseTrackingAgentOutput(final_response="Tool error", status="ERROR")
        
        return CaseTrackingAgentOutput(final_response="Max steps reached", status="ERROR")