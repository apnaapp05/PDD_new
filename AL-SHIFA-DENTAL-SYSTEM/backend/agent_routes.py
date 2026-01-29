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
        
        # --- APPOINTMENT ---
        if agent_role == "appointment":
            if command == "CANCEL":
                if len(parts) < 2 or not parts[1].isdigit(): return "❌ Error: Invalid Selection."
                aid = int(parts[1])
                appt = db.query(models.Appointment).filter(models.Appointment.id == aid).first()
                if not appt: return "❌ Not found."
                appt.status = "cancelled"
                db.commit()
                return f"✅ Cancelled appointment for {appt.patient.user.full_name}."

            elif command == "BOOK":
                if len(parts) < 5: return "❌ Error: Missing info."
                # ... (Keep existing booking logic) ...
                return f"✅ Booked {parts[3]}."

        # --- REVENUE ---
        elif agent_role == "revenue" and command == "UPDATE_INVOICE":
            if len(parts) < 3: return "❌ Error: Missing info."
            inv = db.query(models.Invoice).filter(models.Invoice.id == int(parts[1])).first()
            if inv: inv.status = parts[2].lower(); db.commit(); return f"✅ Invoice #{parts[1]} updated."
            return "❌ Invoice not found."

        # --- INVENTORY ---
        elif agent_role == "inventory" and command == "UPDATE_STOCK":
            if len(parts) < 3: return "❌ Error: Missing info."
            item = db.query(models.InventoryItem).filter(models.InventoryItem.name.ilike(f"%{parts[1]}%")).first()
            if item: item.quantity = int(parts[2]); db.commit(); return f"✅ {item.name} updated."
            return "❌ Item not found."

        return "✅ Action Processed."
    except Exception as e: return f"❌ System Error: {str(e)}"

# ==============================================================================
# 2. CONTEXT LOADERS (Simplified for Brevity)
# ==============================================================================
def get_appointment_context(db, did):
    now = datetime.now()
    end = now + timedelta(days=7)
    appts = db.query(models.Appointment).filter(models.Appointment.doctor_id == did, models.Appointment.start_time >= now, models.Appointment.status != "cancelled").all()
    if not appts: return "SCHEDULE: [EMPTY]"
    lines = ["ACTIVE APPOINTMENTS:"]
    for a in appts: lines.append(f"- ID: {a.id} | {a.start_time.strftime('%I:%M %p')} | {a.patient.user.full_name}")
    return "\n".join(lines)

def get_inventory_context(db, hid):
    items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).all()
    if not items: return "INVENTORY: [EMPTY]"
    lines = ["STOCK:"]
    for i in items: lines.append(f"- {i.name}: {i.quantity}")
    return "\n".join(lines)

# (Other context loaders remain similar - keeping short for script)
def get_revenue_context(db, did): return "FINANCIALS: See Dashboard."
def get_casetracking_context(db, did, q): return "RECORDS: See History."
def get_patient_booking_context(db): return "Patient Context."

# ==============================================================================
# 3. ROUTER & DYNAMIC OPTION PARSER
# ==============================================================================
@router.post("/router")
async def route_agent(
    request: AgentRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        agent = request.role.lower().replace(" ", "")
        today = datetime.now().strftime("%Y-%m-%d")
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        
        # --- PROMPT CONSTRUCTION ---
        context_data = ""
        
        # UNIVERSAL RULES
        # The key is the "OPTIONS:" tag at the end
        CORE_INSTRUCTIONS = (
            f"You are a Smart Assistant. TODAY: {today}\n"
            "1. USE 'LIVE DATA'. If empty, say so.\n"
            "2. IF user gives a command (e.g. 'Cancel'), ASK for selection using DATA.\n"
            "3. ACTION FORMAT: 'ACTION: COMMAND | ID'\n"
            "4. CRITICAL: End response with 'OPTIONS: Option1 | Option2 | Option3'.\n"
            "   - If asking to cancel -> OPTIONS: Cancel John | Cancel Jane | Back\n"
            "   - If empty -> OPTIONS: Book New | Check Schedule\n"
            "   - ALWAYS provide 2-4 relevant short options separated by '|'."
        )

        if agent == "appointment":
            context_data = get_appointment_context(db, doctor.id)
            instr = f"{CORE_INSTRUCTIONS}\nLIVE DATA:\n{context_data}\nROLE: Manage Appointments."
        elif agent == "inventory":
            context_data = get_inventory_context(db, doctor.hospital_id)
            instr = f"{CORE_INSTRUCTIONS}\nLIVE DATA:\n{context_data}\nROLE: Manage Stock."
        else:
            instr = f"{CORE_INSTRUCTIONS}\nROLE: General Assistant."

        full_prompt = f"<|system|>\n{instr}<|end|>\n"
        for msg in request.history[-4:]: full_prompt += f"<|{msg['role']}|>\n{msg['text']}<|end|>\n"
        full_prompt += f"<|user|>\n{request.user_query}<|end|>\n<|assistant|>"

        # --- LLM GENERATION ---
        raw_response = llm_client.generate_response(full_prompt)
        
        # --- PARSING RESPONSE & OPTIONS ---
        clean_text = raw_response
        options_list = []
        
        # Extract OPTIONS
        if "OPTIONS:" in raw_response:
            parts = raw_response.split("OPTIONS:")
            clean_text = parts[0].strip()
            # Split by '|' and clean up
            raw_opts = parts[1].strip().split("|")
            options_list = [o.strip() for o in raw_opts if o.strip()]
        
        # Extract ACTION (if any)
        if "ACTION:" in clean_text:
            match = re.search(r"ACTION:.*", clean_text)
            if match: 
                action_res = execute_action(db, doctor.id, agent, match.group(0))
                # If action success, give default next steps
                return {
                    "response": action_res, 
                    "options": ["Show Schedule", "Main Menu"], 
                    "agent": agent
                }

        # Return Text + Parsed Options
        return {
            "response": clean_text,
            "options": options_list if options_list else ["Main Menu", "Show Schedule"],
            "agent": agent
        }

    except Exception as e: return {"response": f"System Error: {str(e)}", "options": []}
