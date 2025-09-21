#!/usr/bin/env python3
"""
TTS Agent - Servidor MCP Completo

Servidor MCP que proporciona servicios de síntesis de voz (TTS).
Utiliza ElevenLabs como proveedor principal con fallback a Google TTS.

Tools disponibles:
- generate_speech: Genera audio desde texto usando voz especificada
- list_voices: Lista las voces disponibles en ElevenLabs
- get_voice_info: Obtiene información detallada de una voz
- generate_with_settings: Genera audio con configuraciones avanzadas
- get_storage_info: Información sobre archivos de audio almacenados

Autor: GlobalPodcaster Team
"""

import asyncio
import json
import os
import sys
import uuid
import time
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
import aiofiles

from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from gtts import gTTS
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

# Cargar variables de entorno desde .env
load_dotenv("/workspaces/GlobalPodcaster/devcontainer/.env")

def log_debug(message: str):
    """Log debug messages to stderr"""
    print(f"[DEBUG tts] {message}", file=sys.stderr, flush=True)

# Configuración
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEFAULT_VOICE_ID = os.getenv("TTS_DEFAULT_VOICE_ID")
# Usar path absoluto para storage para evitar crear directorios en lugares incorrectos
STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(os.path.dirname(__file__), "storage"))
STORAGE_BASE_URL = os.getenv("STORAGE_BASE_URL", "http://localhost:8080/media")

# El directorio de storage se creará solo cuando se guarde un archivo

# Inicializar cliente ElevenLabs si hay API key
elevenlabs_client = None
if ELEVEN_API_KEY:
    elevenlabs_client = ElevenLabs(api_key=ELEVEN_API_KEY)
    log_debug("ElevenLabs client initialized")
else:
    log_debug("No ElevenLabs API key, using fallback only")

def make_filename(prefix="tts", ext="mp3"):
    """Genera un nombre de archivo único."""
    ts = int(time.time())
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}_{ts}_{unique}.{ext}"

async def generate_tts_elevenlabs(text: str, voice_id: str, model: str = "eleven_multilingual_v2") -> Dict[str, Any]:
    """Genera TTS usando ElevenLabs."""
    try:
        if not elevenlabs_client:
            return {"success": False, "error": "ElevenLabs API key not configured"}
        
        log_debug(f"Generating TTS with ElevenLabs: {len(text)} chars, voice: {voice_id}")
        
        out_name = make_filename("tts_eleven", "mp3")
        out_path = os.path.join(STORAGE_DIR, out_name)
        
        # Crear directorio solo cuando vayamos a guardar el archivo
        os.makedirs(STORAGE_DIR, exist_ok=True)
        
        # Generar audio
        audio_gen = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model
        )
        
        # Combinar chunks en bytes
        audio_bytes = b"".join(audio_gen)
        
        # Guardar archivo de forma async
        async with aiofiles.open(out_path, "wb") as f:
        
        filename = os.path.basename(out_path)
        public_url = f"{STORAGE_BASE_URL}/{filename}"
        
        log_debug(f"TTS success: {out_path}")
        
        return {
            "success": True,
            "provider": "elevenlabs",
            "local_path": out_path,
            "audio_url": public_url,
            "filename": filename,
            "voice_id": voice_id,
            "model": model,
            "text_length": len(text),
            "file_size": len(audio_bytes),
            "simulated": False
        }
        
    except Exception as e:
        log_debug(f"ElevenLabs error: {e}")
        return {"success": False, "error": str(e), "provider": "elevenlabs"}

async def generate_tts_gtts_fallback(text: str, lang: str = None) -> Dict[str, Any]:
    """Fallback TTS usando Google TTS."""
    try:
        log_debug(f"Generating TTS with gTTS fallback: {len(text)} chars")
        
        # Detectar idioma si no se especifica
        if not lang:
            lang = 'es' if any(char in text.lower() for char in 'ñáéíóúü') else 'en'
        
        out_name = make_filename("tts_gtts", "mp3")
        out_path = os.path.join(STORAGE_DIR, out_name)
        
        # Generar TTS (blocking operation, but gTTS is fast)
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(out_path)
        
        filename = os.path.basename(out_path)
        public_url = f"{STORAGE_BASE_URL}/{filename}"
        
        # Get file size
        file_size = os.path.getsize(out_path)
        
        log_debug(f"gTTS success: {out_path}")
        
        return {
            "success": True,
            "provider": "gtts",
            "local_path": out_path,
            "audio_url": public_url,
            "filename": filename,
            "language": lang,
            "text_length": len(text),
            "file_size": file_size,
            "simulated": True
        }
        
    except Exception as e:
        log_debug(f"gTTS error: {e}")
        return {"success": False, "error": str(e), "provider": "gtts"}

async def generate_speech_with_fallback(text: str, voice_id: str = None, model: str = "eleven_multilingual_v2", force_fallback: bool = False) -> Dict[str, Any]:
    """Genera TTS con fallback automático."""
    
    if not force_fallback and elevenlabs_client and voice_id:
        try:
            result = await generate_tts_elevenlabs(text, voice_id, model)
            if result["success"]:
                return result
            
            # Si falla por créditos, usar fallback
            error_msg = result.get("error", "").lower()
            if "quota" in error_msg or "credits" in error_msg:
                log_debug("ElevenLabs quota exceeded, using fallback")
                return await generate_tts_gtts_fallback(text)
            else:
                return result
                
        except Exception as e:
            log_debug(f"ElevenLabs exception, using fallback: {e}")
            return await generate_tts_gtts_fallback(text)
    else:
        # Usar fallback directamente
        return await generate_tts_gtts_fallback(text)

async def list_elevenlabs_voices() -> Dict[str, Any]:
    """Lista las voces disponibles en ElevenLabs."""
    try:
        if not elevenlabs_client:
            return {"success": False, "error": "ElevenLabs API key not configured"}
        
        voices = elevenlabs_client.voices.get_all()
        
        voice_list = []
        for voice in voices.voices:
            voice_info = {
                "voice_id": voice.voice_id,
                "name": voice.name,
                "category": voice.category if hasattr(voice, 'category') else 'unknown',
                "description": voice.description if hasattr(voice, 'description') else '',
                "gender": voice.labels.get('gender') if hasattr(voice, 'labels') and voice.labels else 'unknown',
                "age": voice.labels.get('age') if hasattr(voice, 'labels') and voice.labels else 'unknown',
                "accent": voice.labels.get('accent') if hasattr(voice, 'labels') and voice.labels else 'unknown'
            }
            voice_list.append(voice_info)
        
        return {
            "success": True,
            "voices": voice_list,
            "total_voices": len(voice_list),
            "default_voice_id": DEFAULT_VOICE_ID
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_storage_info() -> Dict[str, Any]:
    """Información sobre archivos de audio almacenados."""
    try:
        if not os.path.exists(STORAGE_DIR):
            return {"success": False, "error": f"Storage directory {STORAGE_DIR} does not exist"}
        
        files = []
        total_size = 0
        
        for filename in os.listdir(STORAGE_DIR):
            if filename.endswith(('.mp3', '.wav', '.ogg')):
                filepath = os.path.join(STORAGE_DIR, filename)
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                
                files.append({
                    "filename": filename,
                    "size": size,
                    "url": f"{STORAGE_BASE_URL}/{filename}",
                    "modified_time": mtime
                })
                total_size += size
        
        return {
            "success": True,
            "storage_dir": STORAGE_DIR,
            "base_url": STORAGE_BASE_URL,
            "total_files": len(files),
            "total_size": total_size,
            "files": files[-10:]  # Last 10 files
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Crear servidor MCP
server = Server("tts-agent")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista las herramientas disponibles del agente TTS."""
    return [
        Tool(
            name="generate_speech",
            description="Genera audio desde texto usando síntesis de voz. Utiliza ElevenLabs o fallback a Google TTS",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Texto a convertir a audio"
                    },
                    "voice_id": {
                        "type": "string",
                        "description": "ID de voz de ElevenLabs (opcional, usa default si no se especifica)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Modelo de ElevenLabs a usar (default: 'eleven_multilingual_v2')",
                        "default": "eleven_multilingual_v2"
                    },
                    "force_fallback": {
                        "type": "boolean",
                        "description": "Forzar uso de Google TTS fallback (default: false)",
                        "default": False
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="list_voices",
            description="Lista las voces disponibles en ElevenLabs",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_voice_info",
            description="Obtiene información detallada de una voz específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "voice_id": {
                        "type": "string",
                        "description": "ID de la voz a consultar"
                    }
                },
                "required": ["voice_id"]
            }
        ),
        Tool(
            name="get_storage_info",
            description="Información sobre archivos de audio almacenados",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="generate_with_settings", 
            description="Genera audio con configuraciones avanzadas específicas",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Texto a convertir"
                    },
                    "voice_id": {
                        "type": "string",
                        "description": "ID de voz"
                    },
                    "model": {
                        "type": "string",
                        "description": "Modelo de ElevenLabs",
                        "default": "eleven_multilingual_v2"
                    },
                    "stability": {
                        "type": "number",
                        "description": "Estabilidad de voz (0.0-1.0)",
                        "default": 0.5
                    },
                    "similarity_boost": {
                        "type": "number", 
                        "description": "Boost de similitud (0.0-1.0)",
                        "default": 0.5
                    },
                    "style": {
                        "type": "number",
                        "description": "Estilo de voz (0.0-1.0)",
                        "default": 0.0
                    }
                },
                "required": ["text"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Maneja las llamadas a herramientas del agente TTS."""
    
    if name == "generate_speech":
        text = arguments.get("text")
        voice_id = arguments.get("voice_id") or DEFAULT_VOICE_ID
        model = arguments.get("model", "eleven_multilingual_v2")
        force_fallback = arguments.get("force_fallback", False)
        
        if not text:
            return [TextContent(type="text", text=json.dumps({"error": "text is required"}))]
        
        try:
            result = await generate_speech_with_fallback(text, voice_id, model, force_fallback)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "text": text[:100] + "..." if len(text) > 100 else text
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "list_voices":
        try:
            result = await list_elevenlabs_voices()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "get_voice_info":
        voice_id = arguments.get("voice_id")
        
        if not voice_id:
            return [TextContent(type="text", text=json.dumps({"error": "voice_id is required"}))]
        
        try:
            if not elevenlabs_client:
                return [TextContent(type="text", text=json.dumps({"error": "ElevenLabs API key not configured"}))]
            
            voice = elevenlabs_client.voices.get(voice_id)
            
            voice_info = {
                "success": True,
                "voice_id": voice.voice_id,
                "name": voice.name,
                "category": voice.category if hasattr(voice, 'category') else 'unknown',
                "description": voice.description if hasattr(voice, 'description') else '',
                "labels": voice.labels if hasattr(voice, 'labels') else {},
                "settings": voice.settings.__dict__ if hasattr(voice, 'settings') else {}
            }
            
            return [TextContent(type="text", text=json.dumps(voice_info, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e), "voice_id": voice_id}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "get_storage_info":
        try:
            result = get_storage_info()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "generate_with_settings":
        text = arguments.get("text")
        voice_id = arguments.get("voice_id") or DEFAULT_VOICE_ID
        model = arguments.get("model", "eleven_multilingual_v2")
        
        if not text:
            return [TextContent(type="text", text=json.dumps({"error": "text is required"}))]
        
        try:
            # For now, use basic generation - advanced settings require more ElevenLabs API integration
            result = await generate_speech_with_fallback(text, voice_id, model)
            
            # Add settings info to result
            if result.get("success"):
                result["advanced_settings"] = {
                    "stability": arguments.get("stability", 0.5),
                    "similarity_boost": arguments.get("similarity_boost", 0.5),
                    "style": arguments.get("style", 0.0),
                    "note": "Advanced settings integration pending"
                }
            
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
                server_name="tts-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())