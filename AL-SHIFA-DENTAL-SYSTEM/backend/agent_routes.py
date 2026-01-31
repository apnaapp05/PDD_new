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

# LOGGING
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentBrain")

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])

# ==========================================
# 0. MEMORY (CONTEXT STORAGE)
# ==========================================
# Stores the last intent per user session (Simplified Global for Demo)
# In production, use a dictionary keyed by user_id
CHAT_CONTEXT = {
    "last_intent": None,
    "last_data": None
}

# ==========================================
# 1. ML BRAIN INITIALIZATION
# ==========================================
model = None

if HAS_ML:
    logger.info("🧠 Training Agentic Model...")
    X_train = [text for text, label in brain_data.TRAINING_DATA]
    y_train = [label for text, label in brain_data.TRAINING_DATA]
    model = make_pipeline(CountVectorizer(), MultinomialNB())
    model.fit(X_train, y_train)
    logger.info("✅ Agentic Model Trained!")

# ==========================================
# 2. INTELLIGENT HELPERS
# ==========================================
def sanitize_text(text):
    """Auto-corrects common typos."""
    corrections = {
        "shedule": "schedule", "schedual": "schedule", "apointment": "appointment",
        "revenue": "revenue", "invntory": "inventory", "tody": "today", 
        "todays": "today", "today's": "today", "tomorow": "tomorrow", "canceled": "cancelled",
        "detals": "details", "statue": "status"
    }
    clean_text = re.sub(r"[^\w\s]", "", text) 
    words = clean_text.split()
    fixed_words = [corrections.get(w, w) for w in words]
    return " ".join(fixed_words)

def predict_intent(text):
    """Uses Scikit-Learn to predict intent."""
    if not model: return "FALLBACK"
    predicted = model.predict([text])[0]
    probs = model.predict_proba([text])[0]
    confidence = max(probs)
    if confidence < 0.35: return "FALLBACK"
    return predicted

def fuzzy_fix_item_name(user_input, db: Session):
    items = db.query(models.InventoryItem).all()
    item_names = [i.name for i in items]
    if not item_names: return None
    match = process.extractOne(user_input, item_names, scorer=fuzz.token_sort_ratio)
    if match and match[1] > 60:
        return db.query(models.InventoryItem).filter(models.InventoryItem.name == match[0]).first()
    return None

def extract_time_object(text):
    text = text.lower().replace(" ", "")
    match = re.search(r'(\d{1,2})(:(\d{2}))?([ap]m)?', text)
    if not match: return None
    raw = match.group(0)
    try:
        for fmt in ["%I:%M%p", "%I%p", "%H:%M", "%H"]:
            try: return datetime.strptime(raw.upper(), fmt).time()
            except: continue
        nums = re.findall(r'\d+', raw)
        h = int(nums[0])
        m = int(nums[1]) if len(nums) > 1 else 0
        if "pm" in text and h < 12: h += 12
        if "am" in text and h == 12: h = 0
        return time(hour=h, minute=m)
    except: return None

def extract_number(text):
    match = re.search(r'\b\d+\b', text)
    if match: return int(match.group(0))
    return 1

# ==========================================
# 3. AGENT ENDPOINT
# ==========================================
@router.post("/chat")
def chat_with_agent(query: dict, db: Session = Depends(database.get_db)):
    raw_text = query.get("message", "").lower().strip()
    user_text = sanitize_text(raw_text)
    
    # --- A. INTENT DETECTION ---
    
    # 1. Critical Rules
    if "cancel" in user_text:
        if any(q in user_text for q in ["how", "show", "list"]): intent = "APPT_SHOW_CANCELLED"
        else: intent = "APPT_CANCEL_ACTION"
    elif "use" in user_text or "deduct" in user_text:
        intent = "INV_USE_ACTION"
    else:
        # 2. ML Prediction
        intent = predict_intent(user_text)
        
        # 3. Rule Safety Net
        if intent == "FALLBACK":
            # Safety Net Rules
            present_categories = set()
            for cat_name, keywords in brain_data.VOCAB.items():
                if any(k in user_text for k in keywords):
                    present_categories.add(cat_name)
            sorted_rules = sorted(brain_data.RULES, key=lambda x: len(x['required']), reverse=True)
            for rule in sorted_rules:
                if all(req in present_categories for req in rule['required']):
                    intent = rule['intent']
                    break
            if intent == "FALLBACK":
                if "check" in user_text or "stock" in user_text: intent = "INV_SPECIFIC_GUESS"

    # --- B. CONTEXTUAL REASONING (MEMORY) ---
    # If the user says "details", "status", or "more", and we have context, USE IT.
    is_follow_up = any(w in user_text for w in ["details", "status", "more", "full", "who"])
    
    if intent == "FALLBACK" and is_follow_up and CHAT_CONTEXT["last_intent"]:
        logger.info(f"💡 Using Context: {CHAT_CONTEXT['last_intent']}")
        intent = CHAT_CONTEXT["last_intent"] # Recall previous topic
    
    # Update Context for next turn
    if intent != "FALLBACK":
        CHAT_CONTEXT["last_intent"] = intent

    logger.info(f"Final Intent: {intent}")
    
    response_data = {}
    text_response = "I'm listening."
    doctor = db.query(models.Doctor).first()

    try:
        now = datetime.now()

        # --- LOGIC HANDLERS ---

        # 1. SCHEDULE (Rich Details Restored)
        if intent == "APPT_TODAY":
            appts = db.query(models.Appointment).filter(func.date(models.Appointment.start_time)==now.date()).order_by(models.Appointment.start_time).all()
            
            # Smart Filter: If user asks specifically for status/details, show EVERYTHING including cancelled
            show_all = "status" in user_text or "details" in user_text or "cancelled" in user_text
            active = appts if show_all else [a for a in appts if a.status != 'cancelled']
            
            if not active:
                text_response = "🗓️ No active appointments today."
            else:
                list_str = ""
                for a in active:
                    # Rich Icons
                    if a.status == "completed": icon = "✅"
                    elif a.status == "cancelled": icon = "❌"
                    elif a.status == "in_progress": icon = "▶️"
                    else: icon = "⏳"
                    
                    p_name = a.patient.user.full_name if a.patient and a.patient.user else "Unknown"
                    time_s = a.start_time.strftime('%I:%M %p')
                    treatment = a.treatment_type if a.treatment_type else "General Checkup"
                    
                    # Format: ✅ 09:00 AM - Ali Khan (Completed) | Treatment
                    list_str += f"{icon} **{time_s}** - {p_name}\n   Status: {a.status} | {treatment}\n"
                
                count_label = "Total" if show_all else "Active"
                text_response = f"🗓️ **Today's Schedule ({len(active)} {count_label}):**\n\n{list_str}"

        # 2. TOMORROW (Rich Details)
        elif intent == "APPT_TOMORROW":
            d = (now + timedelta(days=1)).date()
            appts = db.query(models.Appointment).filter(func.date(models.Appointment.start_time) == d, models.Appointment.status != 'cancelled').order_by(models.Appointment.start_time).all()
            if not appts: text_response = "🔮 No appointments tomorrow."
            else:
                list_str = ""
                for a in appts:
                    p_name = a.patient.user.full_name if a.patient and a.patient.user else "Unknown"
                    list_str += f"• {a.start_time.strftime('%I:%M %p')} - {p_name} ({a.treatment_type})\n"
                text_response = f"🔮 Tomorrow ({len(appts)}):\n{list_str}"

        # 3. REVENUE FORECAST (Pandas)
        elif intent == "REV_FORECAST":
            invoices = db.query(models.Invoice).filter(models.Invoice.status=="paid").all()
            if not invoices:
                text_response = "Not enough data to forecast revenue."
            else:
                data = [{"date": i.created_at, "amount": i.amount} for i in invoices]
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                daily = df.groupby(df['date'].dt.date)['amount'].sum()
                avg_daily = daily.mean()
                forecast = avg_daily * 30
                text_response = f"📈 Based on your daily average of Rs. {avg_daily:.0f}, I project next month's revenue to be approx Rs. {forecast:,.0f}."

        # 4. INVENTORY (RapidFuzz)
        elif intent == "INV_SPECIFIC_GUESS":
             ignore = ["check", "stock", "how", "many", "have", "we", "the", "of"]
             clean = " ".join([w for w in user_text.split() if w not in ignore])
             item = fuzzy_fix_item_name(clean, db)
             if item: text_response = f"🔍 Found '{item.name}': {item.quantity} {item.unit} in stock."
             else: text_response = f"I couldn't find an item matching '{clean}'."

        # 5. CANCELLATION ACTION
        elif intent == "APPT_CANCEL_ACTION":
            t = extract_time_object(user_text)
            if not t: text_response = "What time? (e.g., 'Cancel 9pm')"
            else:
                req_dt = datetime.combine(now.date(), t)
                appt = db.query(models.Appointment).filter(
                    models.Appointment.doctor_id == doctor.id,
                    models.Appointment.status != "cancelled",
                    models.Appointment.start_time >= req_dt - timedelta(minutes=30),
                    models.Appointment.start_time <= req_dt + timedelta(minutes=30)
                ).first()
                if appt:
                    appt.status = "cancelled"
                    inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == appt.id, models.Invoice.status == "pending").first()
                    if inv: inv.status = "cancelled"
                    db.commit()
                    text_response = f"✅ Cancelled appointment at {appt.start_time.strftime('%I:%M %p')}."
                else: text_response = f"No appointment found at {t.strftime('%I:%M %p')}."

        # 6. BASIC QUERIES
        elif intent == "REV_TODAY":
            val = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.status=="paid", func.date(models.Invoice.created_at)==now.date()).scalar() or 0
            text_response = f"💰 Today's Revenue: Rs. {val}"

        elif intent == "APPT_WEEK":
             d = now.date() + timedelta(days=7)
             c = db.query(models.Appointment).filter(models.Appointment.start_time >= now, models.Appointment.start_time <= datetime.combine(d, datetime.min.time()), models.Appointment.status != 'cancelled').count()
             text_response = f"📅 Weekly Outlook: {c} active appointments."

        elif intent == "REV_WEEK":
             start = now - timedelta(days=7)
             val = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.status=="paid", models.Invoice.created_at >= start).scalar() or 0
             text_response = f"💰 Revenue (Last 7 Days): Rs. {val}"
             
        elif intent == "INV_CHECK_LOW":
             low = db.query(models.InventoryItem).filter(models.InventoryItem.quantity < models.InventoryItem.min_threshold).all()
             names = ", ".join([i.name for i in low]) if low else "None"
             text_response = f"📦 Low Stock Items: {names}"

        elif intent == "INV_USE_ACTION":
            qty = extract_number(user_text)
            text_response = f"Assuming you want to deduct {qty} items. Please specify the item name next time."

        else:
            text_response = brain_data.RESPONSE_TEMPLATES.get("FALLBACK")[0]

    except Exception as e:
        logger.error(f"Error: {e}")
        text_response = f"System Error: {str(e)}"

    return {"response": text_response, "intent": intent}
