import json, logging, requests, os
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramHandlers:
    def __init__(self, token: str):
        self.token   = token
        self.base_url= f"https://api.telegram.org/bot{token}"
        # 10 cartes → nom français + symbole
        self.transfo = {
            "10♦️": ("PIQUE", "♠️"),
            "10♠️": ("COEUR", "❤️"),
            "9♣️":  ("COEUR", "❤️"),
            "9♦️":  ("PIQUE", "♠️"),
            "8♣️":  ("PIQUE", "♠️"),
            "8♠️":  ("TREFLE", "♣️"),
            "7♠️":  ("PIQUE", "♠️"),
            "7♣️":  ("TREFLE", "♣️"),
            "6♦️":  ("TREFLE", "♣️"),
            "6♣️":  ("CARREAU", "♦️")
        }
        self.start_msg = (
            "🔰 SUIVRE CES CONSIGNES POUR CONNAÎTRE LA CARTE DANS LE JEU SUIVANT👇\n\n"
            "🟠 Regarde la  première cartes du joueur \n"
            "🟠 Tape la carte  dans le BOT\n"
            "🟠 Parie sur la prédiction  sur le Joueur dans le Jeu Suivant \n\n\n"
            "Rattrape 1 JEU"
        )
        self.regles = (
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

    # ---------- clavier 10 boutons ----------
    def send_keyboard(self, chat_id: int) -> bool:
        kb = [
            ["10♦️", "10♠️", "9♣️"],
            ["9♦️", "8♣️", "8♠️"],
            ["7♠️", "7♣️", "6♦️"],
            ["6♣️", "REGLES DE JEU"]
        ]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        return self.send_message(chat_id, "Choisis la carte observée :", markup)

    # ---------- route ----------
    def handle_update(self, update: Dict[str, Any]) -> None:
        msg = update.get("message", {})
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        if text == "/start":
            self.send_message(chat_id, self.start_msg)
            self.send_keyboard(chat_id)
            return
        if text == "REGLES DE JEU":
            self.send_message(chat_id, self.regles)
            return
        if text in self.transfo:
            nom, symb = self.transfo[text]
            self.send_message(chat_id, f"⚜️LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : {nom} {symb}\n\n📍ASSURANCE 100%📍")
                                                                                                    
