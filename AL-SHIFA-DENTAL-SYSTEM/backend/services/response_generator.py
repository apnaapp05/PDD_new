import random

class ResponseGenerator:
    
    @staticmethod
    def simple(text: str):
        return {"text": text}

    @staticmethod
    def success_schedule(appts, date_str):
        if not appts:
            msgs = [
                f"📅 Your schedule is completely clear for {date_str}. Enjoy the free time!",
                f"📅 No appointments found for {date_str}. A good day for admin work?"
            ]
            return {"text": random.choice(msgs)}
            
        count = len(appts)
        # Dynamic Header
        if count > 8: header = f"📅 **Busy Day Ahead!** ({count} Appts)"
        elif count > 4: header = f"📅 **Steady Schedule** ({count} Appts)"
        else: header = f"📅 **Light Schedule** ({count} Appts)"
        
        return {
            "text": header,
            "schedule_card": {
                "date": date_str,
                "items": [
                    {
                        "time": a.start_time.strftime("%H:%M"),
                        "patient": a.patient.user.full_name if a.patient and a.patient.user else "Blocked Slot",
                        "treatment": a.treatment_type or "General",
                        "status": a.status
                    } for a in appts
                ]
            }
        }

    @staticmethod
    def list_treatments(treatments):
        if not treatments:
            return {"text": "⚠️ Your treatment list is empty. Ask me to 'Add a new treatment'."}
            
        lines = []
        for t in treatments:
            lines.append(f"- **{t.name}**: Rs. {t.cost}")
            
        return {
            "text": "📋 **Standard Procedures & Pricing:**\n\n" + "\n".join(lines)
        }
