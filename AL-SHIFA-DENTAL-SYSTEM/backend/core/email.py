
import logging
from notifications.email import EmailAdapter

logger = logging.getLogger(__name__)

try:
    email_service = EmailAdapter()
except Exception as e:
    logger.warning(f"Email service failed to initialize: {e}")
    email_service = None
