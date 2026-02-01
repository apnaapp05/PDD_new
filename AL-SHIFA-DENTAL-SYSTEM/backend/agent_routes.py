import random
import re
import logging
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, time
import database
import models
import brain_data

# --- AGENTIC LIBRARIES ---
try:
    from rapidfuzz import process, fuzz
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import make_pipeline
    HAS_ML = True
except ImportError:
    HAS_ML = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentBrain")

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])

# --- 1. ML INIT ---
model = None
if HAS_ML:
    logger.info("🧠 Training Agentic Model...")
    X_train = [text for text, label in brain_data.TRAINING_DATA]
    y_train = [label for text, label in brain_data.TRAINING_DATA]
    model = make_pipeline(CountVectorizer(), MultinomialNB())
    model.fit(X_train, y_train)

CHAT_CONTEXT = {"last_intent": None}

# --- 2. HELPERS ---
def sanitize_text(text):
    corrections = {
        "shedule": "schedule", "apointment": "appointment", "revenue": "revenue",
        "invntory": "inventory", "tody": "today", "canceled": "cancelled",
        "rct": "Root Canal", "cleaning": "Teeth Cleaning"
    }
    clean = re.sub(r"[^\w\s]", "", text) 
    words = clean.split()
    return " ".join([corrections.get(w, w) for w in words])

def predict_intent(text):
    if not model: return "FALLBACK"
    probs = model.predict_proba([text])[0]
    if max(probs) < 0.35: return "FALLBACK"
    return model.predict([text])[0]

def extract_time(text):
    match = re.search(r'(\d{1,2})(:(\d{2}))?([ap]m)?', text.lower().replace(" ", ""))
    if match:
        raw = match.group(0)
        for fmt in ["%I:%M%p", "%I%p", "%H:%M", "%H"]:
            try: return datetime.strptime(raw.upper(), fmt).time()
            except: continue
    return None

def extract_money(text):
    match = re.search(r'\b\d+\b', text)
    return int(match.group(0)) if match else None

# --- 3. MASTER ROUTE ---
@router.post("/chat")
def chat_with_agent(query: dict, db: Session = Depends(database.get_db)):
    raw_text = query.get("message", "").lower().strip()
    user_text = sanitize_text(raw_text)
    
    # Intent Detection
    if "block" in user_text: intent = "APPT_BLOCK"
    elif "history" in user_text: intent = "PAT_HISTORY"
    elif "update" in user_text and "price" in user_text: intent = "TREAT_PRICE_UPDATE"
    elif "buying cost" in user_text: intent = "INV_COST_UPDATE"
    elif "profit" in user_text: intent = "FIN_PROFIT"
    elif "complete" in user_text or "mark" in user_text: intent = "APPT_COMPLETE"
    else:
        intent = predict_intent(user_text)
        if intent == "FALLBACK":
             # Fallback Rule Logic (Simplified)
             if "schedule" in user_text: intent = "APPT_TODAY"
             elif "revenue" in user_text: intent = "REV_TODAY"
             elif "stock" in user_text: intent = "INV_SPECIFIC_GUESS"

    CHAT_CONTEXT["last_intent"] = intent
    logger.info(f"Intent: {intent} | Text: {user_text}")

    doctor = db.query(models.Doctor).first()
    now = datetime.now()
    text_response = "I processed your request."

    try:
        # === A. SCHEDULE & BLOCKING ===
        if intent == "APPT_BLOCK":
            t = extract_time(user_text)
            if not t: text_response = "Please specify time. (e.g., 'Block 3pm')"
            else:
                target_dt = datetime.combine(now.date(), t)
                # Cascading Check
                existing = db.query(models.Appointment).filter(
                    models.Appointment.doctor_id == doctor.id,
                    models.Appointment.start_time == target_dt,
                    models.Appointment.status != "cancelled"
                ).first()
                
                msg = ""
                if existing:
                    existing.status = "cancelled"
                    inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == existing.id).first()
                    if inv: inv.status = "cancelled"
                    msg = f"⚠️ Cancelled existing appt for {existing.patient.user.full_name}. "
                
                # Create Block
                block = models.Appointment(doctor_id=doctor.id, start_time=target_dt, status="blocked", treatment_type="Blocked Slot")
                db.add(block)
                db.commit()
                text_response = f"✅ {msg}Time slot {t.strftime('%I:%M %p')} is now BLOCKED."

        # === B. AUTO-PAY & COMPLETION ===
        elif intent == "APPT_COMPLETE":
            t = extract_time(user_text)
            if not t: text_response = "Which appointment? (e.g., 'Mark 9am as completed')"
            else:
                target_dt = datetime.combine(now.date(), t)
                appt = db.query(models.Appointment).filter(
                    models.Appointment.doctor_id == doctor.id,
                    models.Appointment.status != "cancelled",
                    models.Appointment.start_time == target_dt
                ).first()
                
                if appt:
                    appt.status = "completed"
                    # Auto-Pay Invoice
                    inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == appt.id).first()
                    inv_msg = ""
                    if inv:
                        inv.status = "paid"
                        inv_msg = "and Invoice marked as PAID"
                    db.commit()
                    text_response = f"✅ Appointment completed {inv_msg}."
                else: text_response = "No active appointment found at that time."

        # === C. PATIENT HISTORY (Doctor Filtered) ===
        elif intent == "PAT_HISTORY":
            # Extract name roughly
            words = user_text.split()
            ignore = ["show", "history", "for", "me", "what", "did", "we", "do", "record", "of"]
            name_query = " ".join([w for w in words if w not in ignore])
            
            p_user = db.query(models.User).filter(models.User.full_name.ilike(f"%{name_query}%"), models.User.role=="patient").first()
            if not p_user: text_response = f"I couldn't find a patient named '{name_query}'."
            else:
                pat = db.query(models.Patient).filter(models.Patient.user_id == p_user.id).first()
                # Filter by THIS doctor
                history = db.query(models.Appointment).filter(
                    models.Appointment.patient_id == pat.id,
                    models.Appointment.doctor_id == doctor.id
                ).order_by(models.Appointment.start_time.desc()).all()
                
                if not history: text_response = f"No history found for {p_user.full_name} with you."
                else:
                    text_response = f"📜 **History for {p_user.full_name}:**\n"
                    for h in history:
                        text_response += f"• {h.start_time.strftime('%Y-%m-%d')}: {h.treatment_type} ({h.status})\n"

        # === D. TREATMENTS & INVENTORY ===
        elif intent == "TREAT_PRICE_UPDATE":
            price = extract_money(user_text)
            if not price: text_response = "Please specify the new price."
            else:
                # Guess treatment name
                treats = db.query(models.Treatment).all()
                t_names = [t.name for t in treats]
                match = process.extractOne(user_text, t_names)
                if match and match[1] > 50:
                    t = db.query(models.Treatment).filter(models.Treatment.name == match[0]).first()
                    old = t.cost
                    t.cost = float(price)
                    db.commit()
                    text_response = f"✅ Updated {t.name} price: Rs. {old} -> Rs. {t.cost}"
                else: text_response = "I couldn't match the treatment name."

        elif intent == "INV_COST_UPDATE":
            cost = extract_money(user_text)
            items = db.query(models.InventoryItem).all()
            i_names = [i.name for i in items]
            match = process.extractOne(user_text, i_names)
            if match and match[1] > 50:
                item = db.query(models.InventoryItem).filter(models.InventoryItem.name == match[0]).first()
                item.buying_cost = float(cost)
                db.commit()
                text_response = f"✅ Set buying cost for {item.name} to Rs. {cost}."
            else: text_response = "Item not found."

        # === E. FINANCIALS (Profit & Expenses) ===
        elif intent == "FIN_PROFIT":
            # Revenue = Sum of Paid Invoices (This Month)
            start = now.replace(day=1, hour=0, minute=0)
            revenue = db.query(func.sum(models.Invoice.amount)).filter(
                models.Invoice.status == "paid", models.Invoice.created_at >= start
            ).scalar() or 0
            
            # Expenses = Total Value of Current Inventory (Simulated Expense)
            # OR (Restock Quantity * Buying Cost) if we tracked history. 
            # For now, using Total Inventory Valuation as "Capital Locked".
            inventory_val = db.query(func.sum(models.InventoryItem.quantity * models.InventoryItem.buying_cost)).scalar() or 0
            
            # Profit (Simple View)
            profit = revenue - inventory_val # Simplified
            
            text_response = f"💰 **Financial Snapshot (This Month):**\n• Revenue: Rs. {revenue}\n• Inventory Asset Value: Rs. {inventory_val}\n• **Net Flow:** Rs. {profit}"

        elif intent == "FIN_INVOICES":
            pending = db.query(models.Invoice).filter(models.Invoice.status == "pending").all()
            if not pending: text_response = "✅ No pending invoices."
            else:
                text_response = f"📄 **Pending Invoices ({len(pending)}):**\n"
                for i in pending:
                     p_name = i.patient.user.full_name if i.patient else "Unknown"
                     text_response += f"• #{i.id}: {p_name} - Rs. {i.amount}\n"
        
        # === F. DEFAULT SCHEDULE ===
        elif intent == "APPT_TODAY":
             appts = db.query(models.Appointment).filter(func.date(models.Appointment.start_time)==now.date()).all()
             active = [a for a in appts if a.status != 'cancelled']
             if not active: text_response = "🗓️ No active appointments today."
             else:
                 text_response = f"🗓️ **Today ({len(active)}):**\n"
                 for a in active:
                     icon = "✅" if a.status=="completed" else "⏳"
                     p = a.patient.user.full_name if a.patient else "Unknown"
                     text_response += f"{icon} {a.start_time.strftime('%I:%M %p')} - {p} ({a.status})\n"

        else:
             text_response = brain_data.RESPONSE_TEMPLATES.get("FALLBACK")[0]

    except Exception as e:
        logger.error(f"Error: {e}")
        text_response = f"System Error: {str(e)}"

    return {"response": text_response, "intent": intent}
