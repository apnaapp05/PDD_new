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
    def success_schedule(appointments, date_str):
        if not appointments:
            return {
                "text": f"Your schedule is completely clear for {date_str}. Enjoy your free time!",
                "buttons": [
                    { "label": "📅 Manage Schedule", "action": "/doctor/schedule", "type": "navigate" },
                    { "label": "Check Next Week", "action": "Show schedule for next week", "type": "chat" }
                ]
            }
        
        # New Detailed Format
        lines = [f"📅 **Schedule for {date_str}**\nYou have {len(appointments)} appointments:\n"]
        first_patient_name = None

        for appt in appointments:
            time_str = appt.start_time.strftime("%H:%M")
            if appt.status == "blocked":
                reason = appt.notes if appt.notes else "Blocked"
                lines.append(f"- 🕓 **{time_str}**: 🚫 Blocked ({reason})")
            else:
                p_name = "Unknown"
                p_id = "?"
                if appt.patient:
                    p_id = appt.patient.id
                    if appt.patient.user:
                        p_name = appt.patient.user.full_name
                
                treatment = appt.treatment_type if appt.treatment_type else "Checkup"
                if not first_patient_name and p_name != "Unknown": first_patient_name = p_name
                
                lines.append(f"- 🕓 **{time_str}**: 👤 **{p_name}** (ID: {p_id}) — {treatment}")

        buttons = [{ "label": "📅 Go to Calendar", "action": "/doctor/schedule", "type": "navigate" }]
        if first_patient_name:
            buttons.insert(0, {"label": f"Start {first_patient_name}", "action": f"Start appointment for {first_patient_name}", "type": "chat"})

        return {
            "text": "\n".join(lines),
            "buttons": buttons
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
    def success_inventory_alert(items):
        if not items:
            return {"text": "✅ Inventory is healthy. No low stock items found.", "buttons": []}
        
        msg = "⚠️ **Low Stock Alert**:\n" + "\n".join([f"- **{i.name}**: {i.quantity} {i.unit} (Min: {i.min_threshold})" for i in items])
        return {
            "text": msg,
            "buttons": [{ "label": "📦 Restock Now", "action": "/doctor/inventory", "type": "navigate" }]
        }

    @staticmethod
    def error(msg):
        return {
            "text": f"⚠️ I couldn't do that. Reason: {msg}",
            "buttons": []
        }

    @staticmethod
    def simple(text):
        return {"text": text, "buttons": []}
