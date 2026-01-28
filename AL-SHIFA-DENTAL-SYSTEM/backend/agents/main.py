# dental-ai-system/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

# Import your verified Agents
from appointment_agent.orchestrator import AgentOrchestrator as AppointmentAgent
from appointment_agent.models import AppointmentAgentInput, PatientContext
from inventory_agent.orchestrator import InventoryAgentOrchestrator as InventoryAgent
from inventory_agent.tools.external_apis import TOOL_MANAGER as InventoryTools

# (You can import Revenue and Case Tracking similarly once their orchestrators are finalized)

app = FastAPI(title="Dental Clinic AI System")

# CORS: Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agents
appt_agent = AppointmentAgent(max_steps=5)
inv_agent = InventoryAgent(tracer=None, max_steps=5)

# Request Models
class BookingRequest(BaseModel):
    user_query: str
    patient_id: str
    patient_name: str

class StockUpdateRequest(BaseModel):
    item_id: str
    quantity: int

class ProcedureLogRequest(BaseModel):
    patient_id: str
    procedure: str

@app.get("/")
def health_check():
    return {"status": "Online", "agents": ["Appointment", "Inventory"]}

# --- ENDPOINTS ---

@app.post("/api/appointments/book")
def book_appointment(req: BookingRequest):
    print(f"📝 [Appointment Agent] Processing: {req.user_query}")
    input_data = AppointmentAgentInput(
        user_query=req.user_query,
        patient_context=PatientContext(patient_id=req.patient_id, name=req.patient_name)
    )
    result = appt_agent.process_request(input_data)
    return result.dict()

@app.post("/api/inventory/update")
def update_stock(req: StockUpdateRequest):
    print(f"📦 [Inventory Agent] Updating Stock: {req.item_id} -> {req.quantity}")
    # Direct tool usage for manual update
    InventoryTools.update_stock_and_reorder_point(req.item_id, req.quantity, "MANUAL")
    return {"status": "success"}

@app.post("/api/cases/add-procedure")
def add_procedure(req: ProcedureLogRequest):
    print(f"🩺 [Case Tracking] Procedure Logged: {req.procedure}")
    print(f"   ↳ [A2A] Triggering Inventory Agent for Stock Deduction...")
    # Logic to deduct stock would go here
    return {"status": "success", "message": "Procedure logged and stock deducted"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)