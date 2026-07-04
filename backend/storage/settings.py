# backend/storage/settings.py
import os
import json

# Ruta al archivo JSON de configuración local
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".nex_settings.json")

def save_workspace_path(path: str):
    """
    Guarda de forma persistente la ruta absoluta del Workspace en un archivo JSON.
    """
    absolute_path = os.path.abspath(path)
    data = {"workspace_path": absolute_path}
    
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return absolute_path

def get_workspace_path() -> str:
    """
    Recupera la ruta del Workspace guardado.
    Prioriza la variable de entorno NEX_WORKSPACE sobre el archivo de configuración.
    Retorna None si no se ha configurado.
    """
    env_path = os.environ.get("NEX_WORKSPACE")
    if env_path:
        return os.path.abspath(env_path)

    if not os.path.exists(SETTINGS_FILE):
        return None

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("workspace_path")
    except Exception:
        return None