#!/usr/bin/env python3
"""
Feed Monitor Agent - Servidor MCP Completo

Servidor MCP que proporciona herramientas para monitoreo de feeds RSS.
Compatible con Coral Protocol Server y estándares MCP.

Tools disponibles:
- check_feeds: Verifica todos los feeds configurados
- check_feed: Verifica un feed específico  
- get_feed_list: Lista todos los feeds configurados
- get_feed_stats: Obtiene estadísticas de un feed

Autor: GlobalPodcaster Team
"""

import asyncio
import json
import os
import sys
import hashlib
import time
import feedparser
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Configuración
FEEDS_FILE = "feeds.txt"
STATE_DIR = "feed_monitor_state"

def get_feeds_file_path() -> str:
    """Obtiene la ruta absoluta del archivo de feeds."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    feeds_path = os.path.join(script_dir, "..", "..", FEEDS_FILE)
    return os.path.abspath(feeds_path)

def get_state_dir() -> str:
    """Obtiene el directorio para almacenar el estado del monitor."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    state_path = os.path.join(script_dir, STATE_DIR)
    # El directorio se creará solo cuando se guarde un archivo
    return state_path

def get_feeds() -> List[str]:
    """Lee los feeds desde el archivo feeds.txt."""
    feeds_path = get_feeds_file_path()
    if not os.path.exists(feeds_path):
        # Crear archivo con feeds de ejemplo si no existe
        with open(feeds_path, 'w') as f:
            f.write("# Feeds RSS para monitorear\n")
            f.write("https://feeds.feedburner.com/oreilly/radar\n")
            f.write("https://rss.cnn.com/rss/edition.rss\n")
        return []
    
    feeds = []
    with open(feeds_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                feeds.append(line)
    
    return feeds

def get_feed_id(feed_url: str) -> str:
    """Genera un ID único para un feed basado en su URL."""
    return hashlib.md5(feed_url.encode()).hexdigest()[:12]

def load_last_check(feed_id: str) -> Dict[str, Any]:
    """Carga información del último check de un feed."""
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
    """Guarda información del último check de un feed."""
    state_dir = get_state_dir()
    # Crear directorio solo cuando vayamos a guardar el archivo
    os.makedirs(state_dir, exist_ok=True)
    last_check_file = os.path.join(state_dir, f"last_check_{feed_id}.json")
    
    data = {
        "episodes": episodes,
        "last_check": timestamp
    }
    
    try:
        with open(last_check_file, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving last check: {e}", file=sys.stderr)

def check_feed_for_new_episodes(feed_url: str) -> List[Dict[str, Any]]:
    """Verifica un feed RSS en busca de nuevos episodios."""
    try:
        print(f"Checking feed: {feed_url}", file=sys.stderr)
        
        # Parsear el feed
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            return []
        
        feed_id = get_feed_id(feed_url)
        last_check_data = load_last_check(feed_id)
        
        # Extraer episodios actuales
        current_episodes = []
        current_guids = set()
        
        for entry in feed.entries:
            guid = entry.get('id', entry.get('link', ''))
            if guid:
                current_guids.add(guid)
                episode = {
                    'guid': guid,
                    'title': entry.get('title', 'No Title'),
                    'description': entry.get('summary', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'feed_title': feed.feed.get('title', 'Unknown Feed')
                }
                current_episodes.append(episode)
        
        # Comparar con episodios previos
        previous_guids = set(last_check_data.get('episodes', []))
        new_guids = current_guids - previous_guids
        new_episodes = [ep for ep in current_episodes if ep['guid'] in new_guids]
        
        # NO guardamos estado automáticamente - solo detectamos nuevos episodios
        # El estado se guardará explícitamente después del procesamiento exitoso
        
        # Agregar metadata del feed
        for episode in new_episodes:
            episode['feed_url'] = feed_url
            episode['feed_id'] = feed_id
        
        return new_episodes
        
    except Exception as e:
        print(f"Error checking feed {feed_url}: {e}", file=sys.stderr)
        return []

# Crear servidor MCP
server = Server("feed-monitor-agent")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista las herramientas disponibles del feed monitor."""
    return [
        Tool(
            name="check_feeds",
            description="Verifica todos los feeds RSS configurados en busca de nuevos episodios",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="check_feed",
            description="Verifica un feed RSS específico en busca de nuevos episodios", 
            inputSchema={
                "type": "object",
                "properties": {
                    "feed_url": {
                        "type": "string",
                        "description": "URL del feed RSS a verificar"
                    }
                },
                "required": ["feed_url"]
            }
        ),
        Tool(
            name="get_feed_list",
            description="Obtiene la lista de feeds RSS configurados",
            inputSchema={
                "type": "object", 
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_feed_stats",
            description="Obtiene estadísticas de un feed específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "feed_url": {
                        "type": "string",
                        "description": "URL del feed RSS"
                    }
                },
                "required": ["feed_url"]
            }
        ),
        Tool(
            name="get_new_episodes",
            description="Obtiene nuevos episodios con paginación para evitar respuestas grandes",
            inputSchema={
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
        ),
        Tool(
            name="mark_episodes_processed",
            description="Marca episodios específicos como procesados después de completar el pipeline TTS",
            inputSchema={
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
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Maneja las llamadas a herramientas del feed monitor."""
    
    if name == "check_feeds":
        # Verificar todos los feeds configurados
        try:
            feeds = get_feeds()
            all_new_episodes = []
            
            for feed_url in feeds:
                new_episodes = check_feed_for_new_episodes(feed_url)
                all_new_episodes.extend(new_episodes)
            
            result = {
                "status": "success",
                "feeds_checked": len(feeds),
                "new_episodes_found": len(all_new_episodes),
                "episodes": []  # check_feeds solo retorna estadísticas, no episodios completos
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "status": "error", 
                "error": str(e)
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "check_feed":
        # Verificar un feed específico
        feed_url = arguments.get("feed_url")
        if not feed_url:
            return [TextContent(type="text", text=json.dumps({"error": "feed_url is required"}))]
        
        try:
            new_episodes = check_feed_for_new_episodes(feed_url)
            result = {
                "status": "success",
                "feed_url": feed_url,
                "new_episodes_found": len(new_episodes),
                "episodes": new_episodes
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "status": "error",
                "feed_url": feed_url,
                "error": str(e)
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "get_feed_list":
        # Obtener lista de feeds
        try:
            feeds = get_feeds()
            result = {
                "status": "success",
                "feeds": feeds,
                "count": len(feeds)
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e)
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "get_feed_stats":
        # Obtener estadísticas de un feed
        feed_url = arguments.get("feed_url")
        if not feed_url:
            return [TextContent(type="text", text=json.dumps({"error": "feed_url is required"}))]
        
        try:
            feed_id = get_feed_id(feed_url)
            last_check_data = load_last_check(feed_id)
            
            result = {
                "status": "success",
                "feed_url": feed_url,
                "feed_id": feed_id,
                "episodes_tracked": len(last_check_data.get('episodes', [])),
                "last_check": last_check_data.get('last_check', 0)
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "status": "error",
                "feed_url": feed_url,
                "error": str(e)
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "get_new_episodes":
        # Obtener nuevos episodios con paginación
        page = arguments.get("page", 1)
        per_page = min(arguments.get("per_page", 20), 50)  # Máximo 50 por página
        
        try:
            feeds = get_feeds()
            all_new_episodes = []
            
            for feed_url in feeds:
                new_episodes = check_feed_for_new_episodes(feed_url)
                all_new_episodes.extend(new_episodes)
            
            # Calcular paginación
            total_episodes = len(all_new_episodes)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_episodes = all_new_episodes[start_idx:end_idx]
            
            total_pages = (total_episodes + per_page - 1) // per_page  # Redondear hacia arriba
            
            result = {
                "status": "success",
                "page": page,
                "per_page": per_page,
                "total_episodes": total_episodes,
                "total_pages": total_pages,
                "episodes": page_episodes
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e)
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "mark_episodes_processed":
        # Marcar episodios como procesados
        episodes = arguments.get("episodes", [])
        if not episodes:
            return [TextContent(type="text", text=json.dumps({"error": "episodes list is required"}))]
        
        try:
            # Agrupar episodios por feed_id
            episodes_by_feed = {}
            for ep in episodes:
                feed_id = ep.get("feed_id")
                if feed_id:
                    if feed_id not in episodes_by_feed:
                        episodes_by_feed[feed_id] = []
                    episodes_by_feed[feed_id].append(ep["guid"])
            
            # Actualizar estado para cada feed
            processed_count = 0
            for feed_id, guids in episodes_by_feed.items():
                # Cargar estado actual
                last_check_data = load_last_check(feed_id)
                current_episodes = set(last_check_data.get('episodes', []))
                
                # Agregar nuevos episodios procesados
                current_episodes.update(guids)
                
                # Guardar estado actualizado
                current_time = time.time()
                save_last_check(feed_id, list(current_episodes), current_time)
                processed_count += len(guids)
            
            result = {
                "status": "success",
                "processed_episodes": processed_count,
                "feeds_updated": len(episodes_by_feed)
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e)
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

async def main():
    """Función principal del servidor MCP."""
    # Configuración de logging para stderr
    async with AsyncExitStack() as exit_stack:
        read_stream, write_stream = await exit_stack.enter_async_context(stdio_server())
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="feed-monitor-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())