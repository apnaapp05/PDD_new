# backend/agent_routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.llm_service import llm_client
import logging

router = APIRouter(prefix="/agent", tags=["AI Agents"])
logger = logging.getLogger(__name__)

# --- REQUEST MODELS ---
class AgentRequest(BaseModel):
    user_query: str
    session_id: str
    role: str = "doctor"
    agent_type: str = "general"

# --- SYSTEM PROMPTS ---
SYSTEM_PROMPTS = {
    "appointment": (
        "You are the Appointment Agent. Your goal is to manage the doctor's schedule efficiently. "
        "Assist with checking available slots, summarizing daily appointments, handling cancellations, "
        "and optimizing patient flow. Always format dates as YYYY-MM-DD and times clearly (AM/PM)."
    ),
    "revenue": (
        "You are the Revenue Agent. Your goal is to track the clinic's financial health. "
        "Analyze invoices, calculate total revenue, identify pending payments, and summarize earnings "
        "by treatment type. Focus on numbers, financial accuracy, and growth trends."
    ),
    "inventory": (
        "You are the Inventory Agent. Your goal is to ensure the clinic is well-stocked. "
        "Monitor item quantities, identify low-stock alerts, suggest reorders based on usage, "
        "and track material consumption per treatment. Prioritize supply chain efficiency."
    ),
    "casetracking": (
        "You are the Case Tracking Agent. Your goal is to monitor patient progress and clinical history. "
        "Review medical records, track treatment stages, summarize diagnoses, and ensure follow-up continuity. "
        "Use professional medical terminology and focus on patient outcomes."
    ),
    "patient": (
        "You are Dr. AI, a helpful dental assistant for patients. "
        "Answer questions about hygiene, symptoms, and booking. Keep answers simple and reassuring."
    )
}

@router.post("/execute")
async def execute_agent(request: AgentRequest):
    """
    Endpoint for the Patient Portal AI.
    """
    return await process_llm_request(request.user_query, "patient")

@router.post("/router")
async def route_agent(request: AgentRequest):
    """
    Endpoint for the specialized Doctor Agents.
    """
    # The frontend sends the agent ID (appointment, revenue, etc.) in the 'role' field
    agent_key = request.role.lower()
    
    # Fallback if an unknown key is sent
    if agent_key not in SYSTEM_PROMPTS:
        agent_key = "appointment" 
        
    return await process_llm_request(request.user_query, agent_key)

async def process_llm_request(user_query: str, role_key: str):
    if not llm_client or not llm_client.client:
        return {"response": "System Error: AI Service is unavailable. Please check API configuration."}

    system_instruction = SYSTEM_PROMPTS.get(role_key, "")
    
    # Construct the full prompt
    full_prompt = f"""
    SYSTEM INSTRUCTION:
    {system_instruction}

    USER QUERY:
    {user_query}
    """

    try:
        # Call the existing LLM service
        response_text = llm_client.generate_response(full_prompt)
        return {"response": response_text, "action_taken": None}
    except Exception as e:
        logger.error(f"Agent Error: {e}")
        raise HTTPException(status_code=500, detail="AI processing failed")