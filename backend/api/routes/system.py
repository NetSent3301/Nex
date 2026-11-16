"""Rutas de sistema: UI web, salud, métricas, Ollama, subida y limpieza."""
import base64
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.schemas import MetricsResponse, OllamaModelsResponse

router = APIRouter()

WEB_INDEX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "web",
    "index.html",
)

MAX_IMAGE_SIZE = 20 * 1024 * 1024


@router.get("/")
async def web_ui() -> FileResponse:
    return FileResponse(WEB_INDEX)


@router.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "agent": "Nex"}


@router.get("/api/v1/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    memory_pct = 0.0
    cpu_pct = 0.0

    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
            mem_total = int(lines[0].split()[1])
            mem_avail = int(lines[2].split()[1])
            memory_pct = round((1 - mem_avail / mem_total) * 100, 1)
    except Exception:
        memory_pct = 0.0

    try:
        import time

        prev_idle = prev_total = 0
        with open("/proc/stat") as f:
            fields = f.readline().split()
            prev_idle = int(fields[4])
            prev_total = sum(int(v) for v in fields[1:])
        time.sleep(0.1)
        with open("/proc/stat") as f:
            fields = f.readline().split()
            idle = int(fields[4])
            total = sum(int(v) for v in fields[1:])
        delta_idle = idle - prev_idle
        delta_total = total - prev_total
        cpu_pct = round((1 - delta_idle / delta_total) * 100, 1) if delta_total else 0.0
    except Exception:
        cpu_pct = 0.0

    return MetricsResponse(
        memory=memory_pct,
        context_buffer=max(0, min(100, memory_pct * 0.6)),
        agent_status="online",
        cpu=cpu_pct,
    )


@router.get("/api/v1/ollama/models", response_model=OllamaModelsResponse)
async def get_ollama_models() -> OllamaModelsResponse:
    from llm.ollama_provider import detect_ollama_models, is_ollama_running

    return OllamaModelsResponse(
        models=detect_ollama_models(),
        running=is_ollama_running(),
    )


@router.post("/api/v1/upload/image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    contents = await file.read()

    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 20 MB)")

    b64 = base64.b64encode(contents).decode("utf-8")

    return {
        "success": True,
        "filename": file.filename,
        "mime_type": file.content_type,
        "size_kb": round(len(contents) / 1024, 1),
        "image_data": b64,
    }


@router.post("/api/v1/clear-history")
async def clear_all_history() -> dict:
    import glob as g

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.normpath(os.path.join(base, "data"))
    if not data_dir.startswith(base):
        raise HTTPException(status_code=403, detail="Invalid path")
    pattern = os.path.join(data_dir, "*.json")
    deleted = 0
    for f in g.glob(pattern):
        f = os.path.normpath(f)
        if not f.startswith(data_dir):
            continue
        if "settings" not in f:
            os.remove(f)
            deleted += 1
    return {"success": True, "deleted": deleted}