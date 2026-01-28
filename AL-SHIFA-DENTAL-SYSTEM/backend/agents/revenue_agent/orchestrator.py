# revenue_agent/orchestrator.py
from services_shared.shared_models.agent_io import RevenueAgentOutput, FinancialReportData, ToolCall, RevenueAgentInput
from revenue_agent.tools.external_apis import TOOL_MANAGER, REVENUE_TOOL_DECLARATIONS
import json
from typing import List, Dict, Any

class RevenueAgentOrchestrator:
    def __init__(self, tracer=None, max_steps: int = 5):
        self.max_steps = max_steps

    def run_llm_step(self, prompt: str, tool_defs: List[Dict]) -> RevenueAgentOutput:
        """MOCK LLM Logic for Financials."""
        if "Generate Revenue Reports" in prompt and "PENDING_TOOL_CALL" not in prompt:
            return RevenueAgentOutput(
                final_response="Initiating profitability report generation...",
                status="PENDING_TOOL_CALL",
                tool_call=ToolCall(function_name="generate_profitability_report", arguments={"report_type": "MONTHLY_REVENUE", "start_date": "2025-11-01", "end_date": "2025-11-30"})
            )
        
        if "report_ready" in prompt:
            return RevenueAgentOutput(
                final_response="Monthly Revenue Report generated successfully.",
                status="REPORT_GENERATED",
                financial_report_data=FinancialReportData(
                    calculation_type="MONTHLY_REVENUE",
                    patient_responsibility=0.0,
                    disclaimer="Internal Use Only.",
                    data_payload={"Monthly_Revenue": 85500.25, "Net_Profit": 72675.21}
                )
            )
        return RevenueAgentOutput(final_response="Request processed.", status="SUCCESS")

    def process_request(self, input_data: Dict[str, Any]) -> RevenueAgentOutput:
        # Convert dict to Pydantic model if needed, or use directly
        user_query = input_data.get('user_query_or_intent', '')
        current_prompt = f"[USER QUERY]: {user_query}"

        for step in range(self.max_steps):
            agent_output = self.run_llm_step(current_prompt, REVENUE_TOOL_DECLARATIONS)
            
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
                    return RevenueAgentOutput(final_response="Tool error", status="ERROR")
        
        return RevenueAgentOutput(final_response="Max steps reached", status="ERROR")