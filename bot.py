import requests, logging
import time
from handlers import TelegramHandlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.handlers = TelegramHandlers(token)
        self.last_update_id = 0

    # Méthodes pour le Polling
    
    def delete_webhook(self) -> bool:
        """Supprime tout webhook actif pour éviter les conflits en mode polling."""
        try:
            ok = requests.post(f"{self.base_url}/deleteWebhook", timeout=10).json().get("ok", False)
            logger.info("Ancien webhook supprimé (si existant).")
            return ok
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du webhook : {e}")
            return False

    def get_updates(self):
        """Récupère les nouvelles updates de Telegram (Long Polling)."""
        params = {
            'offset': self.last_update_id + 1, 
            'timeout': 30 # Long Polling : attend jusqu'à 30s s'il n'y a pas de messages
        }
        try:
            response = requests.get(f"{self.base_url}/getUpdates", params=params, timeout=40) 
            response.raise_for_status() 
            return response.json().get('result', [])
        except requests.exceptions.RequestException as e:
            # Cette erreur peut survenir si la connexion expire, ce n'est pas critique
            logger.debug(f"Erreur lors de la requête getUpdates : {e}")
            return []

    def start_polling(self):
        """Lance la boucle infinie de polling."""
        logger.info("🤖 Démarrage de la boucle de Polling...")
        self.delete_webhook() # Nettoyage initial

        while True:
            updates = self.get_updates()
            
            if updates:
                logger.info(f"Updates reçues : {len(updates)}")
                for update in updates:
                    update_id = update.get('update_id')
                    
                    # Passage de la mise à jour aux gestionnaires
                    self.handlers.handle_update(update) 
                    
                    # Mise à jour de l'ID pour ne pas re-traiter ce message
                    self.last_update_id = update_id

            # Délai court avant la prochaine requête (après le long polling timeout)
            time.sleep(1) 

    # La méthode handle_update n'est plus utilisée en Polling
    # def handle_update(self, update):
    #     self.handlers.handle_update(update)
    
