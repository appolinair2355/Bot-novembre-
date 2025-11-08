import json, logging, requests, os
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramHandlers:
    def __init__(self, token: str):
        self.token   = token
        self.base_url= f"https://api.telegram.org/bot{token}"
        # transformations
        self.transfo = {
            "♦": "♠", "♠": "❤", "❤": "♣", "♣": "♦",
            "8": "♠", "10": "❤", "U": "♣", "7": "♠", "9": "❤", "6": "♦"
        }
        self.regles  = (
            "1️⃣ LES HEURES DE JEUX FAVORABLE : 01h à 04h  / 14h à 17h / 20h à 22h\n\n"
            "2️⃣ ÉVITEZ DE PARIÉ LE WEEKEND : Le Bookmaker Change régulièrement les algorithmes parce qu'il y a beaucoup de joueurs  le weekend\n\n"
            "3️⃣ SUIVRE LE TIMING DES 10 MINUTES : Après avoir placé un paris et gagnez un jeu il est essentiel de sortir du Bookmaker et revenir 10 minutes après pour un autre paris\n\n"
            "4️⃣ NE PAS FAIRE PLUS DE 20 PARIS GAGNANT PAR JOUR : Si vous violé cette règle votre compte sera  Bloqué par le Bookmaker\n\n"
            "5️⃣ ÉVITEZ D'ENREGISTRER UN COUPON : Quand vous enregistrez un coupon pour le partager , Vous augmentez vos chances de perdre\n\n\n"
            "🍾BON GAINS 🍾"
        )

    # ---------- API ----------
    def send_message(self, chat_id: int, text: str, markup: str = None) -> bool:
        payload = {"chat_id": chat_id, "text": text}
        if markup:
            payload["reply_markup"] = markup
        try:
            ok = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10).json().get("ok", False)
            return ok
        except Exception as e:
            logger.error(f"send_message error : {e}")
            return False

    # ---------- clavier exact image ----------
    def send_keyboard(self, chat_id: int) -> bool:
        kb = [
            ["8", "10", "REGLES DE JEU", "C"],
            ["U", "7", "9", "6"],
            ["♦", "♠", "❤", "♣"],
            ["6", "7", "8", "9"]
        ]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        return self.send_message(chat_id, "Choisis :", markup)

    # ---------- route ----------
    def handle_update(self, update: Dict[str, Any]) -> None:
        msg = update.get("message", {})
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        if text == "/start":
            self.send_keyboard(chat_id)
            return
        if text == "REGLES DE JEU":
            self.send_message(chat_id, self.regles)
            return
        if text in self.transfo:
            self.send_message(chat_id, f"LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : {self.transfo[text]}")
      
