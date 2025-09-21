#!/usr/bin/env python3
"""
Translation Agent - Servidor MCP Completo

Servidor MCP que proporciona servicios de traducción usando Mistral AI.
Traduce texto entre diferentes idiomas utilizando modelos de lenguaje.

Tools disponibles:
- translate_text: Traduce texto a un idioma específico
- detect_language: Detecta el idioma de un texto
- get_supported_languages: Lista los idiomas soportados
- batch_translate: Traduce múltiples textos en batch

Autor: GlobalPodcaster Team  
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
import requests
import aiohttp

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

# Cargar variables de entorno desde .env
load_dotenv("/workspaces/GlobalPodcaster/devcontainer/.env")

def log_debug(message: str):
    """Log debug messages to stderr"""
    print(f"[DEBUG translation] {message}", file=sys.stderr, flush=True)

# Configuración de Mistral AI
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")

if MISTRAL_API_KEY:
    log_debug("Mistral API key found - using real API mode")
    HEADERS = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
else:
    log_debug("MISTRAL_API_KEY no encontrada, usando modo simulación")
    HEADERS = None

async def translate_with_mistral(text: str, target_lang: str, source_lang: Optional[str] = None, model: str = "mistral-tiny") -> Dict[str, Any]:
    """Traduce texto usando Mistral AI."""
    
    # Modo simulación si no hay API key
    if not MISTRAL_API_KEY:
        log_debug("Using simulation mode - no MISTRAL_API_KEY")
        await asyncio.sleep(1)  # Simular tiempo de procesamiento
        return {
            "success": True,
            "translated_text": f"[SIMULADO] Texto traducido al {target_lang}: {text[:100]}... (modo demo sin API key)",
            "source_language": source_lang or "auto-detect",
            "target_language": target_lang,
            "confidence": 0.92,
            "simulated": True
        }
    
    try:
        log_debug(f"Translating {len(text)} chars to {target_lang} with real Mistral API")
        
        # Construir prompt
        if source_lang:
            prompt = f"Translate the following text from {source_lang} to {target_lang}. Only provide the translation, no explanations:\n\n{text}"
        else:
            prompt = f"Translate the following text to {target_lang}. Only provide the translation, no explanations:\n\n{text}"
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": min(len(text) * 2, 4000),  # Estimate output length
            "temperature": 0.2
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(MISTRAL_API_URL, headers=HEADERS, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API error {response.status}: {error_text}"
                    }
                
                result = await response.json()
                
                if "choices" not in result or not result["choices"]:
                    return {
                        "success": False, 
                        "error": "No translation choices returned"
                    }
                
                translated_text = result["choices"][0]["message"]["content"].strip()
                
                log_debug(f"Translation success: {len(translated_text)} chars")
                
                return {
                    "success": True,
                    "original_text": text,
                    "translated_text": translated_text,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "model": model,
                    "original_length": len(text),
                    "translated_length": len(translated_text),
                    "simulated": False
                }
                
    except Exception as e:
        log_debug(f"Translation error: {e} - fallback to simulation")
        # Fallback a simulación cuando la API real falla
        await asyncio.sleep(1)  # Simular tiempo de procesamiento
        return {
            "success": True,
            "translated_text": f"[SIMULADO] Texto traducido al {target_lang}: {text[:100]}... (error en API: {str(e)[:50]})",
            "source_language": source_lang or "auto-detect",
            "target_language": target_lang,
            "confidence": 0.88,
            "simulated": True
        }

async def detect_language_mistral(text: str) -> Dict[str, Any]:
    """Detecta el idioma de un texto usando Mistral AI."""
    try:
        prompt = f"""Detect the language of the following text. Respond only with the ISO 639-1 language code (2 letters) like 'en', 'es', 'fr', etc. No explanations, just the code:

{text[:500]}"""  # Limit to first 500 chars for detection
        
        data = {
            "model": "mistral-tiny",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(MISTRAL_API_URL, headers=HEADERS, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {"success": False, "error": f"API error: {error_text}"}
                
                result = await response.json()
                detected_lang = result["choices"][0]["message"]["content"].strip().lower()
                
                return {
                    "success": True,
                    "detected_language": detected_lang,
                    "text_sample": text[:100] + "..." if len(text) > 100 else text
                }
                
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_supported_languages() -> List[Dict[str, str]]:
    """Lista de idiomas soportados para traducción."""
    return [
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"}, 
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "it", "name": "Italian"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "nl", "name": "Dutch"},
        {"code": "ru", "name": "Russian"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "zh", "name": "Chinese (Simplified)"},
        {"code": "ar", "name": "Arabic"},
        {"code": "hi", "name": "Hindi"},
        {"code": "tr", "name": "Turkish"},
        {"code": "pl", "name": "Polish"},
        {"code": "sv", "name": "Swedish"},
        {"code": "da", "name": "Danish"},
        {"code": "no", "name": "Norwegian"}
    ]

def get_available_models() -> List[Dict[str, str]]:
    """Lista de modelos disponibles en Mistral."""
    return [
        {"name": "mistral-tiny", "description": "Fast and efficient model for basic translations"},
        {"name": "mistral-small", "description": "Balanced model with good accuracy and speed"},
        {"name": "mistral-medium", "description": "High accuracy model for complex translations"}
    ]

# Crear servidor MCP
server = Server("translation-agent")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista las herramientas disponibles del agente de traducción."""
    return [
        Tool(
            name="translate_text",
            description="Traduce texto a un idioma específico usando Mistral AI",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Texto a traducir"
                    },
                    "target_language": {
                        "type": "string",
                        "description": "Código de idioma objetivo (ej: 'es', 'en', 'fr')"
                    },
                    "source_language": {
                        "type": "string", 
                        "description": "Código de idioma fuente (opcional, se detectará automáticamente si no se especifica)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Modelo de Mistral a usar (default: 'mistral-tiny')",
                        "default": "mistral-tiny"
                    }
                },
                "required": ["text", "target_language"]
            }
        ),
        Tool(
            name="detect_language",
            description="Detecta el idioma de un texto",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Texto del cual detectar el idioma"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="get_supported_languages",
            description="Lista los idiomas soportados para traducción",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_available_models",
            description="Lista los modelos de traducción disponibles",
            inputSchema={
                "type": "object", 
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="batch_translate",
            description="Traduce múltiples textos en batch",
            inputSchema={
                "type": "object",
                "properties": {
                    "texts": {
                        "type": "array",
                        "description": "Array de textos a traducir",
                        "items": {"type": "string"}
                    },
                    "target_language": {
                        "type": "string",
                        "description": "Código de idioma objetivo para todos los textos"
                    },
                    "source_language": {
                        "type": "string",
                        "description": "Código de idioma fuente (opcional)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Modelo de Mistral a usar",
                        "default": "mistral-tiny"
                    }
                },
                "required": ["texts", "target_language"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Maneja las llamadas a herramientas del agente de traducción."""
    
    if name == "translate_text":
        text = arguments.get("text")
        target_language = arguments.get("target_language")
        source_language = arguments.get("source_language")
        model = arguments.get("model", "mistral-tiny")
        
        if not text or not target_language:
            return [TextContent(type="text", text=json.dumps({"error": "text and target_language are required"}))]
        
        try:
            result = await translate_with_mistral(text, target_language, source_language, model)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "text": text[:100] + "..." if len(text) > 100 else text
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    elif name == "detect_language":
        text = arguments.get("text")
        
        if not text:
            return [TextContent(type="text", text=json.dumps({"error": "text is required"}))]
        
        try:
            result = await detect_language_mistral(text)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
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
    
    elif name == "batch_translate":
        texts = arguments.get("texts", [])
        target_language = arguments.get("target_language")
        source_language = arguments.get("source_language")
        model = arguments.get("model", "mistral-tiny")
        
        if not texts or not target_language:
            return [TextContent(type="text", text=json.dumps({"error": "texts and target_language are required"}))]
        
        try:
            results = []
            for i, text in enumerate(texts):
                log_debug(f"Batch translating {i+1}/{len(texts)}")
                result = await translate_with_mistral(text, target_language, source_language, model)
                results.append(result)
                
                # Small delay to avoid rate limiting
                if i < len(texts) - 1:
                    await asyncio.sleep(0.5)
            
            batch_result = {
                "success": True,
                "total_texts": len(texts),
                "target_language": target_language,
                "source_language": source_language,
                "model": model,
                "translations": results
            }
            
            return [TextContent(type="text", text=json.dumps(batch_result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "total_texts": len(texts)
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
                server_name="translation-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())