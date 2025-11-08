import os

class Config:
    def __init__(self):
        self.BOT_TOKEN   = os.getenv("BOT_TOKEN")
        self.WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
        self.PORT        = int(os.getenv("PORT", "10000"))
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN manquant")
    @property
    def webhook_path(self) -> str:
        return f"{self.WEBHOOK_URL}/webhook" if self.WEBHOOK_URL else ""
      
