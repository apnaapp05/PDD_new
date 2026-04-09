"""
BRAIN DATA - Level 5: The Clinical OS
Expanded Vocabulary and Intents for Full Clinic Management.
"""

VOCAB = {
    "CMD_SHOW":   ["show", "list", "get", "display", "check", "find", "see", "tell", "what", "how", "status", "count", "history", "who"],
    "CMD_UPDATE": ["set", "change", "update", "increase", "decrease", "modify", "edit"],
    "CMD_ADD":    ["add", "create", "new", "register", "insert", "restock", "buy"],
    "CMD_CANCEL": ["cancel", "delete", "remove", "block", "close", "stop", "void"],
    
    "ENT_MONEY":  ["revenue", "finance", "earning", "profit", "expense", "cost", "invoice", "bill", "price", "amount"],
    "ENT_TREAT":  ["treatment", "procedure", "rct", "cleaning", "implant", "scaling", "extraction", "braces"],
    "ENT_STOCK":  ["stock", "inventory", "item", "glove", "mask", "buying cost", "kit", "syringe"],
    "ENT_PATIENT": ["patient", "record", "file", "history", "ali", "ahmed", "sarah"],
    
    "TIME_TODAY": ["today", "now", "current", "daily"],
    "TIME_FUTURE": ["tomorrow", "next", "upcoming", "week", "future"]
}

TRAINING_DATA = [
    # PATIENT HISTORY (Doctor Filtered)
    ("show Ali's history", "PAT_HISTORY"),
    ("what did we do for Ahmed", "PAT_HISTORY"),
    ("pull up Sarah's records", "PAT_HISTORY"),
    ("patient history for 03001234567", "PAT_HISTORY"),

    # TREATMENT MANAGEMENT
    ("update RCT price to 5000", "TREAT_PRICE_UPDATE"),
    ("change cost of cleaning to 1500", "TREAT_PRICE_UPDATE"),
    ("set extraction price to 2000", "TREAT_PRICE_UPDATE"),
    ("show all treatments", "TREAT_LIST"),
    ("list procedures", "TREAT_LIST"),

    # INVENTORY & EXPENSES
    ("set buying cost of gloves to 200", "INV_COST_UPDATE"),
    ("change mask buying price to 50", "INV_COST_UPDATE"),
    ("how much is our inventory worth", "FIN_EXPENSE"),
    ("calculate total expenses", "FIN_EXPENSE"),
    ("check stock for gloves", "INV_SPECIFIC_GUESS"),

    # BLOCKING (Cascade Logic)
    ("block 3pm today", "APPT_BLOCK"),
    ("close 4pm slot", "APPT_BLOCK"),
    ("block my schedule at 12:00", "APPT_BLOCK"),

    # FINANCIALS
    ("total profit for this month", "FIN_PROFIT"),
    ("how much did we earn vs spend", "FIN_PROFIT"),
    ("show pending invoices", "FIN_INVOICES"),
    ("list unpaid bills", "FIN_INVOICES"),
    ("revenue forecast", "REV_FORECAST"),
    ("how much money did we make today", "REV_TODAY"),

    # SCHEDULE & AUTO-PAY
    ("mark 9am as completed", "APPT_COMPLETE"),
    ("finish the 10am appointment", "APPT_COMPLETE"),
    ("todays schedule", "APPT_TODAY"),
    ("appointments tomorrow", "APPT_TOMORROW")
]

RULES = [
    {"intent": "PAT_HISTORY", "required": ["CMD_SHOW"]},
    {"intent": "TREAT_PRICE_UPDATE", "required": ["CMD_UPDATE", "ENT_TREAT"]},
    {"intent": "INV_COST_UPDATE", "required": ["CMD_UPDATE", "ENT_STOCK"]},
    {"intent": "APPT_BLOCK", "required": ["CMD_CANCEL"]},
    {"intent": "APPT_COMPLETE", "required": ["CMD_UPDATE"]}, # loosely matches 'mark', 'finish'
    {"intent": "REV_TODAY", "required": ["ENT_MONEY", "TIME_TODAY"]}
]

RESPONSE_TEMPLATES = {
    "FALLBACK": ["I am your Clinical OS. I can manage Patients, Treatments, Inventory, and Finance. Try 'Update RCT price' or 'Block 3pm'."]
}
