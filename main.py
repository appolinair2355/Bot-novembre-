import os
from bot import lancer_bot

if __name__ == "__main__":
    if not os.getenv("BOT_TOKEN"):
        raise RuntimeError("BOT_TOKEN non défini")
    lancer_bot()
  
