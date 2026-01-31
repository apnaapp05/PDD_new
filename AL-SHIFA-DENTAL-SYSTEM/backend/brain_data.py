"""
BRAIN DATA - Level 4: The ML Training Set
Contains labeled examples for Scikit-Learn to train on startup.
"""

# --- 1. VOCABULARY (Keep for Fallback) ---
VOCAB = {
    "CMD_SHOW":   ["show", "get", "list", "display", "check", "find", "see", "tell", "what", "how", "status", "count"],
    "CMD_ADD":    ["add", "create", "new", "register", "insert", "update", "restock", "buy", "order", "increase", "book"],
    "CMD_CANCEL": ["cancel", "delete", "remove", "block", "close", "stop", "void", "erase"],
    "ENT_MONEY":  ["revenue", "income", "profit", "earnings", "sales", "money", "cash"],
    "ENT_STOCK":  ["stock", "inventory", "items", "supplies", "qty", "quantity"],
    "ENT_APPT":   ["appointment", "schedule", "booking", "visit", "slot", "calendar"],
    "TIME_TODAY": ["today", "now", "current", "daily"],
    "TIME_FUTURE": ["tomorrow", "next day", "upcoming", "week", "future"]
}

# --- 2. ML TRAINING DATA (The "Textbook" for the AI) ---
# Format: ("User Phrase", "INTENT_LABEL")
TRAINING_DATA = [
    # REVENUE
    ("how much money did we make", "REV_TODAY"),
    ("show me the income", "REV_TODAY"),
    ("what are the earnings today", "REV_TODAY"),
    ("revenue for yesterday", "REV_YESTERDAY"),
    ("income from last week", "REV_WEEK"),
    ("monthly profit report", "REV_MONTH"),
    ("predict next month revenue", "REV_FORECAST"), # NEW
    ("forecast earnings", "REV_FORECAST"),         # NEW
    
    # SCHEDULE
    ("show me today's schedule", "APPT_TODAY"),
    ("who is coming today", "APPT_TODAY"),
    ("appointments for today", "APPT_TODAY"),
    ("what is on the calendar tomorrow", "APPT_TOMORROW"),
    ("upcoming appointments this week", "APPT_WEEK"),
    ("how many patients are booked", "APPT_WEEK"),
    
    # CANCELLATION (Contextual)
    ("cancel the appointment", "APPT_CANCEL_ACTION"),
    ("delete this booking", "APPT_CANCEL_ACTION"),
    ("remove the 9pm slot", "APPT_CANCEL_ACTION"),
    ("patient called to cancel", "APPT_CANCEL_ACTION"),
    ("show cancelled appointments", "APPT_SHOW_CANCELLED"),
    ("how many cancellations", "APPT_SHOW_CANCELLED"),
    
    # INVENTORY
    ("check stock for gloves", "INV_SPECIFIC_GUESS"),
    ("how many masks do we have", "INV_SPECIFIC_GUESS"),
    ("inventory status", "INV_CHECK_LOW"),
    ("any items running low", "INV_CHECK_LOW"),
    ("i used 5 kits", "INV_USE_ACTION"),
    ("deduct 10 syringes", "INV_USE_ACTION"),
    
    # CHIT-CHAT
    ("hello", "CHAT_GREET"),
    ("hi bot", "CHAT_GREET"),
    ("thank you", "CHAT_THANKS"),
    ("who are you", "CHAT_WHO")
]

# --- 3. RESPONSES ---
RESPONSE_TEMPLATES = {
    "REV_FORECAST": [
        "📈 Based on recent trends, I forecast next month's revenue to be approx Rs. {amount}.",
        "Using linear analysis, we project an income of Rs. {amount} for next month."
    ],
    "FALLBACK": ["I'm still learning. Try 'Show revenue' or 'Cancel 9pm'."]
}
