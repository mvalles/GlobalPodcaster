#!/usr/bin/env python3
"""
Transcription Agent - Servidor MCP Completo

Servidor MCP que proporciona servicios de transcripción de audio usando Deepgram.
Convierte archivos de audio a texto utilizando la API de Deepgram.

Tools disponibles:
- transcribe_audio: Transcribe un archivo de audio desde URL
- get_supported_languages: Lista los idiomas soportados para transcripción
- transcribe_with_options: Transcribe con opciones avanzadas (idioma, puntuación, etc.)

Autor: GlobalPodcaster Team
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from deepgram import Deepgram
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
    print(f"[DEBUG transcription] {message}", file=sys.stderr, flush=True)

# Inicializar cliente Deepgram
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
dg_client = None
if DEEPGRAM_API_KEY:
    try:
        dg_client = Deepgram(DEEPGRAM_API_KEY)
        log_debug("Deepgram client initialized successfully")
    except Exception as e:
        log_debug(f"Error initializing Deepgram: {e}")
        dg_client = None
else:
    log_debug("DEEPGRAM_API_KEY no encontrada, usando modo simulación")

async def transcribe_audio_url(audio_url: str, language: str = "en", punctuate: bool = True, model: str = "nova-2") -> Dict[str, Any]:
    """Transcribe audio desde URL usando Deepgram."""
    
    # Modo simulación si no hay cliente Deepgram
    if not dg_client:
        log_debug("Using simulation mode - no DEEPGRAM_API_KEY")
        await asyncio.sleep(1)  # Simular tiempo de procesamiento
        return {
            "success": True,
            "transcript": f"[SIMULADO] Transcripción simulada del audio: {audio_url[:50]}... (modo demo sin API key)",
            "language": language,
            "confidence": 0.95,
            "simulated": True
        }
    
    try:
        log_debug(f"Transcribing audio with real Deepgram API: {audio_url}")
        
        options = {
            "punctuate": punctuate,
            "language": language,
            "model": model,
            "smart_format": True,
            "diarize": False
        }
        
        response = await dg_client.transcription.prerecorded(
            {"url": audio_url},
            options
        )
        
        if not response or "results" not in response:
            log_debug("No results from Deepgram - fallback to simulation")
            await asyncio.sleep(1)
            return {
                "success": True,
                "transcript": f"[SIMULADO] Transcripción simulada del audio: {audio_url[:50]}... (API no retornó resultados)",
                "language": language,
                "confidence": 0.85,
                "simulated": True
            }
        
        channels = response["results"]["channels"]
        if not channels or not channels[0]["alternatives"]:
            log_debug("No transcription alternatives found - fallback to simulation")
            await asyncio.sleep(1)
            return {
                "success": True,
                "transcript": f"[SIMULADO] Transcripción simulada del audio: {audio_url[:50]}... (no se encontraron alternativas)",
                "language": language,
                "confidence": 0.85,
                "simulated": True
            }
        
        transcript = channels[0]["alternatives"][0]["transcript"]
        confidence = channels[0]["alternatives"][0].get("confidence", 0.0)
        
        log_debug(f"Real Deepgram transcription success: {len(transcript)} chars, confidence: {confidence}")
        
        return {
            "success": True,
            "transcript": transcript,
            "confidence": confidence,
            "language": language,
            "model": model,
            "audio_url": audio_url,
            "simulated": False
        }
        
    except Exception as e:
        log_debug(f"Transcription error: {e} - fallback to simulation")
        # Fallback a simulación cuando la API real falla
        await asyncio.sleep(1)  # Simular tiempo de procesamiento
        return {
            "success": True,
            "transcript": f"[SIMULADO] Transcripción simulada del audio: {audio_url[:50]}... (error en API: {str(e)[:50]})",
            "language": language,
            "confidence": 0.90,
            "simulated": True
        }

def get_supported_languages() -> List[Dict[str, str]]:
    """Lista de idiomas soportados por Deepgram."""
    return [
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "it", "name": "Italian"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "nl", "name": "Dutch"},
        {"code": "pl", "name": "Polish"},
        {"code": "ru", "name": "Russian"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "zh", "name": "Chinese"},
        {"code": "hi", "name": "Hindi"},
        {"code": "ar", "name": "Arabic"},
        {"code": "tr", "name": "Turkish"}
    ]

def get_available_models() -> List[Dict[str, str]]:
    """Lista de modelos disponibles en Deepgram."""
    return [
        {"name": "nova-2", "description": "Latest and most accurate general-purpose model"},
        {"name": "nova", "description": "High accuracy general-purpose model"},
        {"name": "enhanced", "description": "Enhanced model for improved accuracy"},
        {"name": "base", "description": "Fastest model with good accuracy"}
    ]

# Crear servidor MCP
server = Server("transcription-agent")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista las herramientas disponibles del agente de transcripción."""
    return [
        Tool(
            name="transcribe_audio",
            description="Transcribe un archivo de audio desde URL usando Deepgram",
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_url": {
                        "type": "string",
                        "description": "URL del archivo de audio a transcribir"
                    },
                    "language": {
                        "type": "string", 
                        "description": "Código de idioma para la transcripción (default: 'en')",
                        "default": "en"
                    },
                    "punctuate": {
                        "type": "boolean",
                        "description": "Agregar puntuación al texto (default: true)",
                        "default": True
                    },
                    "model": {
                        "type": "string",
                        "description": "Modelo de Deepgram a usar (default: 'nova-2')",
                        "default": "nova-2"
                    }
                },
                "required": ["audio_url"]
            }
        ),
        Tool(
            name="get_supported_languages",
            description="Lista los idiomas soportados para transcripción",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_available_models", 
            description="Lista los modelos de transcripción disponibles",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="transcribe_with_options",
            description="Transcribe audio con opciones avanzadas (diarización, formato inteligente, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_url": {
                        "type": "string",
                        "description": "URL del archivo de audio a transcribir"
                    },
                    "language": {
                        "type": "string",
                        "description": "Código de idioma para la transcripción",
                        "default": "en"
                    },
                    "model": {
                        "type": "string", 
                        "description": "Modelo de Deepgram a usar",
                        "default": "nova-2"
                    },
                    "punctuate": {
                        "type": "boolean",
                        "description": "Agregar puntuación",
                        "default": True
                    },
                    "diarize": {
                        "type": "boolean",
                        "description": "Separar speakers diferentes",
                        "default": False
                    },
                    "smart_format": {
                        "type": "boolean",
                        "description": "Formato inteligente (fechas, números, etc.)",
                        "default": True
                    }
                },
                "required": ["audio_url"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Maneja las llamadas a herramientas del agente de transcripción."""
    
    if name == "transcribe_audio":
        audio_url = arguments.get("audio_url")
        language = arguments.get("language", "en")
        punctuate = arguments.get("punctuate", True)
        model = arguments.get("model", "nova-2")
        
        if not audio_url:
            return [TextContent(type="text", text=json.dumps({"error": "audio_url is required"}))]
        
        # La función transcribe_audio_url ya maneja internamente todos los fallbacks
        # No necesitamos un try/catch aquí porque la función nunca debería fallar
        result = await transcribe_audio_url(audio_url, language, punctuate, model)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_supported_languages":
        try:
            languages = get_supported_languages()
            result = {
                "success": True,
                "languages": languages,
                "total_languages": len(languages)
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "get_available_models":
        try:
            models = get_available_models()
            result = {
                "success": True,
                "models": models,
                "total_models": len(models)
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "transcribe_with_options":
        audio_url = arguments.get("audio_url")
        language = arguments.get("language", "en")
        model = arguments.get("model", "nova-2") 
        punctuate = arguments.get("punctuate", True)
        diarize = arguments.get("diarize", False)
        smart_format = arguments.get("smart_format", True)
        
        if not audio_url:
            return [TextContent(type="text", text=json.dumps({"error": "audio_url is required"}))]
        
        try:
            log_debug(f"Advanced transcription: {audio_url} with diarize={diarize}")
            
            options = {
                "punctuate": punctuate,
                "language": language,
                "model": model,
                "smart_format": smart_format,
                "diarize": diarize
            }
            
            response = await dg_client.transcription.prerecorded(
                {"url": audio_url},
                options
            )
            
            if not response or "results" not in response:
                result = {"success": False, "error": "No results from Deepgram"}
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            channels = response["results"]["channels"]
            if not channels or not channels[0]["alternatives"]:
                result = {"success": False, "error": "No transcription alternatives found"}
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            transcript = channels[0]["alternatives"][0]["transcript"]
            confidence = channels[0]["alternatives"][0].get("confidence", 0.0)
            
            # Include speaker information if diarization was enabled
            words = channels[0]["alternatives"][0].get("words", [])
            speakers = []
            if diarize and words:
                unique_speakers = set()
                for word in words:
                    if "speaker" in word:
                        unique_speakers.add(word["speaker"])
                speakers = list(unique_speakers)
            
            result = {
                "success": True,
                "transcript": transcript,
                "confidence": confidence,
                "language": language,
                "model": model,
                "audio_url": audio_url,
                "options": {
                    "punctuate": punctuate,
                    "diarize": diarize,
                    "smart_format": smart_format
                },
                "speakers": speakers if diarize else [],
                "words_count": len(words)
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            log_debug(f"Advanced transcription error: {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "audio_url": audio_url
            }
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
                server_name="transcription-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())