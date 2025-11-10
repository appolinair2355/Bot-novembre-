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
TRANSFO_CONFIG = "transfo_config.json" 

# Mots de passe et IDs administrateur
ADMIN_PW = "kouame2025"
UPDATE_PW = "arrow2025" 
ADMIN_IDS = [1190237801, 1309049556, 5622847726] 

# Constantes pour les états d'édition
STATE_EDIT_CARD = 1 # Utilisé pour la saisie du code de licence
STATE_NEW_CARD = 2
STATE_EDIT_RESULT = 3
STATE_CONFIRM = 4
STATE_UPDATE_PANEL = 5 

# Valeurs de configuration par défaut pour la restauration
DEFAULT_TRANSFO_DATA = {
    "10♦️": ["PIQUE", "♠️"], "10♠️": ["COEUR", "❤️"], "9♣️": ["COEUR", "❤️"],
    "9♦️": ["PIQUE", "♠️"], "8♣️": ["PIQUE", "♠️"], "8♠️": ["TREFLE", "♣️"],
    "7♠️": ["PIQUE", "♠️"], "7♣️": ["TREFLE", "♣️"], "6♦️": ["TREFLE", "♣️"],
    "6♣️": ["CARREAU", "♦️"]
}


class TelegramHandlers:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        
        self.transfo = {} 
        self.last_updated_str = "Inconnue"
        self._ensure_transfo_config() 
        
        self.start_msg = (
            "🔰 SUIVRE CES CONSIGNES POUR CONNAÎTRE LA CARTE DANS LE JEU SUIVANT👇\n\n"
            "🟠 Regarde la première cartes du joueur \n"
            "🟠 Tape la carte dans le BOT\n"
            "🟠 Parie sur la prédiction sur le Joueur dans le Jeu Suivant \n\n\n"
            "Rattrape 1 JEU"
        )
        self.regles = (
            "1️⃣ LES HEURES DE JEUX FAVORABLE : 01h à 04h / 14h à 17h / 20h à 22h\n\n"
            "2️⃣ ÉVITEZ DE PARIÉ LE WEEKEND : Le Bookmaker Change régulièrement les algorithmes parce qu'il y a beaucoup de joueurs le weekend\n\n"
            "3️⃣ SUIVRE LE TIMING DES 10 MINUTES : Après avoir placé un paris et gagnez un jeu il est essentiel de sortir du Bookmaker et revenir 10 minutes après pour un autre paris\n\n"
            "4️⃣ NE PAS FAIRE PLUS DE 20 PARIS GAGNANT PAR JOUR : Si vous violé cette règle votre compte sera Bloqué par le Bookmaker\n\n"
            "5️⃣ ÉVITEZ D'ENREGISTRER UN COUPON : Quand vous enregistrez un coupon pour le partager , Vous augmentez vos chances de perdre\n\n\n"
            "🍾BON GAINS 🍾"
        )
        self._ensure_yaml() 

        self.offset = 0
        self.waiting_password = set() 
        self.waiting_update_pw = set() 
        self.editing_state = {} 


    # --- CONFIGURATION DES CARTES (TRANSFO) ---
    
    def _ensure_transfo_config(self):
        if not os.path.exists(TRANSFO_CONFIG):
            default_transfo = {
                "transfo": {k: list(v) for k, v in DEFAULT_TRANSFO_DATA.items()},
                "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)") 
            }
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(default_transfo, f, indent=4)
                
        self._load_transfo_config()

    def _load_transfo_config(self):
        try:
            with open(TRANSFO_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data.get("transfo") or len(data["transfo"]) < 10:
                    raise ValueError("Configuration dans le fichier incomplète ou invalide.")
                
                self.transfo = {k: tuple(v) for k, v in data["transfo"].items()} 
                self.last_updated_str = data["last_updated"]
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            self.transfo = {k: tuple(v) for k, v in DEFAULT_TRANSFO_DATA.items()}
            self.last_updated_str = "Défaut (GMT+1)"

    def _save_transfo_config(self):
        transfo_list = {k: list(v) for k, v in self.transfo.items()} 
        data = {
            "transfo": transfo_list,
            "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)")
        }
        try:
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.last_updated_str = data["last_updated"]
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de transfo_config.json: {e}")

    def _restore_default(self):
        data = {
            "transfo": {k: list(v) for k, v in DEFAULT_TRANSFO_DATA.items()},
            "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)")
        }
        try:
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self._load_transfo_config() 
            return True
        except Exception as e:
            return False

    # --- GESTION DES LICENCES (YAML/JSON) ---
    
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
        for duration, lst in data.items():
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
    
    # --- API ET CLAVIERS ---

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
        all_cards = list(self.transfo.keys())
        if len(all_cards) < 10:
             all_cards = list(DEFAULT_TRANSFO_DATA.keys()) 
             if len(all_cards) < 10:
                 return self.send_message(chat_id, "❌ Erreur de configuration: 10 cartes de base sont requises.")
             
        kb = [all_cards[0:4], all_cards[4:7], all_cards[7:10], ["REGLES DE JEU"]]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        msg = (self.start_msg + f"\n\n_Dernière mise à jour : {self.last_updated_str}_")
        return self.send_message(chat_id, msg, markup)

    def send_admin_panel(self, chat_id: int):
        data = self._load_yaml()
        unused = {k: len(v) for k, v in data.items()}
        lines = "\n".join([f"**{d}** : {nb} disponible(s)" for d, nb in unused.items()]) 
        self.send_message(chat_id, f"📦 Licences disponibles :\n{lines}")
        kb = [["/lic 1h", "/lic 2h", "/lic 5h"], ["/lic 24h", "/lic 48h"], ["/update_panel", "⬅️ Retour au Menu"]]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "Génération rapide :", markup)
        
    def send_update_panel(self, chat_id: int):
        all_cards = list(self.transfo.keys())
        if len(all_cards) < 10:
             return self.send_message(chat_id, "❌ Erreur de configuration: 10 cartes de base sont requises pour l'édition.")
             
        kb = [all_cards[0:3], all_cards[3:6], all_cards[6:9], [all_cards[9]], ["🔄 RESTAURER", "❌ ANNULER"]]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "Choisissez la carte de départ à modifier (actuellement):", markup)
        
    # --- GESTION DE LA BOUCLE PRINCIPALE (POLLING) ---

    def get_updates(self) -> List[Dict[str, Any]]:
        """Récupère les nouvelles mises à jour (messages) depuis l'API Telegram."""
        try:
            params = {"offset": self.offset + 1, "timeout": 30}
            r = requests.get(f"{self.base_url}/getUpdates", params=params, timeout=35)
            r.raise_for_status()
            
            updates = r.json().get("result", [])
            if updates:
                self.offset = updates[-1]["update_id"]
            
            return updates
        except requests.exceptions.ReadTimeout:
            return []
        except Exception as e:
            logger.error(f"Erreur get_updates : {e}")
            time.sleep(5)
            return []

    def run_bot(self):
        """Lance la boucle principale pour écouter les messages."""
        logger.info("Démarrage du bot. Écoute des mises à jour...")
        self.offset = 0 
        while True:
            updates = self.get_updates()
            for update in updates:
                self.handle_update(update)
    # --- ROUTAGE (HANDLE_UPDATE) ---
    
    def handle_update(self, update: Dict[str, Any]):
        msg = update.get("message", {})
        if "text" not in msg or "chat" not in msg:
             return

        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]

        # GESTION DES ÉTATS D'ÉDITION MULTI-PARTIES (PRIORITÉ MAX)
        if user_id in self.editing_state:
            state = self.editing_state[user_id]
            current_step = state['step']
            
            # Gère l'annulation / retour au menu pour les workflows multi-étapes
            if text in ["❌ ANNULER", "⬅️ Retour au Menu", "/start"]:
                del self.editing_state[user_id]
                self.send_message(chat_id, "❌ Action annulée. Retour au menu principal.")
                if user_id in ADMIN_IDS:
                     self.send_admin_panel(chat_id)
                else:
                     self.send_message(chat_id, "Utilisez `/start`.")
                return 

            # GESTION DES WORKFLOWS (SUIVI DES ÉTATS)

            # STATE_EDIT_CARD (Saisie du code de licence)
            if current_step == STATE_EDIT_CARD:
                licence_code = text
                del self.editing_state[user_id]
                
                if self._licence_valid(licence_code):
                    self._remove_used(licence_code) 
                    
                    duration_str = next((d for d, codes in self._load_yaml().items() if licence_code not in codes), "24h")
                    hours = int(re.search(r'(\d+)', duration_str).group(1))
                    
                    self._save_user_licence(user_id, licence_code, hours)
                    
                    self.send_message(chat_id, f"✅ Licence **{licence_code}** activée pour {hours}h ! Utilisez `/start` pour commencer.")
                else:
                    self.send_message(chat_id, "❌ Code de licence invalide ou déjà utilisé. Veuillez contacter l'administrateur.")
                
                return


            # NOUVEAU: STATE_UPDATE_PANEL (Sélection initiale de la carte à éditer)
            if current_step == STATE_UPDATE_PANEL:
                if text in self.transfo.keys():
                    state['original_card'] = text
                    state['step'] = STATE_NEW_CARD
                    current_result = f"**{self.transfo[text][0]} {self.transfo[text][1]}**".strip()
                    
                    kb = [["✅ OUI"], ["❌ NON"]]
                    markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                    self.send_message(chat_id, 
                        f"Voulez-vous modifier le bouton clavier **{text}** ?\n"
                        f"Résultat actuel : {current_result}", 
                        markup
                    )
                    return
                elif text == "🔄 RESTAURER":
                    if self._restore_default():
                        self.send_message(chat_id, "✅ Configuration restaurée aux valeurs par défaut.")
                    else:
                        self.send_message(chat_id, "❌ Erreur lors de la restauration.")
                    
                    del self.editing_state[user_id]
                    self.send_update_panel(chat_id)
                    return
                else:
                    self.send_message(chat_id, "Veuillez choisir une carte existante, RESTAURER ou ANNULER.")
                    return


            # STATE_NEW_CARD (Confirmation OUI/NON)
            elif current_step == STATE_NEW_CARD:
                if text == "✅ OUI":
                    state['step'] = STATE_EDIT_RESULT
                    self.send_message(chat_id, "Veuillez saisir le **nouveau bouton clavier** (ex: 2♦️) :", markup='{"remove_keyboard": true}')
                    return
                elif text == "❌ NON":
                    del self.editing_state[user_id]
                    self.send_message(chat_id, "Modification annulée. Retour au panneau de mise à jour.")
                    self.send_update_panel(chat_id)
                    return
                else:
                    self.send_message(chat_id, "Réponse invalide. Veuillez choisir OUI ou NON.")
                    return

            # STATE_EDIT_RESULT (Saisie du Nouveau Bouton)
            elif current_step == STATE_EDIT_RESULT:
                if len(text) > 10: 
                    self.send_message(chat_id, "Entrée trop longue pour le nom de la carte. Max 10 caractères.")
                    return

                if state['original_card'] in self.transfo and text != state['original_card']:
                    del self.transfo[state['original_card']]

                state['new_card'] = text 
                state['step'] = STATE_CONFIRM
                self.send_message(chat_id, f"OK. Entrez le **nouveau résultat** de la prédiction (ex: TREFLE ♣️ ou Dame Q) :", markup='{"remove_keyboard": true}')
                return

            # STATE_CONFIRM (Saisie du Nouveau Résultat et Confirmation Finale)
            elif current_step == STATE_CONFIRM:
                
                # Finalisation de l'édition (✅ ENREGISTRER)
                if text == "✅ ENREGISTRER":
                    if 'new_result' not in state:
                        self.send_message(chat_id, "❌ Le résultat de prédiction est manquant. Veuillez le saisir d'abord.")
                        return
                        
                    # SAUVEGARDE EFFICACE ET IMMÉDIATE
                    self.transfo[state['new_card']] = tuple(state['new_result'])
                    self._save_transfo_config()
                    
                    del self.editing_state[user_id] 
                    
                    msg = (
                        f"✅ Clavier mis à jour et enregistré !\n"
                        f"_Date de modification : {self.last_updated_str}_"
                    )
                    self.send_message(chat_id, msg)
                    
                    # Retour à la sélection de carte pour une nouvelle édition
                    self.editing_state[user_id] = {'step': STATE_UPDATE_PANEL}
                    self.send_update_panel(chat_id)
                    return
                
                # Saisie du Nouveau Résultat
                parts = text.split()
                if not parts:
                    self.send_message(chat_id, "Entrée vide. Veuillez entrer le NOUVEAU résultat de prédiction.")
                    return
                
                if len(parts) == 1:
                    nom = parts[0].upper()
                    symb = ""
                else:
                    nom = parts[0].upper()
                    symb = parts[1]
                
                state['new_result'] = [nom, symb]
                display_result = f"{nom} {symb}".strip()
                
                self.send_message(chat_id, 
                    f"Vous avez configuré le bouton clavier **{state['new_card']}**\n"
                    f"et le résultat est : **{display_result}**\n\n"
                )
                
                kb = [["✅ ENREGISTRER"], ["❌ ANNULER"]]
                markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                self.send_message(chat_id, "Si cette information est correcte, confirmez :", markup)
                return


            self.send_message(chat_id, "Veuillez terminer votre action en cours (édition).")
            return


        # ROUTAGE PRINCIPAL (Logique non-état)
        
        # 1. Gestion des mots de passe en cours
        if user_id in self.waiting_password:
            self.waiting_password.remove(user_id)
            if text == ADMIN_PW:
                if user_id not in ADMIN_IDS: ADMIN_IDS.append(user_id) 
                self.send_message(chat_id, "✅ Accès Administrateur réussi ! Bienvenue.")
                self.send_admin_panel(chat_id)
                return
            else:
                self.send_message(chat_id, "❌ Mot de passe incorrect.")
                return

        if user_id in self.waiting_update_pw:
            self.waiting_update_pw.remove(user_id)
            if text == UPDATE_PW:
                self.editing_state[user_id] = {'step': STATE_UPDATE_PANEL}
                self.send_update_panel(chat_id)
                return
            else:
                self.send_message(chat_id, "❌ Mot de passe de mise à jour incorrect.")
                return

        # 2. Commandes et accès Admin
        if text == "/start":
            lic = self._get_user_licence(user_id)
            
            if not lic or self._licence_expired(lic):
                self._remove_user_licence(user_id)
                
                kb = [["🎟️ ACTIVER LICENCE"], ["ℹ️ RÈGLES DE JEU"], ["🔑 ADMIN"]]
                markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                
                self.send_message(chat_id, self.start_msg, markup)
            else:
                remaining_time = self._remaining_str(lic)
                self.send_message(chat_id, f"✅ Licence active : **{lic['code']}**\n{remaining_time}")
                self.send_keyboard(chat_id) 
            return
        
        if text.startswith("/lic ") and user_id in ADMIN_IDS:
             parts = text.split()
             if len(parts) == 2 and parts[1] in ["1h", "2h", "5h", "24h", "48h"]:
                duration = parts[1]
                code = self._add_licence(duration) 
                self.send_message(chat_id, f"✅ Licence {duration} générée : **{code}**")
                self.send_admin_panel(chat_id) 
                return
             else:
                self.send_message(chat_id, "❌ Format de commande incorrect. Utilisez `/lic [durée]`, ex: `/lic 5h`.")
                return

        if text == "/update_panel" and user_id in ADMIN_IDS:
             self.send_message(chat_id, "🔑 Entrez le mot de passe de mise à jour pour le panneau de carte :", markup='{"remove_keyboard": true}')
             self.waiting_update_pw.add(user_id)
             return


        # 3. Actions Utilisateur (Boutons de menu)
        
        if text == "🔑 ADMIN":
            self.send_message(chat_id, "🔑 Entrez le mot de passe d'administration :", markup='{"remove_keyboard": true}')
            self.waiting_password.add(user_id)
            return
            
        if text == "ℹ️ RÈGLES DE JEU" or text == "REGLES DE JEU":
            self.send_message(chat_id, self.regles)
            return

        if text == "🎟️ ACTIVER LICENCE":
            lic = self._get_user_licence(user_id)
            if not lic or self._licence_expired(lic):
                self.send_message(chat_id, "Veuillez entrer votre code de licence (ex: XYZ12308K) :", markup='{"remove_keyboard": true}')
                self.editing_state[user_id] = {'step': STATE_EDIT_CARD} 
            else:
                remaining_time = self._remaining_str(lic)
                self.send_message(chat_id, f"⚠️ Votre licence est déjà active : **{lic['code']}**\n{remaining_time}")
            return
            
        # 4. Prédiction de carte
        if text in self.transfo:
            lic = self._get_user_licence(user_id)
            if not lic or self._licence_expired(lic):
                self.send_message(chat_id, "❌ Votre licence a expiré ou n'est pas active. Utilisez `/start` pour l'activer.")
                return

            # Exécution de la prédiction
            pred_info = self.transfo[text]
            nom, symbole = pred_info[0], pred_info[1]
            
            # FORMAT DE RÉPONSE FINAL (LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE♠️ (Pique))
            result = f"LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE{symbole} ({nom})"

            remaining = self._remaining_str(lic)

            self.send_message(chat_id, f"{result}\n\n{remaining}")
            return

        # 5. AUCUNE CORRESPONDANCE
        self.send_message(chat_id, "Commande ou carte non reconnue. Utilisez les boutons du clavier ou `/start`.")
    
