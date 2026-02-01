import models
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from database import get_db
from models import User, Doctor
from agent.brain import ClinicAgent # Import the new brain
from dependencies import get_current_user

router = APIRouter(prefix="/doctor/agent", tags=["Agent"])

@router.post("/chat")
def chat_with_agent(query: str = Body(..., embed=True), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Security Check
    if user.role != "doctor":
        return {"response": "Access Denied: Only doctors can use the Agent."}
    
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        return {"response": "Doctor profile not found."}

    # 2. Instantiate the Agent
    agent = ClinicAgent(db, doctor.id)
    
    # 3. Process
    try:
        response_text = agent.process(query)
        return {"response": response_text}
    except Exception as e:
        return {"response": f"❌ Agent Error: {str(e)}"}

