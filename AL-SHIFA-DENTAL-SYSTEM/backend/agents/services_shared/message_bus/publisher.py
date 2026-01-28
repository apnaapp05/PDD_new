# dental-ai-system/services_shared/message_bus/publisher.py
import json
from typing import Dict, Any

class MessageBusPublisher:
    def __init__(self, project_id: str = "your-gcp-project-id"):
        self.project_id = project_id

    def publish_structured_message(self, topic_name: str, data: Dict[str, Any]):
        """Publishes structured JSON data for asynchronous A2A communication."""
        payload_json = json.dumps(data, indent=2)
        print(f"\n[A2A PUBLISH] TOPIC: {topic_name}\n{payload_json}")
        return {"status": "queued", "topic": topic_name}

GLOBAL_PUBLISHER = MessageBusPublisher()