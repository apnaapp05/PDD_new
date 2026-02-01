from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Invoice, Appointment, Patient, Treatment
import pandas as pd
from datetime import datetime, timedelta

class AnalyticsService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_financial_summary(self, period="today"):
        """Calculates revenue safely."""
        query = self.db.query(Invoice).join(Appointment).filter(
            Appointment.doctor_id == self.doc_id
        )
        
        now = datetime.now()
        if period == "today":
            query = query.filter(Invoice.created_at >= now.replace(hour=0, minute=0))
        elif period == "week":
            query = query.filter(Invoice.created_at >= now - timedelta(days=7))
            
        invoices = query.all()
        if not invoices: return {"revenue": 0, "pending": 0, "count": 0}

        df = pd.DataFrame([{"amount": i.amount, "status": i.status} for i in invoices])
        
        return {
            "revenue": df[df["status"] == "paid"]["amount"].sum(),
            "pending": df[df["status"] == "pending"]["amount"].sum(),
            "count": len(df)
        }

    def get_treatment_popularity(self):
        """Analyzes most performed treatments."""
        results = self.db.query(
            Appointment.treatment_type, func.count(Appointment.id)
        ).filter(
            Appointment.doctor_id == self.doc_id
        ).group_by(Appointment.treatment_type).all()
        
        return sorted(results, key=lambda x: x[1], reverse=True)
