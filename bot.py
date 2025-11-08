import os
from . import licences   # si tu utilises « from . import licences »
TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_PATH = "/telegram"

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# ------------- Clavier identique à l’image -------------
CLAVIER = ReplyKeyboardMarkup([
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : TREFLE"],
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : CARREAU"],
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : PIQUE"],
    ["ASSURANCE 100%"],
    ["REGLES DE JEU"],
    ["MODE D'EMPLOI"]
], resize_keyboard=True)

WEBHOOK_PATH = "/telegram"

# ------------- Réponses cartes -------------
CARTES = {
    "10♦️": "♠️", "10♠️": "❤️", "9♣️": "❤️", "9♦️": "♠️",
    "8♣️": "♠️", "8♠️": "♣️", "7♠️": "♠️", "7♣️": "♣️",
    "6♦️": "♣️", "6♣️": "♦️"
}

MODE_EMPLOI = """
1️⃣ HEURES FAVORABLES : 01h-04h / 14h-17h / 20h-22h  
2️⃣ ÉVITEZ LE WEEKEND (algo modifié)  
3️⃣ TIMING 10 min : après un gain, pause 10 min  
4️⃣ MAX 20 PARIS GAGNANTS / jour (ban si +)  
5️⃣ ÉVITEZ D’ENREGISTRER / PARTAGER VOS COUPONS  

🍾 BON GAINS 🍾
"""

# ------------- Handlers -------------
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Vérifie si licence valide
    for code, data in licences._load().items():
        if data["user_id"] == user_id and not licences.est_expiree(code):
            await update.message.reply_text("✅ Accès autorisé !", reply_markup=CLAVIER)
            return
    await update.message.reply_text("🔒 Envoyez votre licence :")

async def admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) != 2:
        await update.message.reply_text("Usage : /admin kouame2025 <heures>")
        return
    if not admin_module.est_admin(ctx.args[0]):
        await update.message.reply_text("❌ Accès refusé.")
        return
    try:
        h = int(ctx.args[1])
        code = admin_module.generer_licence(h)
        await update.message.reply_text(f"🔑 Licence générée : `{code}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("Heures doit être un nombre entier.")

async def message_general(update: Update, _: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # 1) test licence (format simple)
    if len(text) >= 7 and "h" in text and text[-1].isupper():
        if licences.licence_valide(text):
            licences.marquer_utilisee(text, user_id)
            await update.message.reply_text("✅ Licence acceptée !", reply_markup=CLAVIER)
            return
        else:
            await update.message.reply_text("❌ Licence invalide ou déjà utilisée.")
            return

    # 2) vérifie expiration
    for code, data in licences._load().items():
        if data["user_id"] == user_id and not licences.est_expiree(code):
            break
    else:
        await update.message.reply_text("🔒 Licence requise / expirée.")
        return

    if text in CARTES:
        await update.message.reply_text(f"→ {CARTES[text]}")
    elif text == "MODE D'EMPLOI":
        await update.message.reply_text(MODE_EMPLOI)
    elif text == "REGLES DE JEU":
        await update.message.reply_text("📜 Règles complètes disponibles prochainement.")
    elif text == "ASSURANCE 100%":
        await update.message.reply_text("✅ Assurance enregistrée.")
    else:
        await update.message.reply_text("🃏 Envoyez une carte (ex : 10♦️)")
        
