import random, string
from licences import ajouter_licence

PWD_ADMIN = "kouame2025"

def est_admin(mot: str) -> bool:
    return mot == PWD_ADMIN

def generer_licence(heures: int) -> str:
    lettre  = random.choice(string.ascii_lowercase)
    chiffre = ''.join(random.choices(string.digits, k=3))
    maj     = random.choice(string.ascii_uppercase)
    code    = f"{lettre}{chiffre}{heures}h{maj}"
    ajouter_licence(code, heures)
    return code
    
