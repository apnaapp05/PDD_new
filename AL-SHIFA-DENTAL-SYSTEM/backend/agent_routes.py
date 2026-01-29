# backend/agent_routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import re
from dependencies import get_current_user, get_db
import models

router = APIRouter(prefix="/agent", tags=["AI Agents"])

class AgentRequest(BaseModel):
    user_query: str
    role: str
    history: list[dict] = []

def handle_appointment_logic(db: Session, doctor_id: int, query: str):
    q_norm = query.lower().strip()
    now = datetime.now()
    
    # 1. CANCEL FLOW
    if "cancel" in q_norm:
        # Fetch active appointments
        appts = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == doctor_id,
            models.Appointment.start_time > now,
            models.Appointment.status != "cancelled"
        ).order_by(models.Appointment.start_time).limit(5).all()
        
        # Scenario A: No appointments
        if not appts:
            return {
                "response": "ℹ️ You have no future appointments to cancel.",
                "options": ["Book Appointment", "Show Schedule"]
            }
            
        # Scenario B: Appointments found
        msg = "Which appointment to cancel? Click one:"
        opts = []
        for a in appts:
            t_str = a.start_time.strftime("%I:%M %p")
            # Button format: Cancel John (10:00 AM) - ID 5
            opts.append(f"Cancel {a.patient.user.full_name} ({t_str}) - ID {a.id}")
            
        opts.append("Back")
        return {"response": msg, "options": opts}

    # 2. DEFAULT
    return {
        "response": "I can help you Schedule, Book, or Cancel.",
        "options": ["Show Schedule", "Cancel Appointment", "Book Appointment"]
    }

@router.post("/router")
async def route_agent(
    request: AgentRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        agent = request.role.lower().replace(" ", "")
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        
        if agent == "appointment":
            return handle_appointment_logic(db, doctor.id, request.user_query)
            
        return {"response": "Agent Ready.", "options": ["Main Menu"]}
    except Exception as e:
        return {"response": f"Error: {str(e)}", "options": ["Retry"]}
