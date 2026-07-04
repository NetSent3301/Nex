from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="El mensaje o instrucción del usuario")
    session_id: str = Field(..., description="Identificador único de la sesión de chat")
    image_data: str | None = Field(None, description="Imagen en base64 para análisis visual")
    image_mime: str | None = Field(None, description="Tipo MIME de la imagen (e.g. image/png)")
    provider: str | None = Field(None, description="Proveedor LLM a usar (gemini, openai, ollama, etc.)")
    model: str | None = Field(None, description="Modelo específico a usar")


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
    send_mode: str = Field("enter", description="Modo de envío: enter, ctrl_enter")
    auto_scroll: bool = Field(True, description="Auto-scroll en nuevos mensajes")
    show_timestamps: bool = Field(False, description="Mostrar marcas de tiempo")
    syntax_highlighting: bool = Field(True, description="Resaltado de sintaxis")
    custom_api_urls: dict[str, str] = Field(default_factory=dict, description="URLs personalizadas por proveedor")
    system_prompt: str = Field("", description="Prompt de sistema personalizado")
    max_tool_calls: int = Field(10, description="Máximo de llamadas a herramientas por ciclo")
    auto_save_interval: int = Field(60, description="Intervalo de auto-guardado en segundos")


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
    send_mode: str | None = Field(None, description="Modo de envío")
    auto_scroll: bool | None = Field(None, description="Auto-scroll")
    show_timestamps: bool | None = Field(None, description="Mostrar timestamps")
    syntax_highlighting: bool | None = Field(None, description="Resaltado de sintaxis")
    custom_api_urls: dict[str, str] | None = Field(None, description="URLs personalizadas por proveedor")
    system_prompt: str | None = Field(None, description="Prompt de sistema personalizado")
    max_tool_calls: int | None = Field(None, description="Máximo tool calls")
    auto_save_interval: int | None = Field(None, description="Intervalo de auto-guardado")


class OllamaModelsResponse(BaseModel):
    models: list[str] = Field(default_factory=list, description="Modelos de Ollama detectados")
    running: bool = Field(False, description="Si Ollama está corriendo")
