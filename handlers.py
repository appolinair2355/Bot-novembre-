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
STATE_EDIT_CARD = 1
STATE_NEW_CARD = 2
STATE_EDIT_RESULT = 3
STATE_CONFIRM = 4

# Valeurs de configuration par défaut pour la restauration
DEFAULT_TRANSFO_DATA = {
    "10♦️": ["PIQUE", "♠️"], 
    "10♠️": ["COEUR", "❤️"], 
    "9♣️": ["COEUR", "❤️"],
    "9♦️": ["PIQUE", "♠️"],
    "8♣️": ["PIQUE", "♠️"],
    "8♠️": ["TREFLE", "♣️"],
    "7♠️": ["PIQUE", "♠️"],
    "7♣️": ["TREFLE", "♣️"],
    "6♦️": ["TREFLE", "♣️"],
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
        self.waiting_licence_code = set()
        self.editing_state = {} 


    # CONFIGURATION DES CARTES (TRANSFO)
    def _ensure_transfo_config(self):
        """S'assure que le fichier de configuration des cartes existe, sinon le crée avec les valeurs par défaut."""
        if not os.path.exists(TRANSFO_CONFIG):
            default_transfo = {
                "transfo": {k: list(v) for k, v in DEFAULT_TRANSFO_DATA.items()},
                "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)") 
            }
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(default_transfo, f, indent=4)
                
        self._load_transfo_config()

    def _load_transfo_config(self):
        """Charge le dictionnaire des correspondances. Utilise les valeurs par défaut si la lecture échoue."""
        try:
            with open(TRANSFO_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data.get("transfo") or len(data["transfo"]) < 10:
                    raise ValueError("Configuration dans le fichier incomplète ou invalide.")
                
                self.transfo = {k: tuple(v) for k, v in data["transfo"].items()} 
                self.last_updated_str = data["last_updated"]
                logger.info("Configuration des cartes chargée depuis le fichier.")
                
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Erreur lors du chargement de transfo_config.json ({type(e).__name__}). Utilisation des valeurs par défaut.")
            self.transfo = {k: tuple(v) for k, v in DEFAULT_TRANSFO_DATA.items()}
            self.last_updated_str = "Défaut (GMT+1)"

    def _save_transfo_config(self):
        """Sauvegarde les correspondances mises à jour."""
        transfo_list = {k: list(v) for k, v in self.transfo.items()} 
        data = {
            "transfo": transfo_list,
            "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)")
        }
        try:
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.last_updated_str = data["last_updated"]
            logger.info(f"Configuration des cartes mise à jour et enregistrée par {self.last_updated_str}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de transfo_config.json: {e}")

    def _restore_default(self):
        """Rétablit la configuration des cartes par défaut et sauvegarde."""
        data = {
            "transfo": {k: list(v) for k, v in DEFAULT_TRANSFO_DATA.items()},
            "last_updated": datetime.now().strftime("%d-%m-%Y à %H:%M:%S (GMT+1)")
        }
        try:
            with open(TRANSFO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self._load_transfo_config() 
            logger.info("Configuration des cartes restaurée aux valeurs par défaut.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la restauration: {e}")
            return False

    # GESTION DES LICENCES (YAML/JSON)
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
        """Génère le format de licence."""
        part1 = ''.join(choice(MAJ) for _ in range(3))
        part2 = ''.join(choice(CHIFFRES) for _ in range(3))
        part3 = datetime.now().strftime("%H")
        part4 = choice(MAJ)
        part5 = choice(LETTRES_KOUAME)
        return f"{part1}{part2}{part3}{part4}{part5}"

    def _add_licence(self, duration: str) -> str:
        """
        Génère un code unique, l'ajoute à la liste de la durée spécifiée et sauvegarde.
        S'assure de la non-duplication du code.
        """
        data = self._load_yaml()
        
        # S'assure de la non-duplication en bouclant
        code = self._generate_code() 
        while self._licence_valid(code):
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
    
    # API ET CLAVIERS

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
            
    def _send_start_menu(self, chat_id: int):
        """Fonction utilitaire pour envoyer le menu de départ."""
        kb = [["1️⃣ J’ai une licence"], ["2️⃣ Administrateur"], ["3️⃣ Mise à jour"]]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "🔰 Choisis :", markup)
        return

    def send_keyboard(self, chat_id: int) -> bool:
        """Envoie le clavier de prédiction des 10 cartes pour les utilisateurs licenciés."""
        all_cards = list(self.transfo.keys())
        if len(all_cards) < 10:
             all_cards = list(DEFAULT_TRANSFO_DATA.keys()) 
             if len(all_cards) < 10:
                 return self.send_message(chat_id, "❌ Erreur de configuration: 10 cartes de base sont requises.")
             
        # Organisation du clavier (4-3-3)
        kb = [
            all_cards[0:4], 
            all_cards[4:7], 
            all_cards[7:10], 
            ["REGLES DE JEU"] 
        ]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        
        msg = (
            self.start_msg + 
            f"\n\n_Dernière mise à jour : {self.last_updated_str}_"
        )
        return self.send_message(chat_id, msg, markup)

    def send_admin_panel(self, chat_id: int):
        """Envoie le panneau d'administration des licences."""
        data = self._load_yaml()
        unused = {k: len(v) for k, v in data.items()}
        lines = "\n".join([f"**{d}** : {nb} disponible(s)" for d, nb in unused.items()]) 
        self.send_message(chat_id, f"📦 Licences disponibles :\n{lines}")
        kb = [["/lic 1h"], ["/lic 2h"], ["/lic 5h"], ["/lic 24h"], ["/lic 48h"], ["⬅️ Retour au Menu"]]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "Génération rapide :", markup)
        
    def send_update_panel(self, chat_id: int):
        """Envoie le clavier des 10 cartes pour l'édition (Administrateur)."""
        all_cards = list(self.transfo.keys())
        if len(all_cards) < 10:
             return self.send_message(chat_id, "❌ Erreur de configuration: 10 cartes de base sont requises pour l'édition.")
             
        kb = [
            all_cards[0:3], all_cards[3:6],
            all_cards[6:9], [all_cards[9]],
            ["🔄 RESTAURER", "⬅️ Retour au Menu"]
        ]
        markup = json.dumps({"keyboard": kb, "resize_keyboard": True, "one_time_keyboard": False})
        self.send_message(chat_id, "Choisissez la carte de départ à modifier (actuellement):", markup)
    # ROUTE
    def handle_update(self, update: Dict[str, Any]):
        msg = update.get("message", {})
        if "text" not in msg or "chat" not in msg:
             return

        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]

        # 1. GESTION DU NETTOYAGE (PRIORITÉ MAX)
        if text == "/start" or text == "⬅️ Retour au Menu":
            # NETTOYAGE COMPLET DES ÉTATS D'ATTENTE ET D'ÉDITION
            self.waiting_password.discard(user_id)
            self.waiting_update_pw.discard(user_id)
            self.waiting_licence_code.discard(user_id)
            self.editing_state.pop(user_id, None) 
            
            self._send_start_menu(chat_id)
            return

        # 2. GESTION DES ÉTATS D'ÉDITION MULTI-PARTIES (PRIORITÉ HAUTE)
        if user_id in self.editing_state:
            state = self.editing_state[user_id]
            current_step = state['step']
            
            # --- SOUS-FLUX ENREGISTRER / ANNULER ---
            if text == "❌ ANNULER":
                del self.editing_state[user_id]
                self.send_message(chat_id, "❌ Modification annulée. Retour au panneau de mise à jour.")
                self.send_update_panel(chat_id) 
                return 

            # CORRECTION : Traitement du clic ENREGISTRER
            if text == "✅ ENREGISTRER" and current_step == STATE_CONFIRM:
                original_card = state['original_card']
                new_card = state['new_card']
                new_result = tuple(state['new_result'])
                
                # Logique d'enregistrement (suppression de l'ancienne carte si le nom change)
                if original_card != new_card and original_card in self.transfo:
                    del self.transfo[original_card] 
                
                self.transfo[new_card] = new_result
                
                self._save_transfo_config()
                
                del self.editing_state[user_id] 
                
                msg = (
                    f"✅ Clavier mis à jour et enregistré !\n"
                    f"_Date de modification : {self.last_updated_str}_\n\n"
                    f"Utilisez le bouton `⬅️ Retour au Menu` ci-dessous pour continuer."
                )
                
                kb = [["⬅️ Retour au Menu"]] 
                markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                self.send_message(chat_id, msg, markup)
                return

            # --- FLUX DES ÉTAPES DE SAISIE ---
            
            # STATE_EDIT_CARD (Attente de la sélection de carte existante)
            if current_step == STATE_EDIT_CARD:
                
                if text in self.transfo.keys():
                    state['original_card'] = text
                    state['step'] = STATE_NEW_CARD 
                    
                    kb = [["✅ OUI"], ["❌ NON"]]
                    markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                    self.send_message(chat_id, 
                        f"Voulez-vous modifier le bouton clavier **{text}** ?", 
                        markup
                    )
                    return
                else: 
                    self.send_message(chat_id, "Carte non reconnue. Veuillez choisir une carte existante dans le clavier d'édition.")
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

                state['new_card'] = text 
                state['step'] = STATE_CONFIRM
                self.send_message(chat_id, f"OK. Entrez le **nouveau résultat** de la prédiction (ex: TREFLE ♣️ ou Dame Q) :", markup='{"remove_keyboard": true}')
                return

            # STATE_CONFIRM (Saisie du Nouveau Résultat)
            elif current_step == STATE_CONFIRM:
                # L'utilisateur vient de saisir le résultat (ce n'est pas "✅ ENREGISTRER" qui est géré plus haut)
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
                
                kb = [["✅ ENREGISTRER"], ["❌ ANNULER"]]
                markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                self.send_message(chat_id, 
                    f"Vous avez modifié le bouton clavier **{state['original_card']}** par **{state['new_card']}**\n"
                    f"et le nouveau résultat pour ce bouton clavier est : **{display_result}**\n\n"
                    "Si cette information est correcte, confirmez :", 
                    markup
                )
                return

            self.send_message(chat_id, "Veuillez terminer votre action en cours (édition).")
            return


        # 3. ROUTAGE DES COMMANDES HAUT NIVEAU (ADMIN - hors édition)

        # Logique de Restauration des Cartes (Admin)
        if text == "🔄 RESTAURER" and user_id in ADMIN_IDS:
            if self._restore_default():
                self.send_message(chat_id, "✅ Configuration des cartes **restaurée** aux valeurs par défaut !")
                self.send_update_panel(chat_id)
            else:
                self.send_message(chat_id, "❌ Échec de la restauration de la configuration des cartes.")
            return
            
        # Logique de Génération de Licence (Admin)
        if text.startswith("/lic ") and user_id in ADMIN_IDS:
            parts = text.split()
            if len(parts) == 2 and parts[1] in ["1h", "2h", "5h", "24h", "48h"]:
                duration = parts[1]
                new_code = self._add_licence(duration)
                
                self.send_message(
                    chat_id, 
                    f"✅ Licence **{duration}** générée :\n\n`{new_code}`"
                )
                self.send_admin_panel(chat_id) 
                return
            else:
                self.send_message(chat_id, "❌ Format de licence invalide. Utilisez `/lic 1h`, `/lic 2h`, etc.")
                return


        # ====================================================================
        # COMMANDE 3: MISE À JOUR (3️⃣ Mise à jour)
        # ====================================================================
        if text == "3️⃣ Mise à jour":
            if user_id in ADMIN_IDS:
                self.waiting_update_pw.add(user_id)
                
                kb = [["⬅️ Retour au Menu"]]
                markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
                self.send_message(chat_id, "Entrez le mot de passe de mise à jour :", markup=markup)
            else:
                self.send_message(chat_id, "❌ Accès refusé. Seuls les administrateurs désignés peuvent effectuer des mises à jour.")
            return

        # Vérification du Mot de passe Mise à Jour (Strict)
        if user_id in self.waiting_update_pw:
            self.waiting_update_pw.remove(user_id)
            # Pas besoin de vérifier "⬅️ Retour au Menu" car c'est géré en priorité 1

            if text == UPDATE_PW and user_id in ADMIN_IDS:
                # Initialisation de l'état d'édition
                self.editing_state[user_id] = {'step': STATE_EDIT_CARD, 'original_card': None, 'new_result': None, 'new_card': None}
                
                self.send_message(chat_id, "✅ Mot de passe correct. **Mode Édition activé.**")
                self.send_update_panel(chat_id) 
                return
            else:
                self.send_message(chat_id, "❌ Mot de passe incorrect.")
                self._send_start_menu(chat_id)
                return

        # ====================================================================
        # COMMANDE 2: ADMINISTRATEUR (2️⃣ Administrateur)
        # ====================================================================
        if text == "2️⃣ Administrateur":
            self.waiting_password.add(user_id)
            
            kb = [["⬅️ Retour au Menu"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
            self.send_message(chat_id, "Entrez le mot de passe administrateur :", markup=markup)
            return

        # Vérification du Mot de passe Administrateur (Strict)
        if user_id in self.waiting_password:
            self.waiting_password.remove(user_id)
            
            if text == ADMIN_PW:
                self.send_admin_panel(chat_id)
                return
            else:
                self.send_message(chat_id, "❌ Mot de passe administrateur incorrect.")
                self._send_start_menu(chat_id)
                return


        # ====================================================================
        # COMMANDE 1: LICENCE (1️⃣ J’ai une licence)
        # ====================================================================
        if text == "1️⃣ J’ai une licence":
            self.waiting_licence_code.add(user_id)
            
            kb = [["⬅️ Retour au Menu"]]
            markup = json.dumps({"keyboard": kb, "resize_keyboard": True})
            self.send_message(chat_id, "Veuillez entrer votre licence :", markup=markup)
            return

        # Traitement du Code de Licence Saisi (Strict)
        if user_id in self.waiting_licence_code:
            self.waiting_licence_code.remove(user_id)
                 
            # Logique de vérification de licence (pour texte)
            data = self._load_yaml()
            is_valid_code = any(text in lst for lst in data.values())

            if not is_valid_code:
                self.send_message(chat_id, "❌ Licence invalide ou déjà utilisée.")
                self._send_start_menu(chat_id)
                return
            
            # --- Activation de la licence ---
            lic_user = self._get_user_licence(user_id)
            
            if lic_user and not self._licence_expired(lic_user):
                self.send_message(chat_id, "✅ Licence déjà active.")
                self.send_keyboard(chat_id) 
                return
            
            if lic_user and self._licence_expired(lic_user):
                self._remove_user_licence(user_id) 
                
            code = text
            duration = None
            
            for d, lst in data.items():
                if code in lst:
                    duration = d
                    break
            
            if not duration:
                self.send_message(chat_id, "❌ Erreur interne lors de la vérification de la licence.")
                self._send_start_menu(chat_id)
                return
            
            self._remove_used(code)
            self._save_user_licence(user_id, code, int(duration.replace("h", ""))) 
            
            self.send_message(chat_id, "✅ Licence acceptée !")
            remaining = self._remaining_str(self._get_user_licence(user_id))
            self.send_message(chat_id, remaining)
            self.send_keyboard(chat_id) 
            return
            
        
        # 4. VÉRIFICATION D'EXPIRATION ET BLOCAGE (Contrôle d'accès général)
        lic_user = self._get_user_licence(user_id)
        if not lic_user or self._licence_expired(lic_user):
            if lic_user and self._licence_expired(lic_user):
                self._remove_user_licence(user_id) 
            
            self.send_message(chat_id, "🔒 Licence invalide ou expirée. Veuillez entrer une licence valide.")
            self._send_start_menu(chat_id)
            return

        # 5. UTILISATEUR LICENCIÉ (PRÉDICTION)
        remaining = self._remaining_str(lic_user)
        self.send_message(chat_id, remaining)

        # Affichage de la prédiction
        if text == "REGLES DE JEU":
            self.send_message(chat_id, self.regles)
            return
        if text in self.transfo:
            nom, symb = self.transfo[text] 
            
            display_result = f"{nom} {symb}".strip() 
            
            self.send_message(chat_id, f"⚜️LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : **{display_result}**\n\n📍ASSURANCE 100%📍")
            return
        
        # 6. Message non compris
        self.send_message(chat_id, "Je n'ai pas compris ce message. Veuillez sélectionner une carte ou utiliser une commande.")
        
