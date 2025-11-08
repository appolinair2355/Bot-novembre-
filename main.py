from flask import Flask, request, jsonify
import os
import logging
from bot import TelegramBot
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
config = Config()
bot = TelegramBot(config.BOT_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Reçoit les updates Telegram"""
    try:
        update = request.get_json(force=True)
        logger.info(f"📩 Update reçue : {update.get('update_id')}")
        bot.handle_update(update)
        return 'OK', 200
    except Exception as e:
        logger.exception("❌ Erreur dans webhook")
        return 'OK', 200

@app.route('/health', methods=['GET'])
def health():
    """Health check pour Render"""
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def home():
    """Page d’accueil"""
    return jsonify({"message": "Telegram Bot is running", "status": "active"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Démarrage sur le port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
           
