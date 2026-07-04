# backend/config/loader.py
import os

def load_text_file(relative_path: str, fallback_content: str = "") -> str:
    """
    Utility de bajo nivel para leer archivos de texto de forma segura.
    """
    # Buscamos el archivo partiendo desde la raíz del backend
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, relative_path)
    
    if not os.path.exists(target_path):
        return fallback_content
        
    with open(target_path, "r", encoding="utf-8") as file:
        return file.read()

def load_system_prompt() -> str:
    """
    Carga el prompt base del sistema para el comportamiento de Nex.
    """
    fallback = "Eres Nex, un asistente de IA avanzado para la terminal."
    return load_text_file("prompts/system.txt", fallback_content=fallback)

def load_initial_config():
    """
    (Reservado para la Fase 6) Lógica para leer y parsear el config.toml
    """
    pass