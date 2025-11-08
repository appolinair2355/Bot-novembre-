from flask import Flask, request
import os, logging
from bot import TelegramBot
from config import Config

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Initialisation de Flask et du bot ---
app = Flask(__name__)
config = Config()
bot = TelegramBot(config.BOT_TOKEN)

# --- Route webhook Telegram ---
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True)
        bot.handle_update(update)
        return "OK", 200
    except Exception:
        logger.exception("Webhook error")
        return "Error", 500

# --- Route de santé (pour Render) ---
@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200

# --- Démarrage principal ---
if __name__ == "__main__":
    webhook_url = config.webhook_path  # utilise la propriété qui ajoute /webhook automatiquement

    if webhook_url:
        bot.set_webhook(webhook_url)
        logger.info(f"Webhook défini sur {webhook_url}")
    else:
        logger.warning("WEBHOOK_URL absent – webhook non défini")

    app.run(host="0.0.0.0", port=config.PORT, debug=False)
