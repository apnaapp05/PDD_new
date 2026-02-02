from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth_dependency import get_current_user
from pydantic import BaseModel
from agent.patient_brain import PatientBrain

router = APIRouter(prefix="/patient/agent", tags=["Patient AI"])

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_with_patient_bot(req: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "patient":
        raise HTTPException(403, "Only patients can use this bot")
    
    brain = PatientBrain(db)
    response = brain.process_message(req.message, user.id)
    return response

