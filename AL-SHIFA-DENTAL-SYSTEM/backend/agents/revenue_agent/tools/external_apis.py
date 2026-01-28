# revenue_agent/tools/external_apis.py
from typing import Dict, Any, Optional, List
from services_shared.db_client import REVENUE_DB_CLIENT

class RevenueLiveTools:
    def get_patient_financial_status(self, patient_id: str, insurance_provider: Optional[str] = None) -> Dict[str, Any]:
        """Tool 1: Retrieves patient deductible/benefit status from the live DB."""
        sql = f"SELECT * FROM patient_financials WHERE patient_id='{patient_id}'"
        db_result = REVENUE_DB_CLIENT.execute_query(sql)
        
        # Mocking a successful DB response
        return {
            "status": "success", 
            "financial_data": {
                "deductible_remaining": 150.00, 
                "benefits_used": 50, 
                "insurance_status": "Active"
            }
        }

    def get_copay_verification(self, patient_id: str, procedure_cpt_code: str, insurance_provider: str) -> Dict[str, Any]:
        """Tool 2: Calculates final co-pay based on patient status, CPT, and insurer rates."""
        # In a real app, this would involve checking fee schedules in the DB.
        return {
            "status": "success", 
            "estimated_copay": 45.00, 
            "disclaimer": "Estimate based on current fee schedule."
        }

    def generate_profitability_report(self, report_type: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Tool 3: Runs complex analytical queries against the Financial Data Warehouse."""
        sql = f"CALL generate_report('{report_type}', '{start_date}', '{end_date}')"
        REVENUE_DB_CLIENT.execute_query(sql)
        
        # Mock Data for the Report
        return {
            "status": "report_ready", 
            "data": {
                "total_revenue": 85500.25, 
                "net_profit": 72675.21,
                "top_procedure": "Invisalign"
            }
        }

TOOL_MANAGER = RevenueLiveTools()

# Tool Definitions for the LLM
REVENUE_TOOL_DECLARATIONS: List[Dict] = [
    {"name": "get_patient_financial_status", "description": "Checks insurance and deductible.", "parameters": {"type": "object", "properties": {"patient_id": {"type": "string"}}, "required": ["patient_id"]}},
    {"name": "get_copay_verification", "description": "Calculates co-pay.", "parameters": {"type": "object", "properties": {"patient_id": {"type": "string"}, "procedure_cpt_code": {"type": "string"}, "insurance_provider": {"type": "string"}}, "required": ["patient_id", "procedure_cpt_code", "insurance_provider"]}},
    {"name": "generate_profitability_report", "description": "Generates financial reports.", "parameters": {"type": "object", "properties": {"report_type": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["report_type", "start_date", "end_date"]}}
]