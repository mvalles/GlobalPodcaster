#!/usr/bin/env python3
"""
Feed Monitor Agent - Servidor MCP HTTP

Servidor MCP que proporciona herramientas para monitoreo de feeds RSS vía HTTP (FastAPI).
"""
import json
import os
import hashlib
import time
import logging
import feedparser
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
# --- Configuración de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("feed-monitor-mcp-http")

# --- Utilidades y lógica de negocio (copiado de feed_monitor_mcp_server) ---
FEEDS_FILE = "feeds.txt"
STATE_DIR = "feed_monitor_state"

def get_feeds_file_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    feeds_path = os.path.join(script_dir, "..", "..", FEEDS_FILE)
    return os.path.abspath(feeds_path)

def get_state_dir() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    state_path = os.path.join(script_dir, STATE_DIR)
    return state_path

def get_feeds() -> List[str]:
    feeds_path = get_feeds_file_path()
    if not os.path.exists(feeds_path):
        logger.warning(f"Archivo de feeds no encontrado en {feeds_path}. No se cargan feeds.")
        return []
    feeds = []
    with open(feeds_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Leer metadatos del feed
                feed_url = line
                try:
                    feed = feedparser.parse(feed_url)
                    owner_email = (
                        feed.feed.get('managingeditor') or
                        feed.feed.get('author') or
                        (feed.feed.get('itunes_owner', {}).get('email') if 'itunes_owner' in feed.feed else None)
                    )
                    feeds.append({
                        'feed_url': feed_url,
                        'owner_email': owner_email or '',
                        'feed_title': feed.feed.get('title', ''),
                    })
                except Exception as e:
                    logger.warning(f"No se pudo leer metadatos de {feed_url}: {e}")
                    feeds.append({'feed_url': feed_url, 'owner_email': '', 'feed_title': ''})
    logger.info(f"Feeds cargados: {[f['feed_url'] for f in feeds]}")
    return feeds

def get_feed_id(feed_url: str) -> str:
    return hashlib.md5(feed_url.encode()).hexdigest()[:12]

def load_last_check(feed_id: str) -> Dict[str, Any]:
    state_dir = get_state_dir()
    last_check_file = os.path.join(state_dir, f"last_check_{feed_id}.json")
    if os.path.exists(last_check_file):
        try:
            with open(last_check_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"episodes": [], "last_check": 0}

def save_last_check(feed_id: str, episodes: List[str], timestamp: float):
    state_dir = get_state_dir()
    os.makedirs(state_dir, exist_ok=True)
    last_check_file = os.path.join(state_dir, f"last_check_{feed_id}.json")
    data = {
        "episodes": episodes,
        "last_check": timestamp
    }
    try:
        with open(last_check_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Guardado estado de feed {feed_id} con {len(episodes)} episodios procesados.")
    except IOError as e:
        logger.error(f"Error saving last check: {e}")

def check_feed_for_new_episodes(feed_url: str) -> List[Dict[str, Any]]:
    try:
        logger.info(f"Verificando feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            logger.warning(f"Feed bozo detectado en {feed_url}")
            return []
        feed_id = get_feed_id(feed_url)
        last_check_data = load_last_check(feed_id)
        # Usar list comprehension para construir current_episodes y current_guids
        entries = [
            {
                'guid': entry.get('id', entry.get('link', '')),
                'title': entry.get('title', 'No Title'),
                'description': entry.get('summary', ''),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'feed_title': feed.feed.get('title', 'Unknown Feed')
            }
            for entry in feed.entries
            if entry.get('id', entry.get('link', ''))
        ]
        current_guids = set(ep['guid'] for ep in entries)
        previous_guids = set(last_check_data.get('episodes', []))
        new_guids = current_guids - previous_guids
        new_episodes = [
            {**ep, 'feed_url': feed_url, 'feed_id': feed_id}
            for ep in entries if ep['guid'] in new_guids
        ]
        logger.info(f"Nuevos episodios detectados en {feed_url}: {len(new_episodes)}")
        return new_episodes
    except Exception as e:
        logger.error(f"Error checking feed {feed_url}: {e}")
        return []

# --- FastAPI MCP HTTP Server ---
app = FastAPI(title="Feed Monitor MCP HTTP Agent")

TOOLS = [
    {
        "name": "get_feed_list",
        "description": "Obtiene la lista de feeds RSS configurados",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_new_episodes",
        "description": "Obtiene nuevos episodios con paginación para evitar respuestas grandes",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Número de página (empezando en 1)",
                    "default": 1
                },
                "per_page": {
                    "type": "integer",
                    "description": "Episodios por página (máximo 50)",
                    "default": 20
                }
            },
            "required": []
        }
    },
    {
        "name": "mark_episodes_processed",
        "description": "Marca episodios específicos como procesados después de completar el pipeline TTS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "episodes": {
                    "type": "array",
                    "description": "Lista de episodios procesados con guid, feed_url y feed_id",
                    "items": {
                        "type": "object",
                        "properties": {
                            "guid": {"type": "string"},
                            "feed_url": {"type": "string"},
                            "feed_id": {"type": "string"}
                        },
                        "required": ["guid", "feed_url", "feed_id"]
                    }
                }
            },
            "required": ["episodes"]
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
    if name == "get_feed_list":
        logger.info("Tool: get_feed_list invocado")
        try:
            feeds = get_feeds()
            result = {
                "status": "success",
                "feeds": feeds,
                "count": len(feeds)
            }
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en get_feed_list: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    elif name == "get_new_episodes":
        logger.info("Tool: get_new_episodes invocado")
        page = arguments.get("page", 1)
        per_page = min(arguments.get("per_page", 20), 50)
        try:
            feeds = get_feeds()
            all_new_episodes = []
            for feed in feeds:
                feed_url = feed['feed_url']
                owner_email = feed.get('owner_email', '')
                feed_title = feed.get('feed_title', '')
                new_episodes = check_feed_for_new_episodes(feed_url)
                # Añadir metadatos de feed a cada episodio
                for ep in new_episodes:
                    ep['owner_email'] = owner_email
                    ep['feed_title'] = feed_title
                all_new_episodes.extend(new_episodes)
            total_episodes = len(all_new_episodes)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_episodes = all_new_episodes[start_idx:end_idx]
            total_pages = (total_episodes + per_page - 1) // per_page
            result = {
                "status": "success",
                "page": page,
                "per_page": per_page,
                "total_episodes": total_episodes,
                "total_pages": total_pages,
                "episodes": page_episodes
            }
            logger.info(f"get_new_episodes: {len(page_episodes)} episodios en la página {page}")
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en get_new_episodes: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    elif name == "mark_episodes_processed":
        logger.info("Tool: mark_episodes_processed invocado")
        episodes = arguments.get("episodes", [])
        if not episodes:
            logger.warning("mark_episodes_processed llamado sin episodios")
            return JSONResponse(content={"error": "episodes list is required"}, status_code=400)
        try:
            episodes_by_feed = {}
            for ep in episodes:
                feed_id = ep.get("feed_id")
                if feed_id:
                    if feed_id not in episodes_by_feed:
                        episodes_by_feed[feed_id] = []
                    episodes_by_feed[feed_id].append(ep["guid"])
            processed_count = 0
            for feed_id, guids in episodes_by_feed.items():
                last_check_data = load_last_check(feed_id)
                current_episodes = set(last_check_data.get('episodes', []))
                current_episodes.update(guids)
                current_time = time.time()
                save_last_check(feed_id, list(current_episodes), current_time)
                processed_count += len(guids)
            result = {
                "status": "success",
                "processed_episodes": processed_count,
                "feeds_updated": len(episodes_by_feed)
            }
            logger.info(f"Episodios marcados como procesados: {processed_count}")
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Error en mark_episodes_processed: {e}")
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    else:
        return JSONResponse(content={"error": f"Unknown tool: {name}"}, status_code=400)

if __name__ == "__main__":
    uvicorn.run("feed_monitor_mcp_http_server:app", host="0.0.0.0", port=8000, reload=True)
