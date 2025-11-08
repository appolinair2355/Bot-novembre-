from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
import os
from admin import generer_licence, est_admin
from licences import licence_valide, marquer_utilisee, est_expiree

TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 10000))

# ---------------- clavier -----------------
CLAVIER = ReplyKeyboardMarkup([
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : TREFLE"],
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : CARREAU"],
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : PIQUE"],
    ["ASSURANCE 100%"],
    ["REGLES DE JEU"],
    ["MODE D'EMPLOI"]
], resize_keyboard=True)

# ---------------- réponses cartes ----------
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
5️⃣ NE PAS ENREGISTRER / PARTAGER VOS COUPONS  

🍾 BON GAINS 🍾
"""

# -------------- handlers --------------
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # on vérifie s'il possède une licence encore valide
    for code, data in licences._load().items():
        if data["user_id"] == user_id and not est_expiree(code):
            await update.message.reply_text("✅ Accès autorisé !", reply_markup=CLAVIER)
            return
    await update.message.reply_text("🔒 Envoyez votre licence :")
    # on pourrait stocker un flag, mais ici on teste tout message

async def admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) != 2:
        await update.message.reply_text("Usage : /admin kouame2025 <heures>")
        return
    if not est_admin(ctx.args[0]):
        await update.message.reply_text("❌ Accès refusé.")
        return
    try:
        h = int(ctx.args[1])
        code = generer_licence(h)
        await update.message.reply_text(f"🔑 Licence générée : `{code}`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("Heures doit être un nombre entier.")

async def message_general(update: Update, _: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # 1) test licence (d'abord on regarde si c'est une licence)
    if len(text) >= 7 and "h" in text and text[-1].isupper():
        if licence_valide(text):
            marquer_utilisee(text, user_id)
            await update.message.reply_text("✅ Licence acceptée !", reply_markup=CLAVIER)
            return
        else:
            await update.message.reply_text("❌ Licence invalide ou déjà utilisée.")
            return

    # 2) sinon on traite les autres messages
    for code in licences._load():
        if licences._load()[code]["user_id"] == user_id and not est_expiree(code):
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

# -------------- lancement ----------
def lancer_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_general))
    url = f"https://bakara-beast.onrender.com"
    app.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=url)
