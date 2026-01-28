# dental-ai-system/services_shared/shared_models/agent_io.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- COMMON TYPES ---
class PatientContext(BaseModel):
    patient_id: str
    name: str
    preferred_contact: str = 'sms'

class SessionTurn(BaseModel):
    role: str
    content: str

class ToolCall(BaseModel):
    function_name: str
    arguments: Dict[str, Any]

class AlertData(BaseModel):
    item_id: str
    severity: str = Field(..., enum=["CRITICAL", "HIGH", "MEDIUM"])
    reason: str
    reorder_quantity: Optional[int] = None

# --- 1. APPOINTMENT AGENT ---
class AppointmentAgentInput(BaseModel):
    user_query: str
    patient_context: PatientContext
    session_history: Optional[List[SessionTurn]] = None

class AppointmentAgentOutput(BaseModel):
    final_response: str
    status: str = Field(..., enum=["SUCCESS", "PENDING_TOOL_CALL", "CLARIFICATION_NEEDED", "ERROR"])
    tool_call: Optional[ToolCall] = None
    next_agent_route: Optional[str] = None

# --- 2. INVENTORY AGENT ---
class InventoryAgentInput(BaseModel):
    trigger_type: str = Field(..., enum=["USER_QUERY", "SYSTEM_CRON", "A2A_REQUEST"])
    user_query_or_intent: str

class InventoryAgentOutput(BaseModel):
    final_response: str
    status: str = Field(..., enum=["SUCCESS", "PENDING_TOOL_CALL", "ALERT_TRIGGERED", "ERROR"])
    tool_call: Optional[ToolCall] = None
    alert_data: Optional[AlertData] = None

# --- 3. REVENUE AGENT ---
class RevenueAgentInput(BaseModel):
    user_query_or_intent: str
    financial_context: Optional[Dict[str, Any]] = None

class FinancialReportData(BaseModel):
    calculation_type: str
    patient_responsibility: float
    disclaimer: str
    data_payload: Optional[Dict[str, Any]] = None
    
class RevenueAgentOutput(BaseModel):
    final_response: str
    status: str = Field(..., enum=["SUCCESS", "PENDING_TOOL_CALL", "DATA_UNAVAILABLE", "ERROR", "REPORT_GENERATED"])
    tool_call: Optional[ToolCall] = None
    financial_report_data: Optional[FinancialReportData] = None

# --- 4. CASE TRACKING AGENT ---
class CaseTrackingAgentInput(BaseModel):
    user_query_or_intent: str
    patient_id: str
    case_focus: str

class ClinicalSummaryData(BaseModel):
    summary_type: str
    subjective: str
    objective: str
    assessment: str
    
class CaseTrackingAgentOutput(BaseModel):
    final_response: str
    status: str = Field(..., enum=["SUCCESS", "PENDING_TOOL_CALL", "REFLECTION_REQUIRED", "ERROR"])
    tool_call: Optional[ToolCall] = None
    clinical_summary_data: Optional[ClinicalSummaryData] = None
    next_agent_route: Optional[str] = None