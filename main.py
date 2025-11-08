from flask import Flask, request
import os, logging
from bot import TelegramBot
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app   = Flask(__name__)
bot   = TelegramBot(Config().BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        bot.handle_update(request.get_json(force=True))
        return "OK", 200
    except Exception:
        logger.exception("Webhook error")
        return "Error", 500

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200

if __name__ == "__main__":
    bot.set_webhook(Config().WEBHOOK_URL)
    app.run(host="0.0.0.0", port=Config().PORT, debug=False)
    
