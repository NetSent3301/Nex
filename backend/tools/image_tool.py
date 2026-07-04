import base64
import os
from pathlib import Path
from typing import Any

from tools.tool import Tool
from tools.errors import ToolError, validate_path_safety


class ReadImageTool(Tool):
    name = "read_image"
    description = "Read and describe an image file from the workspace. Returns a base64-encoded representation that can be sent to vision-capable AI models."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the image file from the workspace root.",
                },
                "prompt": {
                    "type": "string",
                    "description": "Optional specific question or instruction about the image (e.g. 'Describe this image', 'Read the text in this image').",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path: str = kwargs["path"]
        prompt: str = kwargs.get("prompt", "")
        workspace: str = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Image not found: {path}")
        if not safe_path.is_file():
            raise ToolError(f"Not a file: {path}")

        ext = safe_path.suffix.lower()
        supported = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        if ext not in supported:
            raise ToolError(
                f"Unsupported image format '{ext}'. Supported: {', '.join(supported)}"
            )

        try:
            img_data = safe_path.read_bytes()
            mime_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".bmp": "image/bmp",
            }.get(ext, "application/octet-stream")

            b64 = base64.b64encode(img_data).decode("utf-8")
            size_kb = len(img_data) / 1024

            if size_kb > 20480:
                raise ToolError(f"Image too large ({size_kb:.0f} KB). Maximum: 20 MB.")

            result = {
                "success": True,
                "path": path,
                "mime_type": mime_type,
                "size_kb": round(size_kb, 1),
                "width": None,
                "height": None,
                "image_data": b64,
                "data_uri": f"data:{mime_type};base64,{b64[:50]}...[truncated]",
            }

            try:
                from PIL import Image
                import io
                with Image.open(io.BytesIO(img_data)) as img:
                    result["width"], result["height"] = img.size
                    result["format"] = img.format
            except ImportError:
                pass

            return result

        except PermissionError:
            raise ToolError(f"Permission denied: {path}")
        except OSError as e:
            raise ToolError(f"Failed to read image: {e}")


class ImageInfoTool(Tool):
    name = "image_info"
    description = "Get metadata about an image file (dimensions, format, size) without reading its full contents."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the image file from the workspace root.",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path: str = kwargs["path"]
        workspace: str = kwargs.get("workspace_root", os.getcwd())

        safe_path = Path(validate_path_safety(path, workspace))

        if not safe_path.exists():
            raise ToolError(f"Image not found: {path}")

        img_data = safe_path.read_bytes()
        ext = safe_path.suffix.lower()
        size_kb = len(img_data) / 1024
        result = {
            "success": True,
            "path": path,
            "size_kb": round(size_kb, 1),
            "format": ext.lstrip("."),
        }

        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(img_data)) as img:
                result["width"], result["height"] = img.size
                result["format"] = img.format or ext.lstrip(".")
                result["mode"] = img.mode
        except ImportError:
            pass

        return result
