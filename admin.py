import random
import string
from licences import ajouter_licence, licence_deja_utilisee

def generate_licence(hours):
    lettre = random.choice(string.ascii_lowercase)
    chiffres = ''.join(random.choices(string.digits, k=3))
    maj = random.choice(string.ascii_uppercase)
    licence = f"{lettre}{chiffres}{hours}h{maj}"
    ajouter_licence(licence, hours)
    return licence

def is_admin(password):
    return password == "kouame2025"

def use_licence(licence, user_id):
    if licence_deja_utilisee(licence):
        return False
    return True

def licence_valid(user_id):
    # TODO: vérifier si licence encore active pour ce user
    return True
    
