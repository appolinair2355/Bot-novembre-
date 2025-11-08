import json, os, time, pathlib

DB = pathlib.Path("licences.json")

# ---------- helpers ----------
def _load() -> dict:
    if not DB.exists():
        DB.write_text("{}")
    return json.loads(DB.read_text())

def _save(data: dict):
    DB.write_text(json.dumps(data, indent=2))

# ---------- métiers ----------
def ajouter_licence(code: str, hours: int):
    data = _load()
    data[code] = {"hours": hours, "used": False, "user_id": None,
                  "created_at": time.time()}
    _save(data)

def licence_valide(code: str) -> bool:
    return code in _load() and not _load()[code]["used"]

def marquer_utilisee(code: str, user_id: int):
    data = _load()
    if code in data and not data[code]["used"]:
        data[code]["used"] = True
        data[code]["user_id"] = user_id
        data[code]["used_at"] = time.time()
        _save(data)

def est_expiree(code: str) -> bool:
    """
    VRAI si > hours*3600 secondes ont passé depuis used_at
    """
    data = _load().get(code)
    if not data or not data["used"]:
        return False
    elapsed = time.time() - data["used_at"]
    return elapsed > data["hours"] * 3600
        
