# backend/config/loader.py
import os

WORKSPACE_SKIP_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".opencode", "dist", "build", ".next",
}
WORKSPACE_TREE_LIMIT = 100


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


def workspace_file_tree(root: str, limit: int = WORKSPACE_TREE_LIMIT) -> str:
    """Lista un nivel del workspace (directorios con '/' al final), saltando
    carpetas ruidosas (node_modules, .git, .venv...).
    """
    try:
        entries = sorted(os.scandir(root), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError:
        return "(no se pudo leer el directorio del workspace)"

    lines = []
    for entry in entries:
        if entry.name in WORKSPACE_SKIP_DIRS:
            continue
        lines.append(f"{entry.name}/" if entry.is_dir() else entry.name)
        if len(lines) >= limit:
            lines.append(f"... (lista truncada a {limit} entradas)")
            break
    return "\n".join(lines) if lines else "(workspace vacío)"


def build_system_prompt(workspace_root: str | None = None, language: str | None = None) -> str:
    """Compone el prompt completo: base + idioma + entorno real + contexto actual
    del workspace (ruta y contenido raíz), para que el modelo no suponga archivos
    ni directorios que no existen.
    """
    from utils.helpers import get_current_datetime_str, get_system_info

    prompt = load_system_prompt()
    blocks = []

    if language:
        blocks.append(
            f"[IDIOMA]\n"
            f"Responde SIEMPRE en el idioma '{language}'. Úsalo para todas tus "
            "respuestas, explicaciones y mensajes."
        )

    blocks.append(
        "[INFORMACION EN TIEMPO REAL]\n"
        f"- Fecha y hora actual: {get_current_datetime_str()}\n"
        f"- Información del sistema: {get_system_info()}\n"
    )

    if workspace_root:
        workspace_abs = os.path.abspath(workspace_root)
        blocks.append(
            "[CONTEXTO ACTUAL DEL WORKSPACE]\n"
            f"- Ruta absoluta del workspace: {workspace_abs}\n"
            f"- Contenido del nivel raíz en este momento:\n"
            f"{workspace_file_tree(workspace_abs)}\n"
            "\n"
            "Reglas para no confundirte:\n"
            "- El workspace puede cambiar entre sesiones. NO asumas que archivos "
            "mencionados en conversaciones o historiales anteriores siguen en este "
            "workspace: verifica SIEMPRE con list_files/read_file antes de hablar de "
            "un archivo concreto.\n"
            "- Usa rutas relativas al workspace en las herramientas "
            "(ej: 'backend/tools/registry.py'), no rutas absolutas ni rutas de otros "
            "proyectos.\n"
            "- La lista de contenido anterior es un snapshot; para el estado exacto "
            "usa list_files o find_files."
        )

    return prompt + "\n\n" + "\n\n".join(blocks)


def load_initial_config():
    """
    (Reservado para la Fase 6) Lógica para leer y parsear el config.toml
    """
    pass
