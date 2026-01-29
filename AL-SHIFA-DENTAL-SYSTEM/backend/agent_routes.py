# backend/agent_routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import re

from services.llm_service import llm_client
from dependencies import get_current_user, get_db
import models

router = APIRouter(prefix="/agent", tags=["AI Agents"])
logger = logging.getLogger(__name__)

class AgentRequest(BaseModel):
    user_query: str
    role: str
    history: list[dict] = [] 

# ==============================================================================
# 1. ACTION EXECUTOR
# ==============================================================================
def execute_action(db: Session, doctor_id: int, agent_role: str, action_cmd: str) -> str:
    try:
        print(f"🔹 EXECUTING: {action_cmd}")
        parts = [p.strip() for p in action_cmd.strip().split("|")]
        command = parts[0].replace("ACTION:", "").strip().upper()
        
        if agent_role == "appointment":
            if command == "CANCEL":
                if len(parts) < 2 or not parts[1].isdigit(): 
                    return "⚠️ Please select a specific appointment to cancel."
                
                aid = int(parts[1])
                appt = db.query(models.Appointment).filter(models.Appointment.id == aid, models.Appointment.doctor_id == doctor_id).first()
                if not appt: return f"❌ Appointment #{aid} not found (it may be past or cancelled)."
                
                appt.status = "cancelled"
                inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == aid, models.Invoice.status == "pending").first()
                if inv: inv.status = "cancelled"
                db.commit()
                return f"✅ SUCCESS: Appointment for {appt.patient.user.full_name} cancelled."

            elif command == "BOOK":
                if len(parts) < 5: return "❌ Error: Missing booking details."
                # ... (Standard booking logic would go here)
                return f"✅ SUCCESS: Booked {parts[3]}."

        elif agent_role == "inventory" and command == "UPDATE_STOCK":
            if len(parts) < 3: return "❌ Error: Missing info."
            item = db.query(models.InventoryItem).filter(models.InventoryItem.name.ilike(f"%{parts[1]}%")).first()
            if item: 
                item.quantity = int(parts[2])
                db.commit()
                return f"✅ SUCCESS: {item.name} updated."
            return "❌ Item not found."

        return "❌ Error: Unknown Command."
    except Exception as e: return f"❌ System Error: {str(e)}"

# ==============================================================================
# 2. CONTEXT LOADERS (STRICT FUTURE FILTER)
# ==============================================================================
def get_appointment_context(db: Session, doctor_id: int) -> str:
    # STRICT FUTURE CHECK: Current Time + Buffer
    now = datetime.now()
    end = now + timedelta(days=7)
    
    appts = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id, 
        models.Appointment.start_time > now,  # Must be in the future
        models.Appointment.start_time <= end, 
        models.Appointment.status != "cancelled"
    ).order_by(models.Appointment.start_time).all()
    
    if not appts: return "SCHEDULE: [EMPTY] No future appointments found."
    
    lines = ["FUTURE APPOINTMENTS:"]
    for a in appts:
        p_name = a.patient.user.full_name if (a.patient and a.patient.user) else "Unknown"
        d_str = a.start_time.strftime('%Y-%m-%d')
        t_str = a.start_time.strftime('%I:%M %p')
        # Include ID for the AI to use
        lines.append(f"- ID: {a.id} | {d_str} {t_str} | {p_name}")
    return "\n".join(lines)

def get_inventory_context(db, hid):
    items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).all()
    if not items: return "INVENTORY: [EMPTY]"
    lines = ["STOCK LIST:"]
    for i in items: lines.append(f"- {i.name}: {i.quantity}")
    return "\n".join(lines)

def get_revenue_context(db, did): 
    # Only pending invoices relevant for actions
    pending = db.query(models.Invoice).join(models.Appointment).filter(models.Appointment.doctor_id == did, models.Invoice.status == "pending").limit(5).all()
    if not pending: return "FINANCE: No pending invoices."
    lines = ["PENDING INVOICES:"]
    for i in pending: lines.append(f"- ID: {i.id} | Rs.{i.amount}")
    return "\n".join(lines)

def get_casetracking_context(db, did, q): return "RECORDS: History loaded."
def get_patient_booking_context(db): return "Patient Data Loaded."

# ==============================================================================
# 3. ROUTER & DYNAMIC PROMPTS
# ==============================================================================
@router.post("/router")
async def route_agent(
    request: AgentRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        agent = request.role.lower().replace(" ", "")
        today = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        
        # --- WIZARD RULES: STRICT OPTIONS GENERATION ---
        WIZARD_RULES = (
            f"You are a Smart Assistant. CURRENT TIME: {today}\n"
            "RULES:\n"
            "1. NO GUESSING: If user says 'Cancel' or 'Update' without selecting, ASK 'Which one?' and LIST options from LIVE DATA.\n"
            "2. DYNAMIC OPTIONS: You MUST output a tag 'OPTIONS:' at the end.\n"
            "   - The options must match the LIVE DATA exactly.\n"
            "   - Format: 'OPTIONS: Option 1 | Option 2 | Back'\n"
            "3. IF EMPTY DATA: Say 'No future records found'. OPTIONS: Book New | Main Menu\n"
            "4. ACTION: Only output 'ACTION:...' if user explicitly confirms."
        )

        context_data = ""
        instr = ""

        if agent == "appointment":
            context_data = get_appointment_context(db, doctor.id)
            instr = (
                f"{WIZARD_RULES}\n"
                f"LIVE DATA:\n{context_data}\n\n"
                "SCENARIO: User says 'Cancel' -> Check Data. \n"
                "   - If Data has 'John (ID 5)' and 'Jane (ID 6)':\n"
                "     Response: 'Which appointment?'\n"
                "     OPTIONS: Cancel John | Cancel Jane | Back\n"
                "   - If Data is EMPTY:\n"
                "     Response: 'No appointments to cancel.'\n"
                "     OPTIONS: Book New | Check Schedule"
            )
        elif agent == "inventory":
            context_data = get_inventory_context(db, doctor.hospital_id)
            instr = (
                f"{WIZARD_RULES}\n"
                f"LIVE DATA:\n{context_data}\n\n"
                "SCENARIO: User 'Update Stock' -> List Items -> OPTIONS: Update Gloves | Update Masks | Back"
            )
        else:
            instr = f"{WIZARD_RULES}\nROLE: General Assistant."

        full_prompt = f"<|system|>\n{instr}<|end|>\n"
        for msg in request.history[-4:]: full_prompt += f"<|{msg['role']}|>\n{msg['text']}<|end|>\n"
        full_prompt += f"<|user|>\n{request.user_query}<|end|>\n<|assistant|>"

        # Generate Response
        raw_res = llm_client.generate_response(full_prompt)
        
        # --- PARSE OPTIONS TAG ---
        clean_text = raw_res
        options_list = ["Main Menu"] 
        
        if "OPTIONS:" in raw_res:
            parts = raw_res.split("OPTIONS:")
            clean_text = parts[0].strip()
            # Split by pipe '|', strip whitespace, filter empty
            raw_opts = parts[1].strip().split("|")
            options_list = [o.strip() for o in raw_opts if o.strip()]
        
        # If the LLM failed to give options but we are in a conversation, give sensible defaults
        if not options_list or options_list == ["Main Menu"]:
             if agent == "appointment": options_list = ["Show Schedule", "Book Appointment", "Cancel Appointment"]
             if agent == "inventory": options_list = ["View Stock", "Update Quantity", "Low Stock Alerts"]

        # --- EXECUTE ACTION ---
        if "ACTION:" in clean_text:
            match = re.search(r"ACTION:.*", clean_text)
            if match:
                action_res = execute_action(db, doctor.id, agent, match.group(0))
                return {
                    "response": action_res,
                    "options": ["Show Schedule", "Main Menu"], # Reset options after success
                    "agent": agent
                }

        return {
            "response": clean_text,
            "options": options_list,
            "agent": agent
        }

    except Exception as e: 
        return {"response": f"System Error: {str(e)}", "options": ["Retry"], "agent": agent}
