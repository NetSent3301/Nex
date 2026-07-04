from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="El mensaje o instrucción del usuario")
    session_id: str = Field(..., description="Identificador único de la sesión de chat")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Respuesta generada por Nex después del ciclo autónomo")


class MetricsResponse(BaseModel):
    memory: float = Field(..., description="Porcentaje de uso de memoria RAM")
    context_buffer: float = Field(..., description="Porcentaje de uso del buffer de contexto")
    agent_status: str = Field(..., description="Estado del agente: online, busy, offline")
    cpu: float = Field(..., description="Porcentaje de uso de CPU")


class WorkspaceResponse(BaseModel):
    path: str = Field(..., description="Ruta del workspace activo")
