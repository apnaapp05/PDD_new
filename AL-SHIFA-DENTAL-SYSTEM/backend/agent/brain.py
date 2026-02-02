from sqlalchemy.orm import Session
import pandas as pd
from rapidfuzz import process, fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import re

from services.appointment_service import AppointmentService
from services.analytics_service import AnalyticsService
from services.inventory_service import InventoryService
from services.treatment_service import TreatmentService
from services.patient_service import PatientService
from services.clinical_service import ClinicalService
from services.settings_service import SettingsService
from agent.analyst import AnalystEngine
from services.response_generator import ResponseGenerator
from utils.nlp_parser import DateParser
from utils.smart_parser import SmartParser
from agent.intents import INTENT_TRAINING_DATA

class ClinicAgent:
    _sessions = {}

    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id
        
        self.appt = AppointmentService(db, doctor_id)
        self.fin = AnalyticsService(db, doctor_id)
        self.inv = InventoryService(db, doctor_id)
        self.pat = PatientService(db, doctor_id)
        self.treat = TreatmentService(db, doctor_id)
        self.clinical = ClinicalService(db, doctor_id)
        self.settings = SettingsService(db, doctor_id)
        self.analyst = AnalystEngine(db, doctor_id)
        
        self.parser = SmartParser()
        self.vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        self.intent_keys = []
        self._train_intent_model()
        
        if doctor_id not in self._sessions:
            self._sessions[doctor_id] = {"intent": None, "slots": {}}
        self.context = self._sessions[doctor_id]

    def _train_intent_model(self):
        corpus = []
        for intent, phrases in INTENT_TRAINING_DATA.items():
            for p in phrases:
                corpus.append(p)
                self.intent_keys.append(intent)
        if corpus:
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def predict_intent(self, query):
        if not self.intent_keys: return None
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)
        best_idx = similarities.argmax()
        score = similarities[0, best_idx]
        
        # Beast Mode Heuristics
        q = query.lower()
        if score < 0.4:
            if "start" in q and "visit" in q: return "clinical_start"
            if "finish" in q or "complete" in q: return "clinical_complete"
            if "alert" in q or "threshold" in q: return "inventory_threshold"
            if "add" in q and "treatment" in q: return "treatment_create"
            if "delete" in q and "treatment" in q: return "treatment_delete"
            return None
            
        return self.intent_keys[best_idx]

    def process(self, query: str):
        q = query.lower().strip()
        
        # 1. Analyst Check (unless inside a checklist flow)
        if self.analyst.is_analysis_query(q) and not self.context["intent"]:
            return ResponseGenerator.simple(self.analyst.analyze(q))

        # 2. Intent Logic
        if self.context["intent"]:
            intent = self.context["intent"]
        else:
            intent = self.predict_intent(q)

        try:
            # === CLINICAL OPERATIONS (Start/Complete) ===
            if intent == "clinical_start":
                self.context["intent"] = "clinical_start"
                slots = self.context["slots"]
                
                if not slots.get("patient"):
                    # Extract Name
                    clean = q.replace("start", "").replace("visit", "").replace("appointment", "").strip()
                    if len(clean) > 2: slots["patient"] = clean
                    else: return ResponseGenerator.simple("Which patient are we starting?")
                
                res = self.clinical.mark_in_progress(slots["patient"])
                self.context["intent"] = None
                self.context["slots"] = {}
                
                if res: return ResponseGenerator.simple(f"✅ **Visit Started.** {res.patient.user.full_name} is now In Progress.")
                return ResponseGenerator.error("Could not find a confirmed appointment for them today.")

            if intent == "clinical_complete":
                self.context["intent"] = "clinical_complete"
                slots = self.context["slots"]
                
                if not slots.get("patient"):
                    clean = q.replace("complete", "").replace("finish", "").replace("visit", "").strip()
                    if len(clean) > 2: slots["patient"] = clean
                    else: return ResponseGenerator.simple("Which patient is finished?")
                
                res = self.clinical.complete_appointment(slots["patient"]) # Returns tuple (appt, inv)
                self.context["intent"] = None
                self.context["slots"] = {}
                
                if res:
                    appt, inv = res
                    return ResponseGenerator.simple(f"✅ **Visit Completed.**\nInvoice #{inv.id} generated for **Rs. {inv.amount}**.")
                return ResponseGenerator.error("Could not find an in-progress visit for them.")

            # === INVENTORY (Set Threshold) ===
            if intent == "inventory_threshold":
                self.context["intent"] = "inventory_threshold"
                slots = self.context["slots"]
                
                if not slots.get("item"):
                    clean = q.replace("set threshold", "").replace("alert me if", "").strip()
                    # Extract item name logic (simplified)
                    import re
                    # If user says "alert if gloves drop below 5", we split by digits
                    match = re.split(r'\d+', clean)[0].strip()
                    if len(match) > 2: slots["item"] = match
                    else: return ResponseGenerator.simple("For which item?")

                if not slots.get("limit"):
                    nums = re.findall(r'\d+', q)
                    if nums: slots["limit"] = int(nums[-1]) # Take last number usually
                    else: return ResponseGenerator.simple(f"What is the low stock limit for **{slots['item']}**?")
                
                res = self.inv.set_threshold(slots["item"], slots["limit"])
                self.context["intent"] = None
                self.context["slots"] = {}
                if res: return ResponseGenerator.simple(f"✅ Alert set. I'll warn you if **{res.name}** drops below **{res.min_threshold}**.")
                return ResponseGenerator.error("Item not found.")

            # === TREATMENTS (CRUD) ===
            if intent == "treatment_create":
                self.context["intent"] = "treatment_create"
                slots = self.context["slots"]
                
                if not slots.get("name"):
                    clean = q.replace("add new treatment", "").replace("create procedure", "").strip()
                    if len(clean)>2: slots["name"] = clean
                    else: return ResponseGenerator.simple("What is the name of the new treatment?")
                
                if not slots.get("cost"):
                    nums = re.findall(r'\d+', q)
                    if nums: slots["cost"] = float(nums[0])
                    else: return ResponseGenerator.simple(f"What is the price for **{slots['name']}**?")
                
                res = self.treat.create_treatment(slots["name"], slots["cost"])
                self.context["intent"] = None
                self.context["slots"] = {}
                if res: return ResponseGenerator.simple(f"✅ Added **{res.name}** to the price list at **Rs. {res.cost}**.")
                return ResponseGenerator.error("Treatment already exists.")

            if intent == "treatment_delete":
                self.context["intent"] = "treatment_delete"
                slots = self.context["slots"]
                
                if not slots.get("name"):
                    clean = q.replace("delete treatment", "").replace("remove", "").strip()
                    if len(clean)>2: slots["name"] = clean
                    else: return ResponseGenerator.simple("Which treatment should I delete?")
                
                # Check for confirmation
                if "yes" not in q and "confirm" not in q and slots.get("name"):
                     return ResponseGenerator.simple(f"⚠️ Are you sure you want to delete **{slots['name']}** permanently?")
                
                if slots.get("name"):
                    res = self.treat.delete_treatment(slots["name"])
                    self.context["intent"] = None
                    self.context["slots"] = {}
                    if res: return ResponseGenerator.simple(f"🗑️ Deleted **{slots['name']}** from the list.")
                    return ResponseGenerator.error("Treatment not found.")

            # === EXISTING FEATURES (Preserved) ===
            # (Copying the logic from previous Beast Brain for brevity - ensuring they exist)
            if intent == "treatment_update":
                # ... (Previous Logic) ...
                self.context["intent"] = "treatment_update"
                slots = self.context["slots"]
                if not slots.get("name"):
                     all_treats = self.treat.get_all_treatments()
                     names = [t.name for t in all_treats]
                     match = process.extractOne(q, names, scorer=fuzz.token_set_ratio)
                     if match and match[1] > 65: slots["name"] = match[0]
                     else: return {"text": "Select treatment:", "buttons": [{"label": n, "action": n, "type": "chat"} for n in names[:5]]}
                if not slots.get("price"):
                     nums = re.findall(r'\d+', q)
                     if nums: slots["price"] = float(nums[0])
                     else: return ResponseGenerator.simple(f"New price for {slots['name']}?")
                updated = self.treat.update_price(slots["name"], slots["price"])
                self.context["intent"] = None
                self.context["slots"] = {}
                return ResponseGenerator.simple(f"✅ Price updated for **{updated.name}**.")

            if intent == "inventory_create":
                 # ... (Previous Logic) ...
                self.context["intent"] = "inventory_create"
                slots = self.context["slots"]
                if not slots.get("name"):
                    clean = q.replace("create item", "").strip()
                    if len(clean)>2: slots["name"] = clean
                    else: return ResponseGenerator.simple("Item Name?")
                if not slots.get("quantity"):
                    nums = re.findall(r'\d+', q)
                    if nums: slots["quantity"] = int(nums[0])
                    else: return ResponseGenerator.simple("Initial Stock?")
                created = self.inv.create_item(slots["name"], slots["quantity"])
                self.context["intent"] = None
                self.context["slots"] = {}
                return ResponseGenerator.simple(f"✅ Created **{created.name}**.")

            # Fallbacks for View-Only intents
            if intent == "dashboard_stats": return ResponseGenerator.simple(f"📊 {self.analyst.analyze('dashboard')}")
            if intent == "finance_view": return ResponseGenerator.simple(self.analyst.analyze(q))
            if intent == "inventory_check": return ResponseGenerator.simple(f"📦 {self.inv.get_low_stock() and 'Low stock detected' or 'Stock healthy'}")
            if intent == "treatment_list": return ResponseGenerator.list_treatments(self.treat.get_all_treatments())
            if intent == "schedule_view": return ResponseGenerator.success_schedule(self.appt.get_schedule(datetime.now().strftime("%Y-%m-%d")), "Today")

            return ResponseGenerator.simple("I'm listening. Try 'Start visit', 'Set alert for Gloves', or 'Add Treatment'.")

        except Exception as e:
            self.context["intent"] = None
            return ResponseGenerator.error(f"System Error: {str(e)}")
