from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="El mensaje o instrucción del usuario")
    session_id: str = Field(..., description="Identificador único de la sesión de chat")
    image_data: str | None = Field(None, description="Imagen en base64 para análisis visual")
    image_mime: str | None = Field(None, description="Tipo MIME de la imagen (e.g. image/png)")
    provider: str | None = Field(None, description="Proveedor LLM a usar (gemini, openai, ollama, etc.)")
    model: str | None = Field(None, description="Modelo específico a usar")
    language: str | None = Field(None, description="Idioma del usuario (es, en, fr, pt, de)")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Respuesta generada por Nex después del ciclo autónomo")


class MetricsResponse(BaseModel):
    memory: float = Field(..., description="Porcentaje de uso de memoria RAM")
    context_buffer: float = Field(..., description="Porcentaje de uso del buffer de contexto")
    agent_status: str = Field(..., description="Estado del agente: online, busy, offline")
    cpu: float = Field(..., description="Porcentaje de uso de CPU")


class WorkspaceResponse(BaseModel):
    path: str = Field(..., description="Ruta del workspace activo")


class ProviderInfo(BaseModel):
    name: str = Field(..., description="Nombre del proveedor")
    models: list[str] = Field(default_factory=list, description="Modelos disponibles")
    configured: bool = Field(..., description="Si el proveedor tiene API key configurada")


class SettingsResponse(BaseModel):
    provider: str = Field(..., description="Proveedor activo")
    model: str = Field(..., description="Modelo activo")
    temperature: float = Field(0.7, description="Temperatura del modelo")
    max_tokens: int = Field(8192, description="Máximo de tokens")
    top_p: float = Field(0.95, description="Top P sampling")
    providers: list[ProviderInfo] = Field(default_factory=list, description="Proveedores disponibles")
    workspace_path: str = Field("", description="Ruta del workspace")
    interface_radius: int = Field(12, description="Radio de curvatura de la interfaz")
    theme: str = Field("dark", description="Tema de la interfaz: dark, light, system")
    language: str = Field("es", description="Idioma: es, en")
    font_size: int = Field(14, description="Tamaño de fuente base")
    animations_enabled: bool = Field(True, description="Animaciones de interfaz")
    compact_mode: bool = Field(False, description="Modo compacto")
    orb_animation: bool = Field(True, description="Animación del orb")
    send_mode: str = Field("enter", description="Modo de envío: enter, ctrl_enter")
    auto_scroll: bool = Field(True, description="Auto-scroll en nuevos mensajes")
    show_timestamps: bool = Field(False, description="Mostrar marcas de tiempo")
    syntax_highlighting: bool = Field(True, description="Resaltado de sintaxis")
    custom_api_urls: dict[str, str] = Field(default_factory=dict, description="URLs personalizadas por proveedor")
    system_prompt: str = Field("", description="Prompt de sistema personalizado")
    max_tool_calls: int = Field(10, description="Máximo de llamadas a herramientas por ciclo")
    max_sessions: int = Field(50, description="Máximo de sesiones guardadas")
    context_size: int = Field(32, description="Tamaño de contexto en k")
    timeout: int = Field(60, description="Timeout de conexión en segundos")
    auto_save_interval: int = Field(60, description="Intervalo de auto-guardado en segundos")
    sidebar_width: int = Field(270, description="Ancho de la barra lateral")
    accent_color: str = Field("#6366f1", description="Color de acento de la interfaz")
    font_family: str = Field("'Inter', system-ui, -apple-system, sans-serif", description="Familia tipográfica")
    sidebar_visible: bool = Field(True, description="Visibilidad de la barra lateral")
    auto_title: bool = Field(True, description="Generar título automático de sesión")
    confirm_delete: bool = Field(True, description="Confirmar antes de eliminar sesión")


class SettingsUpdateRequest(BaseModel):
    provider: str | None = Field(None, description="Proveedor a usar")
    model: str | None = Field(None, description="Modelo a usar")
    temperature: float | None = Field(None, description="Temperatura")
    max_tokens: int | None = Field(None, description="Máximo de tokens")
    top_p: float | None = Field(None, description="Top P sampling")
    api_keys: dict[str, str] | None = Field(None, description="API keys a actualizar: {provider: key}")
    interface_radius: int | None = Field(None, description="Radio de curvatura de la interfaz")
    theme: str | None = Field(None, description="Tema de interfaz")
    language: str | None = Field(None, description="Idioma")
    font_size: int | None = Field(None, description="Tamaño de fuente")
    animations_enabled: bool | None = Field(None, description="Activar animaciones")
    compact_mode: bool | None = Field(None, description="Modo compacto")
    orb_animation: bool | None = Field(None, description="Animación del orb")
    send_mode: str | None = Field(None, description="Modo de envío")
    auto_scroll: bool | None = Field(None, description="Auto-scroll")
    show_timestamps: bool | None = Field(None, description="Mostrar timestamps")
    syntax_highlighting: bool | None = Field(None, description="Resaltado de sintaxis")
    custom_api_urls: dict[str, str] | None = Field(None, description="URLs personalizadas por proveedor")
    system_prompt: str | None = Field(None, description="Prompt de sistema personalizado")
    max_tool_calls: int | None = Field(None, description="Máximo tool calls")
    max_sessions: int | None = Field(None, description="Máximo de sesiones")
    context_size: int | None = Field(None, description="Tamaño de contexto")
    timeout: int | None = Field(None, description="Timeout de conexión")
    auto_save_interval: int | None = Field(None, description="Intervalo de auto-guardado")
    accent_color: str | None = Field(None, description="Color de acento de la interfaz")
    font_family: str | None = Field(None, description="Familia tipográfica")
    sidebar_visible: bool | None = Field(None, description="Visibilidad de la barra lateral")
    auto_title: bool | None = Field(None, description="Generar título automático de sesión")
    confirm_delete: bool | None = Field(None, description="Confirmar antes de eliminar sesión")


class OllamaModelsResponse(BaseModel):
    models: list[str] = Field(default_factory=list, description="Modelos de Ollama detectados")
    running: bool = Field(False, description="Si Ollama está corriendo")
