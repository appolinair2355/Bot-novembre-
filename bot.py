import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from admin import is_admin, generate_licence, use_licence, licence_valid
from licences import check_licence, save_licence_usage

TOKEN = os.getenv("BOT_TOKEN")

keyboard = [
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : TREFLE"],
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : CARREAU"],
    ["LE JOUEUR VA OBTENIR UNE CARTE ENSEIGNE : PIQUE"],
    ["ASSURANCE 100%"],
    ["REGLES DE JEU"],
    ["MODE D'EMPLOI"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

CARTES_REPONSES = {
    "10♦️": "♠️",
    "10♠️": "❤️",
    "9♣️": "❤️",
    "9♦️": "♠️",
    "8♣️": "♠️",
    "8♠️": "♣️",
    "7♠️": "♠️",
    "7♣️": "♣️",
    "6♦️": "♣️",
    "6♣️": "♦️"
}

MODE_EMPLOI = """
1️⃣ LES HEURES DE JEUX FAVORABLE : 01h à 04h  / 14h à 17h / 20h à 22h

2️⃣ ÉVITEZ DE PARIÉ LE WEEKEND : Le Bookmaker Change régulièrement les algorithmes parce qu'il y a beaucoup de joueurs  le weekend

3️⃣ SUIVRE LE TIMING DES 10 MINUTES : Après avoir placé un paris et gagnez un jeu il est essentiel de sortir du Bookmaker et revenir 10 minutes après pour un autre paris

4️⃣ NE PAS FAIRE PLUS DE 20 PARIS GAGNANT PAR JOUR : Si vous violé cette règle votre compte sera  Bloqué par le Bookmaker

5️⃣ ÉVITEZ D'ENREGISTRER UN COUPON : Quand vous enregistrez un coupon pour le partager , Vous augmentez vos chances de perdre

🍾BON GAINS 🍾
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not licence_valid(user_id):
        await update.message.reply_text("🔒 Veuillez entrer votre licence pour accéder au bot :")
        context.user_data["awaiting_licence"] = True
        return
    await update.message.reply_text("✅ Accès autorisé. Bienvenue dans Bakara Beast !", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get("awaiting_licence"):
        if check_licence(text):
            save_licence_usage(text, user_id)
            context.user_data["awaiting_licence"] = False
            await update.message.reply_text("✅ Licence acceptée. Accès autorisé !", reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ Licence invalide ou déjà utilisée.")
        return

    if not licence_valid(user_id):
        await update.message.reply_text("🔒 Votre licence a expiré. Contactez l’admin.")
        return

    if text in CARTES_REPONSES:
        await update.message.reply_text(f"→ {CARTES_REPONSES[text]}")
    elif text == "MODE D'EMPLOI":
        await update.message.reply_text(MODE_EMPLOI)
    elif text == "REGLES DE JEU":
        await update.message.reply_text("📜 Les règles du jeu seront ajoutées ici.")
    elif text == "ASSURANCE 100%":
        await update.message.reply_text("✅ Assurance activée.")
    else:
        await update.message.reply_text("🃏 Envoyez une carte (ex: 10♦️)")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2 or args[0] != "kouame2025":
        await update.message.reply_text("❌ Accès refusé.")
        return
    try:
        hours = int(args[1])
        licence = generate_licence(hours)
        await update.message.reply_text(f"🔑 Licence générée : `{licence}`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Usage : /admin kouame2025 <heures>")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    port = int(os.environ.get("PORT", 10000))
    app.run_webhook(listen="0.0.0.0", port=port, webhook_url="https://tonnomapp.render.com")

if __name__ == "__main__":
    main()
