import pandas as pd
import random
from sqlalchemy.orm import Session
from models import Appointment, InventoryItem, Patient, Invoice, Treatment, User, Doctor
from datetime import datetime, timedelta, date

class AnalystEngine:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id
        
        self.TEMPLATES = {
            "good": ["Mashallah, excellent results.", "Performance is strong.", "Looking good."],
            "warn": ["Attention needed.", "Performance is below average.", "Check these numbers."],
            "neutral": ["Here is the report.", "Data summary:", "Analysis complete."]
        }

    def is_analysis_query(self, query: str) -> bool:
        triggers = [
            "how many", "how much", "count", "total", "average", "most", "least", "which", 
            "unique", "list of", "report", "analyze", "status", "overview", "trends", "summary",
            "revenue", "income", "stock"
        ]
        return any(t in query.lower() for t in triggers)

    def analyze(self, query: str):
        q = query.lower()
        try:
            if "dashboard" in q or "today" in q: return self._analyze_dashboard()
            if "schedule" in q or "time" in q or "busy" in q: return self._analyze_schedule(q)
            if "patient" in q or "visit" in q: return self._analyze_patients(q)
            if "stock" in q or "inventory" in q: return self._analyze_inventory(q)
            if "revenue" in q or "finance" in q or "money" in q: return self._analyze_finance(q)
            return "I can analyze Dashboard, Schedule, Patients, Inventory, or Finance."
        except Exception as e:
            return f"Analysis Error: {str(e)}"

    def _get_date_filter(self, query: str):
        today = datetime.now().date()
        if "yesterday" in query:
            d = today - timedelta(days=1)
            return d, d, "Yesterday"
        if "tomorrow" in query:
            d = today + timedelta(days=1)
            return d, d, "Tomorrow"
        if "week" in query:
            start = today - timedelta(days=today.weekday())
            return start, today, "This Week"
        if "month" in query:
            start = today.replace(day=1)
            return start, today, "This Month"
        return today, today, "Today"

    def _get_amount(self, invoice):
        """Universal Adapter: Finds the money column automatically"""
        candidates = ['amount', 'total_amount', 'total', 'cost', 'price', 'grand_total', 'final_amount']
        for attr in candidates:
            if hasattr(invoice, attr):
                val = getattr(invoice, attr)
                return float(val) if val else 0.0
        return 0.0

    def _analyze_dashboard(self):
        today = datetime.now().date()
        
        # 1. Get Appointments
        appts = self.db.query(Appointment).filter(Appointment.doctor_id == self.doc_id).all()
        
        # 2. Get Invoices (Robust Join)
        try:
            invoices = self.db.query(Invoice).join(Appointment).filter(Appointment.doctor_id == self.doc_id).all()
        except:
            invoices = []

        df_appt = pd.DataFrame([{"date": a.start_time.date()} for a in appts])
        df_inv = pd.DataFrame([{"date": i.created_at.date(), "amount": self._get_amount(i)} for i in invoices])
        
        count = len(df_appt[df_appt['date'] == today]) if not df_appt.empty else 0
        rev = df_inv[df_inv['date'] == today]['amount'].sum() if not df_inv.empty else 0
        
        mood = random.choice(self.TEMPLATES["good"] if count > 0 else self.TEMPLATES["neutral"])
        
        return (
            f"📊 **Daily Briefing ({today})**\n\n"
            f"{mood}\n"
            f"- **Volume:** {count} appointments.\n"
            f"- **Revenue:** Rs. {rev:,.2f}\n"
        )

    def _analyze_finance(self, q):
        start_date, end_date, label = self._get_date_filter(q)
        
        try:
            invoices = self.db.query(Invoice).join(Appointment).filter(Appointment.doctor_id == self.doc_id).all()
        except:
            return "❌ Database Error: Could not link Invoices to Appointments."

        if not invoices: return f"💰 **Financial Report ({label})**\nNo revenue recorded."
        
        df = pd.DataFrame([{"amount": self._get_amount(i), "status": i.status, "date": i.created_at.date()} for i in invoices])
        
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        filtered_df = df.loc[mask]
        
        total_rev = filtered_df['amount'].sum()
        pending = filtered_df[filtered_df['status'] == 'pending']['amount'].sum()
        count = len(filtered_df)
        
        return (
            f"💰 **Financial Report ({label})**\n"
            f"- **Total Revenue:** Rs. {total_rev:,.2f}\n"
            f"- **Transactions:** {count} invoices.\n"
            f"- **Outstanding:** Rs. {pending:,.2f}"
        )

    def _analyze_inventory(self, q):
        # Robust Doctor Lookup
        doc = self.db.query(Doctor).filter((Doctor.id == self.doc_id) | (Doctor.user_id == self.doc_id)).first()
        if not doc: return "Error: Doctor profile not found."
        
        items = self.db.query(InventoryItem).filter(InventoryItem.hospital_id == doc.hospital_id).all()
        if not items: return "Inventory is empty."
        
        df = pd.DataFrame([{"name": i.name, "qty": i.quantity, "threshold": i.min_threshold} for i in items])
        low_stock = df[df['qty'] <= df['threshold']]
        
        status = "CRITICAL" if len(low_stock) > 0 else "HEALTHY"
        msg = f"📦 **Inventory Status: {status}**\n- **Total Items:** {len(df)}\n- **Low Stock:** {len(low_stock)} items.\n"
        if not low_stock.empty: msg += "\n⚠️ **Alert:** " + ", ".join(low_stock['name'].tolist())
        if "list" in q: msg += "\n\n✅ **Full List:** " + ", ".join([f"{r['name']}({r['qty']})" for _, r in df.iterrows()])
        return msg

    def _analyze_schedule(self, q):
        appts = self.db.query(Appointment).filter(Appointment.doctor_id == self.doc_id).all()
        if not appts: return "Schedule empty."
        df = pd.DataFrame([{"status": a.status} for a in appts])
        return f"📅 **Schedule:** {len(df)} total slots tracked."

    def _analyze_patients(self, q):
        appts = self.db.query(Appointment).filter(Appointment.doctor_id == self.doc_id).all()
        if not appts: return "No patient history."
        unique = {a.patient_id for a in appts if a.patient_id}
        return f"👥 **Patients:** You have treated {len(unique)} unique patients."
