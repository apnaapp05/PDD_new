# dental-ai-system/inventory_agent/orchestrator.py
from typing import List, Dict, Any
from services_shared.shared_models.agent_io import InventoryAgentOutput, AlertData, ToolCall
from inventory_agent.tools.external_apis import TOOL_MANAGER
from services_shared.message_bus.publisher import GLOBAL_PUBLISHER
import json

class InventoryAgentOrchestrator:
    def __init__(self, tracer=None, max_steps: int = 5):
        self.max_steps = max_steps

    def process_request(self, input_data: Dict[str, Any]) -> InventoryAgentOutput:
        # MOCK LOGIC: Direct mapping for demo purposes
        user_query = input_data.get('user_query_or_intent', '')
        
        if "Trigger 30-day forecast" in user_query:
             # In a real ReAct loop, the LLM would decide to call this tool
             tool_result = TOOL_MANAGER.run_demand_forecast(item_id="RESIN-C2", forecast_period_days=30)
             
             if tool_result['stock_after_forecast'] < 20:
                 alert_data = AlertData(item_id="RESIN-C2", severity="CRITICAL", reason="Low Stock Forecast", reorder_quantity=100)
                 GLOBAL_PUBLISHER.publish_structured_message("inventory-alerts-critical", alert_data.model_dump())
                 return InventoryAgentOutput(final_response="Alert published.", status="ALERT_TRIGGERED", alert_data=alert_data)
        
        return InventoryAgentOutput(final_response="Request processed.", status="SUCCESS")