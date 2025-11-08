import json, logging, requests, os, time, re
from datetime import datetime, timedelta
from random import choice
from typing import Dict, Any, List
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LETTRES = "abcdefghijklmnopqrstuvwxyz"
CHIFFRES = "0123456789"
MAJ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LICENCE_YAML = "licences.yaml"
ADMIN_PW = "kouame2025"

class TelegramHandlers:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
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

    def _add_licence(self, duration: str) -> str:
        data = self._load_yaml()
        code = f"{choice(LETTRES)}{''.join(choice(CHIFFRES) for _ in range(3))}{choice(MAJ)}"
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

    def _remove_used(self, code: str):
        data = self._load_yaml()
        for lst in data.values():
            if code in lst:
                lst.remove(code)
                break
        self._save_yaml(data)

    # ---------- LICENCE USER ----------
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

    # ---------- CLAVIERS ----------
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
            "🟠 Regarde la  première cartes du
        
