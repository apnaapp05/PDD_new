from typing import List, Any

class ResponseGenerator:
    @staticmethod
    def simple(text: str):
        return {"text": text, "buttons": []}

    @staticmethod
    def error(text: str):
        return {"text": f"⚠️ {text}", "buttons": []}

    @staticmethod
    def success_schedule(appointments, date_str):
        if not appointments:
            return {
                "text": f"📅 **Schedule for {date_str}**\n\nNo appointments found.",
                "buttons": [{"label": "Block Time", "action": "Block time", "type": "chat"}]
            }
        
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
                treatment = appt.treatment_type if appt.treatment_type else "General Checkup"
                if not first_patient_name and p_name != "Unknown": first_patient_name = p_name
                lines.append(f"- 🕓 **{time_str}**: 👤 **{p_name}** (ID: {p_id}) — {treatment}")

        buttons = [{"label": "📅 Go to Calendar", "action": "/doctor/schedule", "type": "navigate"}]
        if first_patient_name:
            buttons.insert(0, {"label": f"Start {first_patient_name}", "action": f"Start appointment for {first_patient_name}", "type": "chat"})

        return {"text": "\n".join(lines), "buttons": buttons}

    @staticmethod
    def success_block(date, time):
        return {"text": f"Done. I've secured the slot on {date} at {time}.", "buttons": []}

    @staticmethod
    def success_finance(revenue, pending):
        return {
            "text": f"💰 **Financial Update**\n- Revenue: Rs. {revenue}\n- Pending: Rs. {pending}",
            "buttons": [{"label": "View Invoices", "action": "/doctor/finance", "type": "navigate"}]
        }

    @staticmethod
    def success_inventory_alert(items):
        if not items:
            return {
                "text": "✅ **Inventory Status**\n\nAll items are well-stocked.",
                "buttons": [{"label": "Add Item", "action": "Add stock", "type": "chat"}]
            }
        
        lines = [f"⚠️ **Low Stock Alert**\nYou have {len(items)} items below threshold:\n"]
        for i in items:
            lines.append(f"- 📦 **{i.name}**: {i.quantity} {i.unit} (Alert at: {i.min_threshold})")
        
        return {
            "text": "\n".join(lines),
            "buttons": [
                {"label": "Restock List", "action": "/doctor/inventory", "type": "navigate"},
                {"label": "Ignore", "action": "dashboard", "type": "navigate"}
            ]
        }
