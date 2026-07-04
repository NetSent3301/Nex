# backend/main.py
import asyncio
import os

import typer

from llm.gemini import GeminiProvider, system_prompt  # Importamos tu system_prompt estructurado
from storage.memory import MAX_HISTORY_MESSAGES, load_chat_history, save_chat_history, trim_messages
from storage.settings import get_workspace_path, save_workspace_path
from tools.registry import create_default_registry

app = typer.Typer(name="Nex", help="Nex - The best personal AI assistant for you!!.")

@app.command(name="chat")
def chat_with_nex(
    message: str = typer.Argument(..., help="La instrucción o pregunta para Nex")
):
    """
    Comando de chat inteligente capaz de ejecutar herramientas en el Workspace.
    """
    asyncio.run(run_chat_agent(message))
# backend/main.py

async def run_chat_agent(message: str):

    workspace_root = get_workspace_path()
    if not workspace_root:
        typer.secho("❌ Error: No hay un Workspace activo. Configúralo primero con: set-workspace <ruta>", fg=typer.colors.RED, bold=True)
        return

    typer.echo("🤖 [Nex] Pensando...")

    try:
        provider = GeminiProvider()
        registry = create_default_registry()
        tools_metadata = registry.get_all_tools_metadata()

        from google.genai import types

        # ── CARGAR HISTORIAL PERSISTENTE ────────────────────────
        historial_previo = load_chat_history("cli")
        historial_previo = trim_messages(historial_previo, MAX_HISTORY_MESSAGES)
        chat_history = historial_previo + [
            types.Content(role="user", parts=[types.Part.from_text(text=message)])
        ]

        if historial_previo:
            typer.echo(f"📜 {len(historial_previo)} mensajes del historial recuperados")

        # Configuración estricta para el agente
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=tools_metadata,
            temperature=0.2
        )

        # BUCLE AUTÓNOMO MULTI-PASO
        MAX_ITERATIONS = 10

        for iteration in range(MAX_ITERATIONS):
            response = provider.generate_content(
                contents=chat_history,
                config=config,
            )

            if not response.function_calls:
                typer.echo("\n🤖 [Nex Core]:")
                typer.secho(response.text, fg=typer.colors.GREEN)
                chat_history.append(response.candidates[0].content)
                save_chat_history(chat_history, "cli")
                return

            chat_history.append(response.candidates[0].content)

            for call in response.function_calls:
                tool_name = call.name
                tool_args = dict(call.args)
                tool_args["workspace_root"] = workspace_root

                typer.secho(f"🛠️ [Agente] Ejecutando herramienta: {tool_name}...", fg=typer.colors.YELLOW)

                tool = registry.get(tool_name)
                try:
                    tool_result = tool.execute(**tool_args)
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}

                typer.echo("🤖 [Nex] Analizando resultado de la acción...")

                chat_history.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(name=tool_name, response=tool_result)]
                    )
                )

        typer.secho("⚠️  Límite de iteraciones alcanzado. Intenta con una instrucción más simple.", fg=typer.colors.RED)
        save_chat_history(chat_history, "cli")

    except Exception as e:
        typer.secho(f"❌ Ocurrió un error en el bucle del Agente: {e}", fg=typer.colors.RED)

@app.command(name="version", help="Show the version of the application.")
def version():
    typer.echo("Nex version 1.0.0")


@app.command(name="set-workspace", help="Set your workspace configuration.")
def workspace(path: str = typer.Argument(..., help="The path to your workspace configuration file.")):
    if not os.path.exists(path):
        typer.secho(f"Error: The specified path '{path}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not os.path.isdir(path):
        typer.secho(f"Error: The specified path '{path}' is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    absolute_path = save_workspace_path(path)
    typer.secho(f"Workspace path set to: {absolute_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
