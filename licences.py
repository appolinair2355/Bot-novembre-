import json
import os
import time

LICENCES_FILE = "licences.json"

def load_licences():
    if not os.path.exists(LICENCES_FILE):
        return {}
    with open(LICENCES_FILE, "r") as f:
        return json.load(f)

def save_licences(data):
    with open(LICENCES_FILE, "w") as f:
        json.dump(data, f)

def ajouter_licence(licence, hours):
    data = load_licences()
    data[licence] = {
        "hours": hours,
        "used": False,
        "user_id": None,
        "created_at": time.time()
    }
    save_licences(data)

def check_licence(licence):
    data = load_licences()
    return licence in data and not data[licence]["used"]

def save_licence_usage(licence, user_id):
    data = load_licences()
    if licence in data and not data[licence]["used"]:
        data[licence]["used"] = True
        data[licence]["user_id"] = user_id
        data[licence]["used_at"] = time.time()
        save_licences(data)

def licence_deja_utilisee(licence):
    data = load_licences()
    return data.get(licence, {}).get("used", False)
