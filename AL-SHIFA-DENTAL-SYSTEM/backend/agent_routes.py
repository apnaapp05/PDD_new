from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import re

from dependencies import get_current_user, get_db
import models

router = APIRouter(prefix="/agent", tags=["AI Agents"])
logger = logging.getLogger(__name__)

class AgentRequest(BaseModel):
    user_query: str
    role: str
    history: list[dict] = []

# ==============================================================================
# 1. APPOINTMENT LOGIC (STRICT)
# ==============================================================================
def handle_appointment_logic(db: Session, doctor_id: int, query: str):
    q_norm = query.lower().strip()
    now = datetime.now()
    
    # A. SHOW TODAY (Specific)
    if "today" in q_norm:
        end_of_day = now.replace(hour=23, minute=59, second=59)
        appts = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == doctor_id,
            models.Appointment.start_time >= now,
            models.Appointment.start_time <= end_of_day,
            models.Appointment.status != "cancelled"
        ).order_by(models.Appointment.start_time).all()
        
        if not appts:
            return {"response": f"📅 **Today ({now.strftime('%b %d')}):** No remaining appointments.", "options": ["Book Appointment", "Show Upcoming"]}
            
        msg = "📅 **Today's Remaining Schedule:**\n"
        opts = []
        for a in appts:
            t_str = a.start_time.strftime("%I:%M %p")
            msg += f"- **{t_str}**: {a.patient.user.full_name}\n"
            opts.append(f"Cancel {a.patient.user.full_name}")
            
        return {"response": msg, "options": opts + ["Book New"]}

    # B. CANCEL REQUEST (Show Dynamic Buttons)
    if "cancel" in q_norm and "id" not in q_norm:
        # Show future appointments
        appts = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == doctor_id,
            models.Appointment.start_time > now,
            models.Appointment.status != "cancelled"
        ).order_by(models.Appointment.start_time).limit(5).all()
        
        if not appts:
            return {"response": "ℹ️ You have no active appointments to cancel.", "options": ["Book Appointment", "Show Schedule"]}
            
        msg = "Which appointment would you like to cancel? Click below:"
        opts = []
        for a in appts:
            # Format: "Cancel Name (Time) - ID 5"
            t_str = a.start_time.strftime("%I:%M %p")
            opts.append(f"Cancel {a.patient.user.full_name} ({t_str}) - ID {a.id}")
        
        opts.append("Back")
        return {"response": msg, "options": opts}

    # C. EXECUTE CANCEL (Regex Trigger)
    if "cancel" in q_norm and "id" in q_norm:
        match = re.search(r"id\s*(\d+)", q_norm)
        if match:
            aid = int(match.group(1))
            appt = db.query(models.Appointment).filter(models.Appointment.id == aid, models.Appointment.doctor_id == doctor_id).first()
            if appt:
                appt.status = "cancelled"
                db.query(models.Invoice).filter(models.Invoice.appointment_id == aid, models.Invoice.status == "pending").update({"status": "cancelled"})
                db.commit()
                return {"response": f"✅ Success: Cancelled appointment for {appt.patient.user.full_name}.", "options": ["Show Schedule", "Main Menu"]}
            
        return {"response": "❌ Appointment not found.", "options": ["Show Schedule"]}

    # D. DEFAULT / FALLBACK
    return {
        "response": "I can help you Schedule, Book, or Cancel.",
        "options": ["Show Today's Schedule", "Cancel Appointment", "Book Appointment"]
    }

# ==============================================================================
# 2. ROUTER
# ==============================================================================
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
        return {"response": f"System Error: {str(e)}", "options": ["Retry"]}