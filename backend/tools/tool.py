# backend/tools/tool.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class Tool(ABC):
    """
    Clase abstracta base para todas las herramientas de Nex.
    Cualquier herramienta nueva debe heredar de aquí.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la herramienta (ej. 'filesystem_write')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción detallada para que el LLM sepa cuándo y cómo usarla."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Esquema de parámetros en formato JSON Schema que requiere la herramienta."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Lógica de ejecución física en Python."""
        pass