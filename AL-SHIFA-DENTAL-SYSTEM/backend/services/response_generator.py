import random

class ResponseGenerator:
    """
    Generates structured responses:
    {
        "text": "The message to display",
        "buttons": [
            { "label": "Button Name", "action": "/link/to/page", "type": "navigate" },
            { "label": "Chat Command", "action": "User Query", "type": "chat" }
        ]
    }
    """

    @staticmethod
    def success_finance(rev, pending):
        buttons = [{ "label": "📊 Full Report", "action": "/doctor/finance", "type": "navigate" }]
        
        if rev == 0:
            text = "It looks like a quiet period. No revenue recorded yet. Should we check your upcoming appointments?"
            buttons.append({ "label": "📅 Check Schedule", "action": "/doctor/schedule", "type": "navigate" })
        elif pending > (rev * 0.2): # High pending ratio
            text = f"You have generated **Rs. {rev}**, but please note that **Rs. {pending}** is still pending. You might want to follow up on invoices."
            buttons.insert(0, { "label": "⚠️ Pending Invoices", "action": "/doctor/finance", "type": "navigate" })
        else:
            text = f"Great performance! 🚀 You have collected **Rs. {rev}** so far, with only **Rs. {pending}** pending."
        
        return {"text": text, "buttons": buttons}

    @staticmethod
    def success_schedule(appts, date_str):
        if not appts:
            return {
                "text": f"Your schedule is completely clear for {date_str}. Enjoy your free time!",
                "buttons": [
                    { "label": "📅 Manage Schedule", "action": "/doctor/schedule", "type": "navigate" },
                    { "label": "Check Next Week", "action": "Show schedule for next week", "type": "chat" }
                ]
            }
        
        count = len(appts)
        text = f"You have **{count} appointments** for {date_str}:\n" + "\n".join([f"- {a.start_time.strftime('%H:%M')}: {a.treatment_type}" for a in appts])
        
        return {
            "text": text,
            "buttons": [
                { "label": "📅 Go to Calendar", "action": "/doctor/schedule", "type": "navigate" },
                { "label": "Start First Appt", "action": f"Start appointment for {appts[0].patient.user.full_name if appts[0].patient else 'Unknown'}", "type": "chat" }
            ]
        }

    @staticmethod
    def success_block(date, time):
        text = random.choice([
            f"Done. I've secured the slot on **{date}** at **{time}**.",
            f"Confirmed. Your schedule is blocked for {date} {time}.",
            f"✅ Blocked {date} at {time} successfully."
        ])
        return {
            "text": text,
            "buttons": [{ "label": "Undo / View", "action": "/doctor/schedule", "type": "navigate" }]
        }

    @staticmethod
    def error(msg):
        return {
            "text": f"⚠️ I couldn't do that. Reason: {msg}",
            "buttons": []
        }

    @staticmethod
    def simple(text):
        """Helper for simple text responses"""
        return {"text": text, "buttons": []}
