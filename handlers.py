import json, logging, requests, os, time, re
from datetime import datetime, timedelta
from random import choice
from typing import Dict, Any, List
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LETTRES_FR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHIFFRES = "0123456789"
NOM_REF = "KOUAME"
LICENCE_YAML = "licences.yaml"
USER_LICENCES = "user_licences.json"
ADMIN_PW = "kouame2025"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

class TelegramHandlers:
    def __init__(self):
        self.transfo = {
            "10♦️": ("PIQUE", "♠️"),
            "10♠️": ("COEUR", "❤️"),
            "9♣️": ("COEUR", "❤️"),
            "9♦️": ("PIQUE", "♠️"),
            "8♣️": ("PIQUE", "♠️"),
            "8♠️": ("TREFLE", "♣️"),
            "7♠️": ("PIQUE", "♠️"),
            "7♣️": ("TREFLE", "♣️"),
            "6♦️": ("TREFLE", "♣️"),
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

    # ---------- YAML ----------
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
        lettres = ''.join(choice(LETTRES_FR) for _ in range(3))
        chiffres = ''.join(choice(CHIFFRES) for _ in range(3))
        heure = datetime.utcnow().strftime("%H")
        maj = choice(LETTRES_FR)
        ref_lettre = choice(NOM_REF)
        return f"{lettres}{chiffres}{heure}{maj}{ref_lettre}"

    def _add_licence(self, duration: str) -> str:
        data = self._load_yaml()
        code = self._generate_code()
        data[duration].append(code)
        self._save_yaml(data)
        return code

    def _pop_licence(self, duration: str) -> str:
        data = self._load_yaml()
        if not data[duration]:
            return self._add_licence(duration)
        code = data[duration].pop(0)
        self._save_yaml(data)
        return code

    def _licence_valid(self, code: str) -> bool:
        data = self._load_yaml()
        for lst in data.values():
            if code in lst:
                return True
        return False

    def _move_to_expired(self, code: str):
        # Ajoute dans un fichier expired.yaml
        expired_file = "expired_licences.yaml"
        if not os.path.exists(expired_file):
            with open(expired_file, "w", encoding="utf-8") as f:
                yaml.dump({"expired": []}, f)
        with open(expired_file, "r+", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            data["expired"].append(code)
            f.seek(0)
            yaml.dump(data, f)
            f.truncate()

    # ---------- LICENCE USER ----------
    def _get_user_licence(self, user_id: int) -> Dict[str, Any]:
        if not os.path.exists(USER_LICENCES):
            return {}
        try:
            with open(USER_LICENCES, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(str(user_id), {})
        except Exception:
            return {}

    def _save_user_licence(self, user_id: int, code: str, hours: int):
        if not os.path.exists(USER_LICENCES):
            with open(USER_LICENCES, "w", encoding="utf-8") as f:
                json.dump({}, f)
        with open(USER_LICENCES, "r+", encoding="utf-8") as f:
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

    def _delete_user_messages(self, chat_id: int):
        # Supprime les 50 derniers messages de l’utilisateur
        try:
            url = f"{BASE_URL}/getUpdates"
            resp = requests.get(url, timeout=10).json()
            if not resp.get("ok"):
                return
            updates = resp.get("result", [])
            for upd in updates[-50:]:
                if upd.get("message", {}).get("from", {}).get("id") == chat_id:
                    msg_id = upd["message"]["message_id"]
                    requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
        except Exception:
            pass

    # ---------- API ----------
    def send_message(self, chat_id: int, text: str, markup: str = None) -> bool:
        payload = {"chat_id": chat_id, "text": text}
        if markup:
            payload["reply_markup"] = markup
        try:
            ok = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10).json().get("ok", False)
            return ok
        except Exception as e:
            logger.error(f"send_message error : {e}")
            return False

    def send_keyboard(self, chat_id: int) -> bool:
        kb = [
            ["10♦️", "10♠️", "9♣️"],
            ["9♦️", "8♣️", "8♠️"],
            ["7♠️", "7♣️", "6♦️"],
            ["6♣️", "REGLES DE JEU"]
        ]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        msg = (
            "🔰 SUIVRE CES CONSIGNES POUR CONNAÎTRE LA CARTE DANS LE JEU SUIVANT👇\n\n"
            "🟠 Regarde la  première cartes du joueur \n"
            "🟠 Tape la carte  dans le BOT\n"
            "🟠 Parie sur la prédiction  sur le Joueur dans le Jeu Suivant \n\n\n"
            "Rattrape 1 JEU"
        )
        return self.send_message(chat_id, msg, markup)

    def send_admin_panel(self, chat_id: int):
        data = self._load_yaml()
        unused = {k: len(v) for k, v in data.items()}
        lines = "\n".join([f"{d} : {nb} disponible(s)" for d, nb in unused.items()])
        self.send_message(chat_id, f"📦 Licences disponibles :\n{lines}")
        kb = [["/lic 1h"], ["/lic 2h"], ["/lic 5h"], ["/lic 24h"], ["/lic 48h"]]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "Génération rapide :", markup)

    def _cmd_lic(self, chat_id: int, text: str):
        parts = text.split()
        if len(parts) == 2 and parts[1] in ["1h", "2h", "5h", "24h", "48h"]:
            code = self._add_licence(parts[1])
            self.send_message(chat_id, f"🔑 Licence générée : `{code}`\nDurée : {parts[1]}")
        else:
            self.send_message(chat_id, "❌ Syntaxe : /lic 1h|2h|5h|24h|48h")

    # ---------- POLLING ----------
    def get_updates(self, offset: int) -> List[Dict[str, Any]]:
        url = f"{BASE_URL}/getUpdates"
        payload = {"offset": offset, "timeout": 30}
        try:
            resp = requests.post(url, json=payload, timeout=35).json()
            return resp.get("result", [])
        except Exception as e:
            logger.error(f"getUpdates error : {e}")
            return []

    def process_update(self, update: Dict[str, Any]):
        msg = update.get("message", {})
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]

        # ADMIN : mot de passe ou /lic
        if text == ADMIN_PW:
            self.send_admin_panel(chat_id)
            return
        if text and text.startswith("/lic "):
            self._cmd_lic(chat_id, text)
            return

        # START → choix 1 ou 2
        if text == "/start":
            kb = [["1️⃣ J’ai une licence"], ["2️⃣ Administrateur"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
            self.send_message(chat_id, "🔰 Choisis :", markup)
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
            if lic_user and self._licence_expired(lic_user):
                self.send_message(chat_id, "🔒 Licence expirée. Achetez une nouvelle.")
                # Efface messages + licence
                self._delete_user_messages(chat_id)
                self._move_to_expired(lic_user["code"])
                # Supprime de user_licences.json
                with open(USER_LICENCES, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data.pop(str(user_id), None)
                    f.seek(0)
                    json.dump(data, f)
                    f.truncate()
                return
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
            # Déplace vers user + retire de yaml
            self._remove_used(code)
            self._save_user_licence(user_id, code, int(duration.replace("h", "")))
            self.send_message(chat_id, "✅ Licence acceptée !")
            remaining = self._remaining_str(self._get_user_licence(user_id))
            self.send_message(chat_id, remaining)
            self.send_keyboard(chat_id)
            return

        # Vérification expiration à chaque message
        lic_user = self._get_user_licence(user_id)
        if not lic_user or self._licence_expired(lic_user):
            kb = [["1️⃣ J’ai une licence"], ["2️⃣ Administrateur"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
            self.send_message(chat_id, "🔒 Licence expirée. Achetez une nouvelle.", markup)
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
            self.send_message(chat_id, f"⚜️LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : {nom} {symb}\n\n📍ASSURANCE 100%📍")

    # ---------- RUN ----------
    def run(self):
        logger.info("🚀 Démarrage du bot en mode polling…")
        self.offset = 0
        while True:
            updates = self.get_updates(self.offset)
            for upd in updates:
                self.process_update(upd)
                self.offset = upd["update_id"] + 1
            time.sleep(2)
            
