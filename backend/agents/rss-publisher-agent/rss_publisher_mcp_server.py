#!/usr/bin/env python3
"""
RSS Publisher Agent - MCP Server

Agent 5: RSS-Publisher-Agent
Purpose: Publishes final translated episodes to RSS feeds
Trigger: Receives job from TTS-Agent via Coral
Input: {"new_audio_url": "...", "translated_title": "...", "language": "es", "episode_id": "..."}
Process:
1. Fetches appropriate translated RSS feed file (e.g., user123_es.xml) from storage
2. Adds new <item> entry with translated title, description, and audio URL  
3. Saves updated XML file
4. Validates RSS structure
Output: Updated RSS feed ready for distribution

Autor: GlobalPodcaster Team
"""

import asyncio
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextlib import AsyncExitStack
import aiofiles
from pathlib import Path

from dotenv import load_dotenv
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

# Cargar variables de entorno
load_dotenv("/workspaces/GlobalPodcaster/devcontainer/.env")

def log_debug(message: str):
    """Log debug messages to stderr"""
    print(f"[DEBUG rss-publisher] {message}", file=sys.stderr, flush=True)

# Configuración
# Usar path absoluto para storage para evitar crear directorios en lugares incorrectos
RSS_STORAGE_DIR = os.getenv("RSS_STORAGE_DIR", os.path.join(os.path.dirname(__file__), "storage"))
RSS_BASE_URL = os.getenv("RSS_BASE_URL", "http://localhost:8080/feeds")
AUDIO_BASE_URL = os.getenv("STORAGE_BASE_URL", "http://localhost:8080/media")

# Los directorios de feeds RSS y episodios completados se crearán solo cuando se guarde un archivo
COMPLETED_EPISODES_DIR = "../feed-monitor-agent/feed_monitor_state"

def sanitize_filename(name: str) -> str:
    """Sanitiza nombres para archivos seguros."""
    return "".join(c for c in name if c.isalnum() or c in ('-', '_')).lower()

def create_rss_feed_template(title: str, description: str, language: str = "es") -> str:
    """Crea plantilla base para feed RSS."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
    <channel>
        <title>{title}</title>
        <description>{description}</description>
        <language>{language}</language>
        <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>
        <generator>GlobalPodcaster v1.0</generator>
        <itunes:author>GlobalPodcaster</itunes:author>
        <itunes:category text="Technology"/>
    </channel>
</rss>"""

async def get_or_create_rss_feed(user_id: str, language: str, title: str = None, description: str = None) -> str:
    """Obtiene o crea un feed RSS para usuario y idioma específicos."""
    try:
        feed_filename = f"{sanitize_filename(user_id)}_{language}.xml"
        feed_path = os.path.join(RSS_STORAGE_DIR, feed_filename)
        
        if os.path.exists(feed_path):
            log_debug(f"RSS feed exists: {feed_path}")
            return feed_path
        else:
            # Crear directorio solo cuando vayamos a crear el feed
            os.makedirs(RSS_STORAGE_DIR, exist_ok=True)
            
            # Crear nuevo feed
            default_title = title or f"GlobalPodcaster - {user_id.title()} ({language.upper()})"
            default_desc = description or f"Podcast traducido automáticamente a {language} por GlobalPodcaster"
            
            rss_content = create_rss_feed_template(default_title, default_desc, language)
            
            async with aiofiles.open(feed_path, "w", encoding="utf-8") as f:
                await f.write(rss_content)
            
            log_debug(f"Created new RSS feed: {feed_path}")
            return feed_path
            
    except Exception as e:
        log_debug(f"Error managing RSS feed: {e}")
        raise

async def add_episode_to_rss(feed_path: str, episode_data: Dict[str, Any]) -> Dict[str, Any]:
    """Añade un nuevo episodio al feed RSS."""
    try:
        # Leer feed existente
        async with aiofiles.open(feed_path, "r", encoding="utf-8") as f:
            rss_content = await f.read()
        
        # Parsear XML
        root = ET.fromstring(rss_content)
        channel = root.find("channel")
        
        if channel is None:
            return {"success": False, "error": "Invalid RSS structure - no channel found"}
        
        # Crear nuevo item
        item = ET.SubElement(channel, "item")
        
        # Datos del episodio
        title_elem = ET.SubElement(item, "title")
        title_elem.text = episode_data.get("translated_title", "Untitled Episode")
        
        desc_elem = ET.SubElement(item, "description")
        desc_elem.text = episode_data.get("translated_description", "No description available")
        
        # URL del audio
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", episode_data["new_audio_url"])
        enclosure.set("type", "audio/mpeg")
        enclosure.set("length", str(episode_data.get("audio_size", 0)))
        
        # GUID único
        guid_elem = ET.SubElement(item, "guid")
        guid_elem.text = f"globalpodcaster_{episode_data['episode_id']}_{episode_data.get('language', 'es')}"
        guid_elem.set("isPermaLink", "false")
        
        # Fecha de publicación
        pub_date = ET.SubElement(item, "pubDate")
        pub_date.text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # iTunes tags
        itunes_duration = ET.SubElement(item, "itunes:duration")
        itunes_duration.text = episode_data.get("duration", "00:00:00")
        
        # Actualizar lastBuildDate del channel
        last_build = channel.find("lastBuildDate")
        if last_build is not None:
            last_build.text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Guardar RSS actualizado
        updated_rss = ET.tostring(root, encoding="unicode", xml_declaration=True)
        
        # Formatear XML (básico)
        formatted_rss = updated_rss.replace('><', '>\n<')
        
        async with aiofiles.open(feed_path, "w", encoding="utf-8") as f:
            await f.write(formatted_rss)
        
        # URL pública del feed
        feed_filename = os.path.basename(feed_path)
        public_feed_url = f"{RSS_BASE_URL}/{feed_filename}"
        
        log_debug(f"Episode added to RSS: {feed_path}")
        
        # Marcar episodio como completado para este idioma
        episode_id = episode_data.get("episode_id")
        language = episode_data.get("language")
        if episode_id:
            completion_result = await mark_episode_completed(episode_id, language)
            log_debug(f"Episode completion marked: {completion_result.get('success', False)}")
        
        return {
            "success": True,
            "feed_path": feed_path,
            "public_feed_url": public_feed_url,
            "episode_guid": guid_elem.text,
            "episodes_count": len(channel.findall("item")),
            "last_updated": pub_date.text,
            "episode_completed": completion_result.get("success", False) if episode_id else False
        }
        
    except ET.ParseError as e:
        return {"success": False, "error": f"XML parsing error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"RSS update error: {str(e)}"}

async def validate_rss_feed(feed_path: str) -> Dict[str, Any]:
    """Valida la estructura de un feed RSS."""
    try:
        async with aiofiles.open(feed_path, "r", encoding="utf-8") as f:
            content = await f.read()
        
        root = ET.fromstring(content)
        
        # Validaciones básicas
        if root.tag != "rss":
            return {"valid": False, "error": "Root element is not 'rss'"}
        
        channel = root.find("channel")
        if channel is None:
            return {"valid": False, "error": "No 'channel' element found"}
        
        required_elements = ["title", "description", "language"]
        missing = []
        
        for elem in required_elements:
            if channel.find(elem) is None:
                missing.append(elem)
        
        if missing:
            return {"valid": False, "error": f"Missing required elements: {', '.join(missing)}"}
        
        # Contar episodios
        items = channel.findall("item")
        
        return {
            "valid": True,
            "episodes_count": len(items),
            "title": channel.find("title").text,
            "language": channel.find("language").text,
            "last_updated": channel.find("lastBuildDate").text if channel.find("lastBuildDate") is not None else "Unknown"
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}

async def mark_episode_completed(episode_id: str, language: str = None) -> Dict[str, Any]:
    """Marca un episodio como completado en el sistema de seguimiento del feed monitor"""
    try:
        # Crear directorio para episodios completados solo cuando sea necesario
        os.makedirs(COMPLETED_EPISODES_DIR, exist_ok=True)
        
        # Cargar estado actual del feed monitor
        completed_file = os.path.join(COMPLETED_EPISODES_DIR, "completed_episodes.json")
        
        completed_episodes = {}
        if os.path.exists(completed_file):
            async with aiofiles.open(completed_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if content.strip():
                    completed_episodes = json.loads(content)
        
        # Marcar episodio como completado
        completion_time = datetime.now().isoformat()
        
        if episode_id not in completed_episodes:
            completed_episodes[episode_id] = {}
        
        if language:
            # Marcar idioma específico como completado
            completed_episodes[episode_id][f"completed_{language}"] = completion_time
        else:
            # Marcar episodio general como completado
            completed_episodes[episode_id]["completed_all"] = completion_time
        
        # Guardar estado actualizado
        async with aiofiles.open(completed_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(completed_episodes, indent=2))
        
        log_debug(f"Episode {episode_id} marked as completed (language: {language or 'all'})")
        
        return {
            "success": True,
            "episode_id": episode_id,
            "language": language or "all",
            "completed_time": completion_time,
            "total_completed": len(completed_episodes)
        }
        
    except Exception as e:
        log_debug(f"Error marking episode completed: {e}")
        return {"success": False, "error": str(e)}

def list_rss_feeds() -> Dict[str, Any]:
    """Lista todos los feeds RSS disponibles."""
    try:
        feeds = []
        
        if not os.path.exists(RSS_STORAGE_DIR):
            return {"success": True, "feeds": [], "total": 0}
        
        for filename in os.listdir(RSS_STORAGE_DIR):
            if filename.endswith('.xml'):
                filepath = os.path.join(RSS_STORAGE_DIR, filename)
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                
                feeds.append({
                    "filename": filename,
                    "path": filepath,
                    "size": size,
                    "modified_time": mtime,
                    "public_url": f"{RSS_BASE_URL}/{filename}"
                })
        
        return {
            "success": True,
            "feeds": feeds,
            "total": len(feeds),
            "storage_dir": RSS_STORAGE_DIR
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Crear servidor MCP
server = Server("rss-publisher-agent")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista las herramientas disponibles del agente RSS Publisher."""
    return [
        Tool(
            name="publish_episode",
            description="Publica un episodio traducido al feed RSS correspondiente",
            inputSchema={
                "type": "object",
                "properties": {
                    "episode_id": {
                        "type": "string",
                        "description": "ID único del episodio"
                    },
                    "user_id": {
                        "type": "string", 
                        "description": "ID del usuario propietario del feed"
                    },
                    "language": {
                        "type": "string",
                        "description": "Código de idioma (es, en, fr, etc.)"
                    },
                    "new_audio_url": {
                        "type": "string",
                        "description": "URL del archivo de audio traducido"
                    },
                    "translated_title": {
                        "type": "string",
                        "description": "Título traducido del episodio"
                    },
                    "translated_description": {
                        "type": "string",
                        "description": "Descripción traducida del episodio"
                    },
                    "duration": {
                        "type": "string",
                        "description": "Duración del audio (formato HH:MM:SS)"
                    },
                    "audio_size": {
                        "type": "number",
                        "description": "Tamaño del archivo de audio en bytes"
                    }
                },
                "required": ["episode_id", "user_id", "language", "new_audio_url", "translated_title"]
            }
        ),
        Tool(
            name="create_rss_feed",
            description="Crea un nuevo feed RSS para un usuario e idioma",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "ID del usuario"
                    },
                    "language": {
                        "type": "string", 
                        "description": "Código de idioma"
                    },
                    "title": {
                        "type": "string",
                        "description": "Título del podcast"
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripción del podcast"
                    }
                },
                "required": ["user_id", "language"]
            }
        ),
        Tool(
            name="validate_rss",
            description="Valida la estructura de un feed RSS",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "ID del usuario"
                    },
                    "language": {
                        "type": "string",
                        "description": "Código de idioma"
                    }
                },
                "required": ["user_id", "language"]
            }
        ),
        Tool(
            name="list_feeds",
            description="Lista todos los feeds RSS disponibles",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_feed_info",
            description="Obtiene información detallada de un feed RSS específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "ID del usuario"
                    },
                    "language": {
                        "type": "string",
                        "description": "Código de idioma"
                    }
                },
                "required": ["user_id", "language"]
            }
        ),
        Tool(
            name="mark_episode_completed",
            description="Marca un episodio como completado en el sistema de seguimiento para evitar reprocesamiento",
            inputSchema={
                "type": "object",
                "properties": {
                    "episode_id": {
                        "type": "string",
                        "description": "ID único del episodio a marcar como completado"
                    },
                    "language": {
                        "type": "string",
                        "description": "Código de idioma específico (opcional, si no se especifica marca como completado para todos los idiomas)"
                    }
                },
                "required": ["episode_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Maneja las llamadas a herramientas del agente RSS Publisher."""
    
    if name == "publish_episode":
        required_fields = ["episode_id", "user_id", "language", "new_audio_url", "translated_title"]
        
        # Validar campos requeridos
        for field in required_fields:
            if not arguments.get(field):
                return [TextContent(type="text", text=json.dumps({"error": f"{field} is required"}))]
        
        try:
            # Obtener o crear feed RSS
            feed_path = await get_or_create_rss_feed(
                arguments["user_id"], 
                arguments["language"]
            )
            
            # Añadir episodio al feed
            result = await add_episode_to_rss(feed_path, arguments)
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "create_rss_feed":
        user_id = arguments.get("user_id")
        language = arguments.get("language")
        
        if not user_id or not language:
            return [TextContent(type="text", text=json.dumps({"error": "user_id and language are required"}))]
        
        try:
            feed_path = await get_or_create_rss_feed(
                user_id, 
                language,
                arguments.get("title"),
                arguments.get("description")
            )
            
            result = {
                "success": True,
                "feed_path": feed_path,
                "public_url": f"{RSS_BASE_URL}/{os.path.basename(feed_path)}",
                "user_id": user_id,
                "language": language
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "validate_rss":
        user_id = arguments.get("user_id")
        language = arguments.get("language")
        
        if not user_id or not language:
            return [TextContent(type="text", text=json.dumps({"error": "user_id and language are required"}))]
        
        try:
            feed_filename = f"{sanitize_filename(user_id)}_{language}.xml"
            feed_path = os.path.join(RSS_STORAGE_DIR, feed_filename)
            
            if not os.path.exists(feed_path):
                return [TextContent(type="text", text=json.dumps({"valid": False, "error": "RSS feed not found"}))]
            
            result = await validate_rss_feed(feed_path)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"valid": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "list_feeds":
        try:
            result = list_rss_feeds()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "get_feed_info":
        user_id = arguments.get("user_id")
        language = arguments.get("language")
        
        if not user_id or not language:
            return [TextContent(type="text", text=json.dumps({"error": "user_id and language are required"}))]
        
        try:
            feed_filename = f"{sanitize_filename(user_id)}_{language}.xml"
            feed_path = os.path.join(RSS_STORAGE_DIR, feed_filename)
            
            if not os.path.exists(feed_path):
                return [TextContent(type="text", text=json.dumps({"exists": False, "error": "RSS feed not found"}))]
            
            validation = await validate_rss_feed(feed_path)
            
            # Añadir info adicional
            stat = os.stat(feed_path)
            
            result = {
                "exists": True,
                "path": feed_path,
                "public_url": f"{RSS_BASE_URL}/{feed_filename}",
                "size": stat.st_size,
                "modified_time": stat.st_mtime,
                "validation": validation
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"exists": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "mark_episode_completed":
        episode_id = arguments.get("episode_id")
        language = arguments.get("language")
        
        if not episode_id:
            return [TextContent(type="text", text=json.dumps({"error": "episode_id is required"}))]
        
        try:
            result = await mark_episode_completed(episode_id, language)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

async def main():
    """Función principal del servidor MCP."""
    async with AsyncExitStack() as exit_stack:
        read_stream, write_stream = await exit_stack.enter_async_context(stdio_server())
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="rss-publisher-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())