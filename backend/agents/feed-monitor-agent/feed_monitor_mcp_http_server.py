#!/usr/bin/env python3
"""
Feed Monitor Agent - Servidor MCP HTTP

Servidor MCP que proporciona herramientas para monitoreo de feeds RSS vía HTTP (FastAPI).
"""
import logging
import firebase_admin
import os
from firebase_admin import credentials, firestore
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from feed_utils import get_feed_id
from feed_tools import (
    add_feed_to_user_main,
    delete_feed_from_user_main,
    get_all_feeds_main,
    get_new_episodes_main,
    get_user_feeds_main,
    mark_episode_processed_main,
    validate_rss_feed_main
)

# --- Inicialización de Firebase Admin y Firestore ---
FIREBASE_KEY_PATH = os.environ.get('FIREBASE_KEY_PATH')
if not FIREBASE_KEY_PATH:
    # Ruta por defecto para desarrollo local
    FIREBASE_KEY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../devcontainer/serviceAccountKey.json'))
if not os.path.exists(FIREBASE_KEY_PATH):
    raise FileNotFoundError(f"No se encontró el archivo de credenciales de Firebase en: {FIREBASE_KEY_PATH}. Define la variable de entorno FIREBASE_KEY_PATH o coloca el archivo en la ruta por defecto.")
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Configuración de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("feed-monitor-mcp-http")


# --- FastAPI MCP HTTP Server ---

app = FastAPI(title="Feed Monitor MCP HTTP Agent")

# --- Middleware CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto por los dominios permitidos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOOLS = [
    {
        "name": "validateRssFeed",
        "description": "Valida si una URL es un RSS feed correcto. Devuelve is_valid, title, description y error si aplica.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feed_url": {"type": "string", "description": "URL del feed RSS a validar"}
            },
            "required": ["feed_url"]
        }
    },
    {
        "name": "get_user_feeds",
        "description": "Obtiene solo los feeds de un usuario, con la información personalizada de la subcolección feeds interna",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "ID del usuario"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "get_all_feeds",
        "description": "Obtiene la información de todos los feeds globales (colección feeds)",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_new_episodes",
        "description": "Obtiene nuevos episodios no procesados de todos los feeds (máximo 100)",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "add_feed_to_user",
        "description": "Añade un feed RSS a la lista de un usuario",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "ID del usuario (UID o email)"},
                "email": {"type": "string", "description": "Email del usuario (opcional, para guardar como campo)"},
                "feed_url": {"type": "string", "description": "URL del feed a añadir"},
                "custom_name": {"type": "string", "description": "Nombre personalizado del feed"},
                "active": {"type": "boolean", "description": "Si el feed está activo"}
            },
            "required": ["user_id", "feed_url"]
        }
    },
    {
        "name": "delete_feed_from_user",
        "description": "Elimina un feed RSS de la lista de un usuario",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "ID del usuario"},
                "feed_url": {"type": "string", "description": "URL del feed a eliminar"}
            },
            "required": ["user_id", "feed_url"]
        }
    },
    {
        "name": "mark_episode_processed",
        "description": "Marca un episodio como procesado en la subcolección processed_episodes de un feed, guardando metadatos y timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feed_id": {"type": "string", "description": "ID del feed"},
                "guid": {"type": "string", "description": "GUID del episodio"},
                "metadata": {"type": "object", "description": "Metadatos del episodio"}
            },
            "required": ["feed_id", "guid", "metadata"]
        }
    }
]

class CallToolRequest(BaseModel):
    name: str
    arguments: dict

@app.get("/list_tools")
async def list_tools():
    return TOOLS

@app.post("/call_tool")
async def call_tool(req: CallToolRequest):
    name = req.name
    arguments = req.arguments
    if name == "validateRssFeed":
        logger.info("Tool: validateRssFeed invocada")
        feed_url = arguments.get("feed_url")
        if not feed_url:
            return JSONResponse(content={"status": "error", "error": "feed_url es obligatoria"}, status_code=400)
        try:
            result = validate_rss_feed_main(feed_url)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en validateRssFeed: {e}")
            return JSONResponse(content={"is_valid": False, "error": str(e)}, status_code=500)
    elif name == "get_user_feeds":
        logger.info("Tool: get_user_feeds invocado")
        user_id = arguments.get("user_id")
        if not user_id:
            return JSONResponse(content={"status": "error", "error": "user_id es obligatorio"}, status_code=400)
        try:
            result = get_user_feeds_main(db, user_id)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en get_user_feeds: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    elif name == "get_all_feeds":
        logger.info("Tool: get_all_feeds invocado")
        try:
            result = get_all_feeds_main(db)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en get_all_feeds: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    elif name == "get_new_episodes":
        logger.info("Tool: get_new_episodes invocado")
        try:
            result = get_new_episodes_main(db)
            logger.info(f"get_new_episodes: {result['total_episodes']} episodios devueltos")
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en get_new_episodes: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    elif name == "add_feed_to_user":
        logger.info("Tool: add_feed_to_user invocada")
        user_id = arguments.get("user_id")
        feed_url = arguments.get("feed_url")
        custom_name = arguments.get("custom_name", "")
        active = arguments.get("active", True)
        if not user_id or not feed_url:
            return JSONResponse(content={"status": "error", "error": "user_id y feed_url son obligatorios"}, status_code=400)
        try:
            email = arguments.get("email")
            result = add_feed_to_user_main(db, user_id, feed_url, custom_name, active, email=email)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en add_feed_to_user: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    elif name == "delete_feed_from_user":
        logger.info("Tool: delete_feed_from_user invocada")
        user_id = arguments.get("user_id")
        feed_url = arguments.get("feed_url")
        if not user_id or not feed_url:
            return JSONResponse(content={"status": "error", "error": "user_id y feed_url son obligatorios"}, status_code=400)
        try:
            result = delete_feed_from_user_main(db, user_id, feed_url)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en delete_feed_from_user: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    elif name == "mark_episode_processed":
        logger.info("Tool: mark_episode_processed invocada")
        feed_id = arguments.get("feed_id")
        guid = arguments.get("guid")
        metadata = arguments.get("metadata")
        if not feed_id or not guid or metadata is None:
            return JSONResponse(content={"status": "error", "error": "feed_id, guid y metadata son obligatorios"}, status_code=400)
        try:
            result = mark_episode_processed_main(db, feed_id, guid, metadata)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en mark_episode_processed: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    else:
        return JSONResponse(content={"error": f"Unknown tool: {name}"}, status_code=400)

if __name__ == "__main__":
    uvicorn.run("feed_monitor_mcp_http_server:app", host="0.0.0.0", port=8000, reload=True)
