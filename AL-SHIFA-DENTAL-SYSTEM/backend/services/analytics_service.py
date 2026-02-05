from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import Invoice, Appointment, Patient, User
import pandas as pd
from datetime import datetime, timedelta

class AnalyticsService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_financial_summary(self, period="all"):
        """
        Returns:
        1. Stats (Revenue, Pending)
        2. Recent Invoices List (for the table)
        """
        # Base Query
        query = self.db.query(Invoice).join(Appointment).filter(
            Appointment.doctor_id == self.doc_id
        )
        
        # Period Filter
        now = datetime.now()
        if period == "today":
            query = query.filter(Invoice.created_at >= now.replace(hour=0, minute=0))
        elif period == "week":
            query = query.filter(Invoice.created_at >= now - timedelta(days=7))
            
        invoices = query.order_by(desc(Invoice.created_at)).all()
        
        # 1. Calculate Stats
        total_revenue = 0
        pending = 0
        if invoices:
            df = pd.DataFrame([{"amount": i.amount, "status": i.status} for i in invoices])
            total_revenue = df[df["status"] == "paid"]["amount"].sum()
            pending = df[df["status"] == "pending"]["amount"].sum()

        # 2. Format List for Table
        invoice_list = []
        for inv in invoices:
            # Safe Patient Name Lookup
            patient_name = "Unknown"
            if inv.patient and inv.patient.user:
                patient_name = inv.patient.user.full_name
            elif inv.appointment and inv.appointment.patient and inv.appointment.patient.user:
                patient_name = inv.appointment.patient.user.full_name

            invoice_list.append({
                "id": inv.id,
                "patient_name": patient_name,
                "procedure": inv.appointment.treatment_type if inv.appointment else "Consultation",
                "amount": inv.amount,
                "status": inv.status,
                "date": inv.created_at.strftime("%Y-%m-%d"),
                "time": inv.created_at.strftime("%H:%M")
            })

        return {
            "revenue": total_revenue,
            "pending": pending,
            "count": len(invoices),
            "invoices": invoice_list
        }
    
    def get_clinical_stats(self, week_offset: int = 0):
        """
        Get clinical case breakdown for a week.
        """
        from datetime import date, timedelta
        
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        
        target_monday = start_of_week + timedelta(weeks=week_offset)
        target_sunday = target_monday + timedelta(days=6)
        
        # Get completed appointments
        appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.status == 'completed',
            Appointment.start_time >= datetime.combine(target_monday, datetime.min.time()),
            Appointment.end_time <= datetime.combine(target_sunday, datetime.max.time())
        ).all()
        
        breakdown = {}
        for a in appts:
            if not a.treatment_type: continue
            breakdown[a.treatment_type] = breakdown.get(a.treatment_type, 0) + 1
            
        return breakdown

    def get_weekly_revenue_comparison(self):
        """
        Compare this week's revenue with last week's.
        """
        from datetime import date, timedelta
        
        today = date.today()
        start_of_current = today - timedelta(days=today.weekday())
        start_of_last = start_of_current - timedelta(weeks=1)
        
        def get_revenue(start_date):
            end_date = start_date + timedelta(days=7)
            invoices = self.db.query(Invoice).filter(
                Invoice.created_at >= datetime.combine(start_date, datetime.min.time()),
                Invoice.created_at < datetime.combine(end_date, datetime.min.time()),
                Invoice.status == 'paid'
            ).all()
            return sum([i.amount for i in invoices])
            
        current = get_revenue(start_of_current)
        last = get_revenue(start_of_last)
        
        growth = 0
        if last > 0:
            growth = ((current - last) / last) * 100
        elif current > 0:
            growth = 100 # Default if 0 to something
            
        return {
            "current_week_revenue": current,
            "last_week_revenue": last,
            "growth_percentage": f"{growth:.1f}%",
            "message": "Revenue is up!" if growth > 0 else "Revenue is down." if growth < 0 else "Stable."
        }

    def get_treatment_popularity(self):
        results = self.db.query(
            Appointment.treatment_type, func.count(Appointment.id)
        ).filter(
            Appointment.doctor_id == self.doc_id
        ).group_by(Appointment.treatment_type).all()
        return sorted(results, key=lambda x: x[1], reverse=True)

    def get_trend_analysis(self, months: int = 6):
        """
        Returns monthly revenue for the last X months.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30*months)
        
        invoices = self.db.query(Invoice).join(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Invoice.status == 'paid',
            Invoice.created_at >= start_date 
        ).all()
        
        if not invoices: return "No revenue data found for trend analysis."
        
        # Group by month
        data = [{"date": i.created_at, "amount": i.amount} for i in invoices]
        df = pd.DataFrame(data)
        
        df['month'] = df['date'].dt.strftime('%Y-%m')
        grouped = df.groupby('month')['amount'].sum().reset_index()
        return grouped.to_dict('records')

    def get_treatment_profitability(self):
        """
        Calculates profitability per treatment type.
        Profit = (Total Revenue from Treatment) - (Cost of Goods Sold)
        """
        from models import Treatment, InventoryItem
        
        treatments = self.db.query(Treatment).filter(Treatment.doctor_id == self.doc_id).all()
        profit_data = []
        
        for t in treatments:
            # Calculate Unit COGS
            cogs = 0
            for link in t.required_items:
                 item = self.db.query(InventoryItem).filter(InventoryItem.id == link.item_id).first()
                 if item: 
                     cogs += (item.buying_cost or 0) * link.quantity_required
            
            # Count Completed Procedures
            count = self.db.query(Appointment).filter(
                Appointment.doctor_id == self.doc_id,
                Appointment.treatment_type == t.name,
                Appointment.status == 'completed'
            ).count()
            
            if count == 0: continue

            total_revenue = count * t.cost
            total_cost = count * cogs
            profit = total_revenue - total_cost
            margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
            
            profit_data.append({
                "treatment": t.name,
                "count": count,
                "revenue": total_revenue,
                "cost": total_cost,
                "profit": profit,
                "margin": f"{margin:.1f}%"
            })
            
        return sorted(profit_data, key=lambda x: x['profit'], reverse=True)
