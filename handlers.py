import json, logging, requests, os, time, re
from datetime import datetime, timedelta
from random import choice
from typing import Dict, Any, List
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LETTRES = "abcdefghijklmnopqrstuvwxyz"
CHIFFRES = "0123456789"
MAJ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LETTRES_KOUAME = "Kouame" # Lettres pour le format de licence
LICENCE_YAML = "licences.yaml"
ADMIN_PW = "kouame2025"
ADMIN_IDS = [1190237801] 

class TelegramHandlers:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.transfo = {
            "10♦️": ("PIQUE", "♠️"), "10♠️": ("COEUR", "❤️"), "9♣️": ("COEUR", "❤️"),
            "9♦️": ("PIQUE", "♠️"), "8♣️": ("PIQUE", "♠️"), "8♠️": ("TREFLE", "♣️"),
            "7♠️": ("PIQUE", "♠️"), "7♣️": ("TREFLE", "♣️"), "6♦️": ("TREFLE", "♣️"),
            "6♣️": ("CARREAU", "♦️")
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
        self._ensure_yaml()
        self.offset = 0
        self.waiting_password = set()
        self.waiting_licence = set()
        # Stockage temporaire des IDs de message envoyés pour l'effacement
        self.user_message_log = {}

    # ---------- YAML (Méthodes de gestion de licences) ----------
    def _ensure_yaml(self):
        if not os.path.exists(LICENCE_YAML):
            data = {"licences": {"1h": [], "2h": [], "5h": [], "24h": [], "48h": []}}
            with open(LICENCE_YAML, "w", encoding="utf-8") as f:
                yaml.dump(data, f)

    def _load_yaml(self) -> Dict[str, List[str]]:
        with open(LICENCE_YAML, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)["licences"]

    def _save_yaml(self, data: Dict[str, List[str]]):
        with open(LICENCE_YAML, "w", encoding="utf-8") as f:
            yaml.dump({"licences": data}, f)

    def _generate_code(self) -> str:
        """Génère le nouveau format de licence (3 lettres, 3 chiffres, HH, 1 Maj, 1 lettre Kouame)."""
        
        # 3 Lettres aléatoires
        part1 = ''.join(choice(MAJ) for _ in range(3))
        # 3 Chiffres aléatoires
        part2 = ''.join(choice(CHIFFRES) for _ in range(3))
        # Heure actuelle (HH)
        part3 = datetime.now().strftime("%H")
        # 1 Majuscule aléatoire
        part4 = choice(MAJ)
        # 1 Lettre aléatoire de "Kouame"
        part5 = choice(LETTRES_KOUAME)
        
        return f"{part1}{part2}{part3}{part4}{part5}"

    def _add_licence(self, duration: str) -> str:
        data = self._load_yaml()
        # Utilise la nouvelle fonction de génération
        code = self._generate_code() 
        data[duration].append(code)
        self._save_yaml(data)
        return code
    
    # Le reste des fonctions YAML (_pop_licence, _licence_valid, _remove_used) ne changent pas.

    # ---------- LICENCE USER (Méthodes de gestion d'accès utilisateur) ----------
    # ... (les méthodes _get_user_licence, _save_user_licence, _licence_expired, _remaining_str restent les mêmes) ...
    def _get_user_licence(self, user_id: int) -> Dict[str, Any]:
        if not os.path.exists("user_licences.json"):
            return {}
        try:
            with open("user_licences.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(str(user_id), {})
        except Exception:
            return {}

    def _save_user_licence(self, user_id: int, code: str, hours: int):
        if not os.path.exists("user_licences.json"):
            with open("user_licences.json", "w", encoding="utf-8") as f:
                json.dump({}, f)
        with open("user_licences.json", "r+", encoding="utf-8") as f:
            data = json.load(f)
            data[str(user_id)] = {
                "code": code,
                "hours": hours,
                "used_at": datetime.utcnow().isoformat()
            }
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()

    def _licence_expired(self, lic: Dict[str, Any]) -> bool:
        if not lic:
            return True
        used_at = datetime.fromisoformat(lic["used_at"])
        hours = lic["hours"]
        expiry = used_at + timedelta(hours=hours)
        return datetime.utcnow() > expiry

    def _remaining_str(self, lic: Dict[str, Any]) -> str:
        if self._licence_expired(lic):
            return "⏰ Licence expirée"
        used_at = datetime.fromisoformat(lic["used_at"])
        hours = lic["hours"]
        expiry = used_at + timedelta(hours=hours)
        remaining = expiry - datetime.utcnow()
        h, rem = divmod(int(remaining.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        return f"⏳ Licence : {h:02d}h {m:02d}m {s:02d}s"

    # ---------- NOUVELLE FONCTION : SUPPRESSION DE MESSAGES ----------
    def _delete_message(self, chat_id: int, message_id: int):
        """Supprime un message spécifique."""
        payload = {"chat_id": chat_id, "message_id": message_id}
        try:
            requests.post(f"{self.base_url}/deleteMessage", json=payload, timeout=5)
        except Exception as e:
            logger.debug(f"Erreur lors de la suppression du message {message_id}: {e}")

    def _delete_user_messages(self, user_id: int, chat_id: int):
        """Supprime tous les messages enregistrés pour cet utilisateur."""
        if user_id in self.user_message_log:
            logger.info(f"Suppression des messages de l'utilisateur {user_id}")
            # Fait une copie des IDs avant de modifier le log
            for msg_id in list(self.user_message_log[user_id]):
                self._delete_message(chat_id, msg_id)
            # Efface le log de cet utilisateur
            del self.user_message_log[user_id]
            
        # Supprime aussi l'entrée de la licence de l'utilisateur
        self._remove_user_licence(user_id)
        
    def _remove_user_licence(self, user_id: int):
        """Supprime la licence du fichier JSON (Licence expirée)."""
        if not os.path.exists("user_licences.json"):
            return
        try:
            with open("user_licences.json", "r+", encoding="utf-8") as f:
                data = json.load(f)
                if str(user_id) in data:
                    del data[str(user_id)]
                    f.seek(0)
                    json.dump(data, f, indent=2)
                    f.truncate()
        except Exception:
            pass

    # ---------- API (Utilise self.base_url) ----------
    def send_message(self, chat_id: int, text: str, markup: str = None) -> bool:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if markup:
            payload["reply_markup"] = markup
        try:
            r = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            r.raise_for_status()
            
            # Enregistrement du message pour l'effacement futur
            response_json = r.json()
            if response_json.get("ok") and chat_id not in ADMIN_IDS:
                message_id = response_json["result"]["message_id"]
                user_id = chat_id # Dans ce cas, chat_id = user_id
                
                if user_id not in self.user_message_log:
                    self.user_message_log[user_id] = set()
                
                # Conserve seulement les 50 derniers messages pour éviter une mémoire illimitée
                if len(self.user_message_log[user_id]) >= 50:
                    oldest_id = min(self.user_message_log[user_id])
                    self.user_message_log[user_id].remove(oldest_id)
                
                self.user_message_log[user_id].add(message_id)
                
            return r.json().get("ok", False)
        except Exception as e:
            logger.error(f"send_message error : {e}")
            return False

    # ---------- ROUTE (handle_update) ----------
    def handle_update(self, update: Dict[str, Any]):
        msg = update.get("message", {})
        if "text" not in msg or "chat" not in msg:
             return

        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        
        # Enregistrement du message de l'utilisateur (pour l'effacement)
        if user_id not in ADMIN_IDS and "message_id" in msg:
            if user_id not in self.user_message_log:
                self.user_message_log[user_id] = set()
            self.user_message_log[user_id].add(msg["message_id"])

        # Admin : /lic 24h (Vérification de l'ID Admin)
        if text and text.startswith("/lic "):
            if user_id not in ADMIN_IDS:
                 self.send_message(chat_id, "❌ Accès administrateur refusé.")
                 return
            
            parts = text.split()
            if len(parts) == 2:
                duration = parts[1]
                if duration in ["1h", "2h", "5h", "24h", "48h"]:
                    # Utilise la fonction corrigée pour la génération
                    code = self._add_licence(duration) 
                    self.send_message(chat_id, f"🔑 Licence générée : `{code}`\nDurée : {duration}")
                else:
                    self.send_message(chat_id, "❌ Durée invalide.")
            return

        # Start
        if text == "/start":
            kb = [["1️⃣ J’ai une licence"], ["2️⃣ Administrateur"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
            self.send_message(chat_id, "🔰 Choisis :", markup)
            return

        # Admin mot de passe
        if text == "2️⃣ Administrateur":
            self.send_message(chat_id, "Entrez le mot de passe administrateur :")
            return
        if text == ADMIN_PW:
            self.send_admin_panel(chat_id)
            return

        # Choix 1 : saisie licence
        if text == "1️⃣ J’ai une licence":
            self.send_message(chat_id, "Veuillez entrer votre licence :")
            return

        # Vérification licence
        if self._licence_valid(text):
            lic_user = self._get_user_licence(user_id)
            if lic_user and not self._licence_expired(lic_user):
                self.send_message(chat_id, "✅ Licence déjà active.")
                self.send_keyboard(chat_id)
                return
            
            # Gestion du cas : Licence expirée
            if lic_user and self._licence_expired(lic_user):
                self._remove_user_licence(user_id) # Supprime l'entrée expirée
                self.send_message(chat_id, "🔒 Licence expirée. Veuillez acheter une nouvelle licence.")
                return

            # Activation de la nouvelle licence
            code = text
            duration = None
            data = self._load_yaml()
            for d, lst in data.items():
                if code in lst:
                    duration = d
                    break
            if not duration:
                self.send_message(chat_id, "❌ Licence introuvable.")
                return
            
            self._remove_used(code)
            self._save_user_licence(user_id, code, int(duration.replace("h", ""))) 
            
            self.send_message(chat_id, "✅ Licence acceptée !")
            remaining = self._remaining_str(self._get_user_licence(user_id))
            self.send_message(chat_id, remaining)
            self.send_keyboard(chat_id)
            return

        # VÉRIFICATION D'EXPIRATION ET BLOCAGE
        lic_user = self._get_user_licence(user_id)
        if not lic_user or self._licence_expired(lic_user):
            # 🔐 ÉTAPE 3: Si la licence vient d'expirer, efface les messages
            if lic_user and self._licence_expired(lic_user):
                self._delete_user_messages(user_id, chat_id)
            
            # Blocage total et demande de licence
            kb = [["1️⃣ J’ai une licence"], ["2️⃣ Administrateur"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
            self.send_message(chat_id, "🔒 Licence invalide ou expirée. Veuillez entrer une licence valide.", markup)
            return

        # Temps restant
        remaining = self._remaining_str(lic_user)
        self.send_message(chat_id, remaining)

        # Commandes normales
        if text == "REGLES DE JEU":
            self.send_message(chat_id, self.regles)
            return
        if text in self.transfo:
            nom, symb = self.transfo[text]
            self.send_message(chat_id, f"⚜️LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : **{nom} {symb}**\n\n📍ASSURANCE 100%📍")
            return
        
        self.send_message(chat_id, "Je n'ai pas compris ce message. Veuillez sélectionner une carte ou utiliser une commande.")
        
