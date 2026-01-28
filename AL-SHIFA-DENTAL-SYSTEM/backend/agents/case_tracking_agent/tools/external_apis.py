# case_tracking_agent/tools/external_apis.py
from typing import Dict, Any, Optional, List
from services_shared.db_client import CASE_TRACKING_DB_CLIENT
from services_shared.message_bus.publisher import GLOBAL_PUBLISHER

class CaseTrackingLiveTools:
    def retrieve_clinical_notes(self, patient_id: str, case_focus: str) -> Dict[str, Any]:
        """Tool 1: Retrieves raw notes from the DB."""
        sql = f"SELECT notes_text FROM clinical_records WHERE patient_id='{patient_id}' AND focus='{case_focus}'"
        CASE_TRACKING_DB_CLIENT.execute_query(sql)
        
        # Mocking the return of unstructured notes
        return {
            "status": "success", 
            "raw_notes": "S: Patient reports throbbing pain. O: X-ray shows stable bone. A: Ready for Crown. P: Schedule next visit."
        }

    def propose_next_appointment(self, patient_id: str, required_procedure: str) -> Dict[str, Any]:
        """Tool 2: Triggers the Appointment Agent via A2A message."""
        payload = {"patient_id": patient_id, "procedure": required_procedure}
        
        # A2A: Publish to the shared message bus
        GLOBAL_PUBLISHER.publish_structured_message('milestone-scheduling', payload)
        
        return {"status": "success", "message": "Scheduling request queued for Appointment Agent."}

TOOL_MANAGER = CaseTrackingLiveTools()

# Tool Definitions for the LLM
CASE_TOOL_DECLARATIONS: List[Dict] = [
    {"name": "retrieve_clinical_notes", "description": "Gets raw clinical history.", "parameters": {"type": "object", "properties": {"patient_id": {"type": "string"}, "case_focus": {"type": "string"}}, "required": ["patient_id", "case_focus"]}},
    {"name": "propose_next_appointment", "description": "Triggers A2A scheduling.", "parameters": {"type": "object", "properties": {"patient_id": {"type": "string"}, "required_procedure": {"type": "string"}}, "required": ["patient_id", "required_procedure"]}}
]