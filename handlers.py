import json, logging, requests, os, time, re
from datetime import datetime, timedelta
from random import choice
from typing import Dict, Any, List, Tuple
import yaml

# Configuration de base
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constantes pour la génération de licence et les fichiers
LETTRES = "abcdefghijklmnopqrstuvwxyz"
CHIFFRES = "0123456789"
MAJ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LETTRES_KOUAME = "Kouame"
LICENCE_YAML = "licences.yaml"
TRANSFO_CONFIG = "transfo_config.json" # Fichier pour les correspondances des cartes

# Mots de passe et IDs administrateur
ADMIN_PW = "kouame2025"
UPDATE_PW = "arrow2025" 
ADMIN_IDS = [1190237801, 1309049556] 

# Constantes pour les états d'édition
STATE_EDIT_CARD = 1
STATE_EDIT_RESULT = 2
STATE_CONFIRM = 3


class TelegramHandlers:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        
        # Le dictionnaire self.transfo sera chargé depuis un fichier
        self.transfo = {} 
        self._ensure_transfo_config() # S'assure que le fichier existe et le charge (met à jour self.transfo et self.last_updated_str)
        
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
        self._ensure_yaml() # Initialise licences.yaml

        # États pour la gestion des interactions
        self.offset = 0
        self.waiting_password = set() # Pour le mot de passe Admin
        self.waiting_update_pw = set() # Pour le mot de passe Mise à jour
        self.editing_state = {} # {user_id: {'step': X, 'original_card': '10♦️', ...}}


    # ---------- CONFIGURATION DES CARTES (TRANSFO) ----------
    def _ensure_transfo_config(self):
        """S'assure que le fichier de configuration des cartes existe, sinon le crée avec les valeurs par défaut."""
        if not os.path.exists(TRANSFO_CONFIG):
            default_transfo = {
                "transfo": {
                    "10♦️": ["PIQUE", "♠️"], "10♠️": ["COEUR", "❤️"], "9♣️": ["COEUR", "❤️"],
                    "9♦️": ["PIQUE", "♠️"], "8♣️": ["PIQUE", "♠️"], "8♠️": ["TREFLE", "♣️"],
                    "7♠️": ["PIQUE", "♠️"], "7♣️": ["TREFLE", "♣️"], "6♦️": ["TREFLE", "♣️"],
                    "6♣️": ["CARREAU", "♦️"]
                },
                # Heure du Bénin (GMT+1)
                "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)") 
            }
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(default_transfo, f, indent=4)
                
        self._load_transfo_config()

    def _load_transfo_config(self):
        """Charge le dictionnaire des correspondances et la date/heure de mise à jour."""
        try:
            with open(TRANSFO_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convertit la liste [nom, symbole] en tuple (nom, symbole)
                self.transfo = {k: tuple(v) for k, v in data["transfo"].items()} 
                self.last_updated_str = data["last_updated"]
        except Exception as e:
            logger.error(f"Erreur lors du chargement de transfo_config.json: {e}")
            self.transfo = {}
            self.last_updated_str = "Inconnue"

    def _save_transfo_config(self):
        """Sauvegarde les correspondances mises à jour."""
        # Convertit les tuples en listes pour la sauvegarde JSON
        transfo_list = {k: list(v) for k, v in self.transfo.items()} 
        data = {
            "transfo": transfo_list,
            # Sauvegarde avec l'heure du Bénin (GMT+1)
            "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)")
        }
        try:
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.last_updated_str = data["last_updated"]
            logger.info(f"Configuration des cartes mise à jour et enregistrée par {self.last_updated_str}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de transfo_config.json: {e}")


    # ---------- GESTION DES LICENCES (YAML/JSON) ----------
    # (Les méthodes _ensure_yaml, _load_yaml, _save_yaml, _generate_code, _add_licence, etc., restent inchangées)
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
        """Génère le format de licence : 3 lettres, 3 chiffres, HH, 1 Maj, 1 lettre Kouame."""
        part1 = ''.join(choice(MAJ) for _ in range(3))
        part2 = ''.join(choice(CHIFFRES) for _ in range(3))
        part3 = datetime.now().strftime("%H")
        part4 = choice(MAJ)
        part5 = choice(LETTRES_KOUAME)
        return f"{part1}{part2}{part3}{part4}{part5}"

    def _add_licence(self, duration: str) -> str:
        data = self._load_yaml()
        code = self._generate_code() 
        data[duration].append(code)
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

    def _get_user_licence(self, user_id: int) -> Dict[str, Any]:
        if not os.path.exists("user_licences.json"):
            return {}
        try:
            with open("user_licences.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(str(user_id), {})
        except Exception:
            return {}

    def _remove_user_licence(self, user_id: int):
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
    
    # ---------- API ET CLAVIERS ----------

    def send_message(self, chat_id: int, text: str, markup: str = None) -> bool:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if markup:
            payload["reply_markup"] = markup
        try:
            r = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            r.raise_for_status()
            return r.json().get("ok", False)
        except Exception as e:
            logger.error(f"send_message error : {e}")
            return False

    def send_keyboard(self, chat_id: int) -> bool:
        """Envoie le clavier des 10 cartes avec la date de mise à jour."""
        # Utilise les clés actuelles de self.transfo (dynamique)
        all_cards = list(self.transfo.keys())
        # Assurez-vous qu'il y a au moins 10 cartes pour éviter un IndexError
        if len(all_cards) < 10:
             return self.send_message(chat_id, "❌ Erreur de configuration: 10 cartes de base sont requises.")
             
        kb = [
            all_cards[0:3], all_cards[3:6],
            all_cards[6:9], [all_cards[9], "REGLES DE JEU"]
        ]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        
        msg = (
            self.start_msg + 
            f"\n\n_Dernière mise à jour : {self.last_updated_str}_"
        )
        return self.send_message(chat_id, msg, markup)

    def send_admin_panel(self, chat_id: int):
        data = self._load_yaml()
        unused = {k: len(v) for k, v in data.items()}
        lines = "\n".join([f"**{d}** : {nb} disponible(s)" for d, nb in unused.items()]) 
        self.send_message(chat_id, f"📦 Licences disponibles :\n{lines}")
        kb = [["/lic 1h"], ["/lic 2h"], ["/lic 5h"], ["/lic 24h"], ["/lic 48h"]]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "Génération rapide :", markup)
        
    def send_update_panel(self, chat_id: int):
        """Envoie le clavier des 10 cartes à éditer."""
        all_cards = list(self.transfo.keys())
        if len(all_cards) < 10:
             return self.send_message(chat_id, "❌ Erreur de configuration: 10 cartes de base sont requises pour l'édition.")
             
        kb = [
            all_cards[0:3], all_cards[3:6],
            all_cards[6:9], [all_cards[9]] # Pas de bouton REGLES DE JEU dans ce clavier
        ]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "Choisissez la carte de départ à modifier (actuellement):", markup)

    # ---------- ROUTE (handle_update) ----------
    def handle_update(self, update: Dict[str, Any]):
        msg = update.get("message", {})
        if "text" not in msg or "chat" not in msg:
             return

        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]

        # --- GESTION DES ÉTATS D'ÉDITION ---
        if user_id in self.editing_state:
            state = self.editing_state[user_id]
            current_step = state['step']
            
            if current_step == STATE_EDIT_CARD:
                # Étape 1 : Saisie de la nouvelle carte de départ
                if len(text) > 10: 
                    self.send_message(chat_id, "Entrée trop longue. Veuillez entrer la carte de départ (ex: 8♣️).")
                    return
                state['new_card'] = text
                state['step'] = STATE_EDIT_RESULT
                self.send_message(chat_id, f"OK. Entrez le NOUVEAU résultat de prédiction (ex: PIQUE ♠️) :")
                return

            elif current_step == STATE_EDIT_RESULT:
                # Étape 2 : Saisie du nouveau résultat (ex: PIQUE ♠️)
                parts = text.split()
                if len(parts) < 2:
                    self.send_message(chat_id, "Format invalide. Le résultat doit contenir le NOM et le SYMBOLE (ex: PIQUE ♠️).")
                    return
                
                nom = parts[0].upper()
                symb = parts[1] # Le reste est le symbole
                
                state['new_result'] = [nom, symb]
                state['step'] = STATE_CONFIRM
                
                self.send_message(chat_id, 
                    f"Mise à jour en attente : \n"
                    f"Carte de départ: **{state['new_card']}**\n"
                    f"Résultat: **{nom} {symb}**\n\n"
                )
                kb = [["✅ ENREGISTRER"], ["❌ ANNULER"]]
                markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                self.send_message(chat_id, "Confirmez :", markup)
                return

            elif current_step == STATE_CONFIRM:
                # Étape 3 : Confirmation et Sauvegarde
                del self.editing_state[user_id] 
                
                if text == "✅ ENREGISTRER":
                    # Suppression de l'ancienne carte et ajout de la nouvelle
                    if state['original_card'] in self.transfo:
                        del self.transfo[state['original_card']] 
                    self.transfo[state['new_card']] = tuple(state['new_result'])
                    self._save_transfo_config()
                    
                    self.send_message(chat_id, "✅ Clavier mis à jour et enregistré ! Utilisez `/start` pour revenir au menu principal.")
                    return
                
                elif text == "❌ ANNULER":
                    self.send_message(chat_id, "❌ Modification annulée. Utilisez `/start` pour revenir au menu principal.")
                    return
            
            # Si un message est reçu alors que l'utilisateur est en édition, mais ne correspond pas aux options
            self.send_message(chat_id, "Veuillez terminer votre action en cours (édition).")
            return


        # --- ROUTAGE PRINCIPAL ---

        # Admin : /lic 24h (Vérification de l'ID Admin)
        if text and text.startswith("/lic "):
            if user_id not in ADMIN_IDS:
                 self.send_message(chat_id, "❌ Accès administrateur refusé.")
                 return
            
            parts = text.split()
            if len(parts) == 2:
                duration = parts[1]
                if duration in ["1h", "2h", "5h", "24h", "48h"]:
                    code = self._add_licence(duration) 
                    self.send_message(chat_id, f"🔑 Licence générée : `{code}`\nDurée : {duration}")
                else:
                    self.send_message(chat_id, "❌ Durée invalide.")
            return

        # Start (Nouveau bouton 3️⃣ Mise à jour)
        if text == "/start":
            kb = [["1️⃣ J’ai une licence"], ["2️⃣ Administrateur"], ["3️⃣ Mise à jour"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
            self.send_message(chat_id, "🔰 Choisis :", markup)
            return

        # Accès Mise à Jour (Mot de passe)
        if text == "3️⃣ Mise à jour":
            self.waiting_update_pw.add(user_id)
            self.send_message(chat_id, "Entrez le mot de passe de mise à jour :")
            return

        # Vérification du Mot de passe Mise à Jour (Sécurité ID)
        if user_id in self.waiting_update_pw:
            self.waiting_update_pw.remove(user_id)

            # Doit être un Admin ID pour accéder à l'édition (Sécurité)
            if user_id not in ADMIN_IDS:
                self.send_message(chat_id, "❌ Accès refusé. Seuls les administrateurs désignés peuvent effectuer des mises à jour.")
                return

            if text == UPDATE_PW:
                self.send_update_panel(chat_id) # Envoie le clavier des 10 boutons
                return
            else:
                self.send_message(chat_id, "❌ Mot de passe incorrect.")
                return

        # Sélection de la Carte à Éditer (Après l'accès Mise à Jour)
        if text in self.transfo.keys():
            # Si l'utilisateur clique sur un bouton de carte APRES avoir réussi l'authentification (ou s'il est admin)
            if user_id in ADMIN_IDS:
                self.editing_state[user_id] = {
                    'step': STATE_EDIT_CARD,
                    'original_card': text,
                    'new_card': None,
                    'new_result': None
                }
                self.send_message(chat_id, f"Édition de la carte '{text}' : Entrez la NOUVELLE carte de départ (ex: 8♣️) :")
                return

        # Admin mot de passe (gestion des licences)
        if text == "2️⃣ Administrateur":
            self.waiting_password.add(user_id)
            self.send_message(chat_id, "Entrez le mot de passe administrateur :")
            return
        if user_id in self.waiting_password and text == ADMIN_PW:
            self.waiting_password.remove(user_id)
            self.send_admin_panel(chat_id)
            return
        if user_id in self.waiting_password:
             self.waiting_password.remove(user_id)
             self.send_message(chat_id, "❌ Mot de passe administrateur incorrect.")
             return


        # Choix 1 : saisie licence
        if text == "1️⃣ J’ai une licence":
            self.send_message(chat_id, "Veuillez entrer votre licence :")
            return

        # Vérification et activation de licence (logique inchangée)
        if self._licence_valid(text):
            lic_user = self._get_user_licence(user_id)
            if lic_user and not self._licence_expired(lic_user):
                self.send_message(chat_id, "✅ Licence déjà active.")
                self.send_keyboard(chat_id)
                return
            
            if lic_user and self._licence_expired(lic_user):
                self._remove_user_licence(user_id) 
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
            # Si la licence vient d'expirer, on la supprime du fichier utilisateur
            if lic_user and self._licence_expired(lic_user):
                self._remove_user_licence(user_id) 
            
            # Blocage total et renvoi au menu de licence
            kb = [["1️⃣ J’ai une licence"], ["2️⃣ Administrateur"], ["3️⃣ Mise à jour"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
            self.send_message(chat_id, "🔒 Licence invalide ou expirée. Veuillez entrer une licence valide.", markup)
            return

        # Temps restant
        remaining = self._remaining_str(lic_user)
        self.send_message(chat_id, remaining)

        # Commandes normales (affichage de la prédiction)
        if text == "REGLES DE JEU":
            self.send_message(chat_id, self.regles)
            return
        if text in self.transfo:
            # Récupère le résultat mis à jour dynamiquement
            nom, symb = self.transfo[text] 
            self.send_message(chat_id, f"⚜️LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : **{nom} {symb}**\n\n📍ASSURANCE 100%📍")
            return
        
        self.send_message(chat_id, "Je n'ai pas compris ce message. Veuillez sélectionner une carte ou utiliser une commande.")
