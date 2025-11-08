import requests, logging
from handlers import TelegramHandlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token     = token
        self.base_url  = f"https://api.telegram.org/bot{token}"
        self.handlers  = TelegramHandlers(token)

    def handle_update(self, update):
        self.handlers.handle_update(update)

    def set_webhook(self, url: str) -> bool:
        if not url:
            logger.warning("WEBHOOK_URL absent – webhook non défini")
            return False
        ok = requests.post(f"{self.base_url}/setWebhook",
                           json={"url": url, "allowed_updates": ["message"]},
                           timeout=15).json().get("ok", False)
        logger.info("Webhook défini" if ok else "Échec webhook")
        return ok
        
