import os
import logging
from threading import Thread
from flask import Flask, jsonify # Importation de Flask et Thread
from bot import TelegramBot
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Fonction pour le Polling du Bot ---
def run_bot(token: str):
    """Initialise et lance la boucle de Polling du bot dans un thread."""
    try:
        bot = TelegramBot(token) 
        logger.info("🤖 Lancement de la boucle de Polling du bot.")
        bot.start_polling() 
    except Exception as e:
        logger.critical(f"❌ Erreur critique dans le thread du bot: {e}")

# --- Application Flask Minimale pour le Health Check ---
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Endpoint requis par de nombreux hébergeurs pour vérifier que le service est actif."""
    return jsonify({"status": "healthy", "bot_mode": "polling"}), 200

@app.route('/', methods=['GET'])
def home():
    """Page d'accueil."""
    return jsonify({"message": "Telegram Bot is running (Polling mode)", "status": "active"}), 200

# --- Lancement du Programme ---
if __name__ == '__main__':
    try:
        config = Config()
        
        # 1. Démarrer le bot dans un thread séparé
        # Le Polling est une boucle infinie et bloquerait le démarrage de Flask si elle était lancée directement.
        bot_thread = Thread(target=run_bot, args=(config.BOT_TOKEN,))
        # Le thread s'arrêtera si le processus principal (Flask) s'arrête
        bot_thread.daemon = True 
        bot_thread.start()
        logger.info("✅ Le thread du Bot a démarré.")

        # 2. Démarrer Flask sur le port requis par l'hébergeur
        # Récupère le PORT de l'environnement, 10000 par défaut (votre valeur)
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"🚀 Démarrage du serveur Flask minimal sur le port {port} (pour le Health Check).")
        
        # Le Flask est l'application principale qui écoute
        app.run(host="0.0.0.0", port=port, debug=False)

    except ValueError as ve:
        logger.critical(f"❌ Erreur de configuration : {ve}. Assurez-vous que BOT_TOKEN est défini.")
    except Exception as e:
        logger.critical(f"❌ Échec critique au démarrage: {e}")
    
