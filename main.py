import os
import threading
import time
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ------------- importe nos handlers -------------
from bot import start, admin, message_general, TOKEN, WEBHOOK_PATH

# ------------- Flask -------------
app = Flask(__name__)

# ------------- PTB Application -------------
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("admin", admin))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_general))

# ------------- Webhook Flask -------------
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(400)
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    # traite l’update en arrière-plan
    threading.Thread(target=application.process_update, args=(update,)).start()
    return "", 200

# ------------- Health Check (Render) -------------
@app.route("/")
def health():
    return "OK", 200

# ------------- Mise à jour du webhook au démarrage -------------
def set_telegram_webhook():
    url = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
    while True:
        try:
            application.bot.set_webhook(url)
            print("Webhook Telegram défini →", url)
            break
        except Exception as e:
            print("Retry set_webhook :", e)
            time.sleep(2)

if __name__ == "__main__":
    set_telegram_webhook()
    # Gunicorn lancera cette appli sur 0.0.0.0:PORT
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

  
