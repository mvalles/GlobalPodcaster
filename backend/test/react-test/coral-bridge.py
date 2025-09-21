#!/usr/bin/env python3
"""
Global Podcaster - Coral Protocol Bridge
Servidor HTTP que integra DirectMCP para acceso directo a herramientas MCP de agentes
"""

import os
import json
import subprocess
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Configuración
CORAL_BASE_URL = "http://localhost:5555"
APPLICATION_ID = "globalpodcaster"
PRIVACY_KEY = "test"

app = Flask(__name__)
CORS(app)

# Estadísticas globales
stats = {
    'total_checks': 0,
    'new_episodes': 0,
    'last_check': 'Never',
    'recent_episodes': [],
    'feeds_status': 'Active',
    'agent_status': 'Connected'
}

@app.route('/api/execute-check', methods=['POST'])
def execute_check():
    """Ejecuta verificación de feeds via Direct MCP Connection"""
    print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Executing feed check via Direct MCP...")
    
    try:
        print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Executing DirectMCPClient via subprocess...")
        
        # Ejecutar el DirectMCPClient como subprocess con comando 'check'
        result = subprocess.run([
            'python', '/workspaces/GlobalPodcaster/backend/multi_agent_mcp_client.py', 'check'
        ], capture_output=True, text=True, timeout=120, cwd='/workspaces/GlobalPodcaster/backend')
        
        if result.returncode == 0:
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] DirectMCP subprocess completed successfully")
            
            # Actualizar estadísticas
            global stats
            stats['total_checks'] += 1
            stats['last_check'] = datetime.now().strftime('%H:%M:%S')
            
            # Parsear output para buscar información de nuevos episodios
            # NOTA: No sumamos a stats aquí para evitar doble conteo - solo reportamos
            output = result.stdout
            new_episodes_found = 0
            
            try:
                import re
                # Buscar patrón "Encontrados X nuevos episodios"
                match = re.search(r'Encontrados (\d+) nuevos episodios', output)
                if match:
                    new_episodes_found = int(match.group(1))
                    # Actualizar stats con los episodios nuevos encontrados
                    stats['new_episodes'] = new_episodes_found
                else:
                    # Buscar patrón JSON como fallback
                    match = re.search(r'"new_episodes_count":\s*(\d+)', output)
                    if match:
                        new_episodes_found = int(match.group(1))
                        # Actualizar stats con los episodios nuevos encontrados
                        stats['new_episodes'] = new_episodes_found
            except Exception as e:
                print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Could not parse episodes count: {e}")
                pass
            
            return jsonify({
                "success": True,
                "method": "direct_mcp_subprocess",
                "message": f"Feed check executed successfully. Found {new_episodes_found} new episodes.",
                "session_id": "direct_mcp",
                "new_episodes_found": new_episodes_found,
                "coral_response": {
                    "status": 200,
                    "response": "Success via DirectMCP subprocess",
                    "success": True
                },
                "subprocess_output": result.stdout[-1000:] if result.stdout else "No output",  # Últimos 1000 chars
                "stats_updated": True
            })
        else:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] DirectMCP subprocess failed: {result.stderr}")
            return jsonify({
                "success": False,
                "method": "direct_mcp_subprocess",
                "error": f"Subprocess failed: {result.stderr}",
                "returncode": result.returncode
            })
            
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Execute check error: {e}")
        return jsonify({
            "success": False,
            "method": "direct_mcp_subprocess", 
            "error": str(e)
        })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas del monitoreo"""
    global stats
    stats_with_info = stats.copy()
    stats_with_info['coral_session_id'] = "direct_mcp"
    stats_with_info['coral_connected'] = True
    stats_with_info['mcp_method'] = "DirectMCP Subprocess"
    
    return jsonify(stats_with_info)

@app.route('/api/reset-stats', methods=['POST'])
def reset_stats():
    """Resetea las estadísticas"""
    global stats
    stats = {
        'total_checks': 0,
        'new_episodes': 0,
        'last_check': 'Never',
        'recent_episodes': [],
        'feeds_status': 'Active',
        'agent_status': 'Connected'
    }
    return jsonify({"success": True, "message": "Stats reset successfully"})

@app.route('/api/execute-pipeline', methods=['POST'])
def execute_pipeline():
    """Ejecuta el pipeline completo usando MultiAgent DirectMCP"""
    print(f"🚀 [{datetime.now().strftime('%H:%M:%S')}] Executing full pipeline...")
    
    try:
        # Ejecutar el pipeline completo
        result = subprocess.run([
            'python', '/workspaces/GlobalPodcaster/backend/multi_agent_mcp_client.py', 'full'
        ], capture_output=True, text=True, timeout=180, cwd='/workspaces/GlobalPodcaster/backend')
        
        if result.returncode == 0:
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Full pipeline completed successfully")
            
            # Actualizar estadísticas
            global stats
            stats['total_checks'] += 1
            stats['last_check'] = datetime.now().strftime('%H:%M:%S')
            
            # Parsear el resultado para obtener información del pipeline
            output = result.stdout
            episodes_processed = 0
            new_episodes_found = 0
            
            try:
                import re
                # Buscar episodios procesados 
                match_processed = re.search(r'Procesados (\d+) episodios', output)
                if match_processed:
                    episodes_processed = int(match_processed.group(1))
                
                # Buscar nuevos episodios encontrados
                match_new = re.search(r'Encontrados (\d+) nuevos episodios', output)
                if match_new:
                    new_episodes_found = int(match_new.group(1))
                    
                # Actualizar stats con la información más relevante
                if episodes_processed > 0:
                    stats['new_episodes'] = episodes_processed
                elif new_episodes_found > 0:
                    stats['new_episodes'] = new_episodes_found
            except Exception as e:
                print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Could not parse pipeline output: {e}")
                pass
            
            return jsonify({
                "success": True,
                "method": "multi_agent_pipeline",
                "message": f"Pipeline completed successfully. Processed {episodes_processed} episodes, found {new_episodes_found} new episodes.",
                "session_id": "multi_agent",
                "episodes_processed": episodes_processed,
                "new_episodes_found": new_episodes_found,
                "pipeline_output": result.stdout[-1000:] if result.stdout else "No output",
                "stats_updated": True
            })
        else:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Pipeline failed: {result.stderr}")
            return jsonify({
                "success": False,
                "method": "multi_agent_pipeline",
                "error": f"Pipeline failed: {result.stderr}",
                "returncode": result.returncode
            })
            
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Pipeline error: {e}")
        return jsonify({
            "success": False,
            "method": "multi_agent_pipeline",
            "error": str(e)
        })

@app.route('/')
def index():
    """Sirve la página principal - dashboard moderno"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/test.html')
def test_page():
    """Sirve la página de test con interfaz de botones"""
    return send_from_directory('.', 'test.html')

@app.route('/dashboard.html')
def dashboard():
    """Sirve el dashboard moderno"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/index.html')
def landing_page():
    """Sirve la página de landing"""
    return send_from_directory('.', 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verificar el estado de salud de todos los agentes MCP"""
    print(f"🩺 [{datetime.now().strftime('%H:%M:%S')}] Checking MCP agents health...")
    
    try:
        # Ejecutar verificación de salud
        result = subprocess.run([
            'python', '/workspaces/GlobalPodcaster/backend/multi_agent_mcp_client.py', 'health'
        ], capture_output=True, text=True, timeout=60, cwd='/workspaces/GlobalPodcaster/backend')
        
        if result.returncode == 0:
            # Parsear el resultado JSON del health check
            output = result.stdout
            
            try:
                # Buscar el JSON en el output
                import re
                json_match = re.search(r'({.*"success".*})', output, re.DOTALL)
                if json_match:
                    health_data = json.loads(json_match.group(1))
                    
                    return jsonify({
                        "success": health_data.get("success", True),
                        "agents": health_data.get("agents", {}),
                        "overall_health": health_data.get("overall_health", "unknown"),
                        "last_health_check": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "raw_output": result.stdout[-500:] if result.stdout else "No output"
                    })
                else:
                    # Fallback si no se encuentra JSON válido
                    print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] No valid JSON found in health output")
                    agents_status = {
                        "feed_monitor": {"status": "unknown", "last_check": "never"},
                        "transcription": {"status": "unknown", "last_check": "never"},
                        "translation": {"status": "unknown", "last_check": "never"},
                        "tts": {"status": "unknown", "last_check": "never"}
                    }
                    
                    return jsonify({
                        "success": True,
                        "agents": agents_status,
                        "overall_health": "unknown",
                        "last_health_check": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "raw_output": result.stdout[-500:] if result.stdout else "No output"
                    })
                    
            except json.JSONDecodeError as e:
                print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] JSON decode error in health check: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to parse health check response: {e}",
                    "overall_health": "error"
                })
        else:
            return jsonify({
                "success": False,
                "error": f"Health check failed: {result.stderr}",
                "overall_health": "unhealthy"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "overall_health": "error"
        })

@app.route('/api/start-scheduler', methods=['POST'])
def start_scheduler():
    """Iniciar el scheduler en background"""
    print(f"⏰ [{datetime.now().strftime('%H:%M:%S')}] Starting background scheduler...")
    
    try:
        # Verificar si el scheduler ya está corriendo
        result = subprocess.run(['pgrep', '-f', 'scheduler.py'], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({
                "success": False,
                "error": "Scheduler already running",
                "message": "El scheduler ya está ejecutándose en el sistema"
            })
        
        # Iniciar el scheduler en background
        scheduler_path = '/workspaces/GlobalPodcaster/backend/scheduler.py'
        subprocess.Popen(['python', scheduler_path], 
                        cwd='/workspaces/GlobalPodcaster/backend',
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        return jsonify({
            "success": True,
            "message": "Scheduler iniciado en background",
            "details": "El scheduler ejecutará verificaciones cada 15 minutos y pipeline cada 6 horas"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/reset-feed-state', methods=['POST'])
def reset_feed_state():
    """Resetear el estado de feeds para forzar detección de todos los episodios como nuevos"""
    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Resetting feed state...")
    
    try:
        import shutil
        state_dir = '/workspaces/GlobalPodcaster/backend/agents/feed-monitor-agent/feed_monitor_state'
        
        # Eliminar directorio de estado si existe
        if os.path.exists(state_dir):
            shutil.rmtree(state_dir)
            print(f"🗑️ [{datetime.now().strftime('%H:%M:%S')}] Deleted feed state directory")
        
        # Resetear estadísticas también
        global stats
        stats['new_episodes'] = 0
        stats['total_checks'] = 0
        
        return jsonify({
            "success": True,
            "message": "Feed state reseteado exitosamente",
            "details": "La próxima verificación detectará todos los episodios como nuevos"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ===== RUTAS PARA SERVIR ARCHIVOS DE MEDIOS =====

@app.route('/media/<path:filename>')
def serve_audio_files(filename):
    """Sirve archivos de audio TTS desde el directorio storage del agente TTS"""
    try:
        # Ruta al directorio storage del agente TTS
        tts_storage_dir = '/workspaces/GlobalPodcaster/backend/agents/tts-agent/storage'
        
        # Crear directorio si no existe
        os.makedirs(tts_storage_dir, exist_ok=True)
        
        # Servir archivo con headers apropiados
        response = send_from_directory(tts_storage_dir, filename)
        
        # Headers para archivos de audio
        response.headers['Content-Type'] = 'audio/mpeg'
        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache 1 hora
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        print(f"🔊 [{datetime.now().strftime('%H:%M:%S')}] Serving audio: {filename}")
        return response
        
    except FileNotFoundError:
        return jsonify({"error": "Audio file not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Error serving audio file: {str(e)}"}), 500

@app.route('/feeds/<path:filename>')
def serve_rss_feeds(filename):
    """Sirve feeds RSS desde el directorio de feeds del agente RSS Publisher"""
    try:
        # Ruta al directorio de feeds RSS
        rss_storage_dir = '/workspaces/GlobalPodcaster/backend/agents/rss-publisher-agent/rss_feeds'
        
        # Crear directorio si no existe
        os.makedirs(rss_storage_dir, exist_ok=True)
        
        # Servir archivo con headers apropiados para RSS
        response = send_from_directory(rss_storage_dir, filename)
        
        # Headers para feeds RSS
        response.headers['Content-Type'] = 'application/rss+xml; charset=utf-8'
        response.headers['Cache-Control'] = 'public, max-age=300'  # Cache 5 minutos
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Serving RSS feed: {filename}")
        return response
        
    except FileNotFoundError:
        return jsonify({"error": "RSS feed not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Error serving RSS feed: {str(e)}"}), 500

@app.route('/api/media/list')
def list_media_files():
    """Lista archivos de audio disponibles"""
    try:
        tts_storage_dir = '/workspaces/GlobalPodcaster/backend/agents/tts-agent/storage'
        os.makedirs(tts_storage_dir, exist_ok=True)
        
        audio_files = []
        for filename in os.listdir(tts_storage_dir):
            if filename.endswith(('.mp3', '.wav', '.ogg')):
                filepath = os.path.join(tts_storage_dir, filename)
                stat = os.stat(filepath)
                
                audio_files.append({
                    "filename": filename,
                    "url": f"http://localhost:8080/media/{filename}",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return jsonify({
            "success": True,
            "files": audio_files,
            "total": len(audio_files)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/feeds/list')
def list_rss_feeds():
    """Lista feeds RSS disponibles"""
    try:
        rss_storage_dir = '/workspaces/GlobalPodcaster/backend/agents/rss-publisher-agent/rss_feeds'
        os.makedirs(rss_storage_dir, exist_ok=True)
        
        rss_feeds = []
        for filename in os.listdir(rss_storage_dir):
            if filename.endswith('.xml'):
                filepath = os.path.join(rss_storage_dir, filename)
                stat = os.stat(filepath)
                
                rss_feeds.append({
                    "filename": filename,
                    "url": f"http://localhost:8080/feeds/{filename}",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return jsonify({
            "success": True,
            "feeds": rss_feeds,
            "total": len(rss_feeds)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/info')
def api_info():
    """Información de la API en formato JSON"""
    return jsonify({
        "status": "Global Podcaster Coral Bridge",
        "version": "1.0-directmcp",
        "coral_url": CORAL_BASE_URL,
        "media_urls": {
            "audio_base": "http://localhost:8080/media/",
            "rss_base": "http://localhost:8080/feeds/",
            "api_media_list": "http://localhost:8080/api/media/list",
            "api_feeds_list": "http://localhost:8080/api/feeds/list"
        },
        "endpoints": [
            "POST /api/execute-check - Execute feed check via DirectMCP",
            "POST /api/execute-pipeline - Execute full pipeline",
            "GET /api/health - Check MCP agents health",
            "POST /api/start-scheduler - Start background scheduler",
            "POST /api/reset-feed-state - Reset feed state to detect all episodes as new",
            "GET /api/stats - Get monitoring statistics", 
            "POST /api/reset-stats - Reset statistics",
            "GET /media/<filename> - Serve TTS audio files",
            "GET /feeds/<filename> - Serve RSS feeds",
            "GET /api/media/list - List available audio files",
            "GET /api/feeds/list - List available RSS feeds"
        ]
    })

if __name__ == '__main__':
    print("🚀 Global Podcaster Coral Protocol Bridge starting...")
    print("🌐 Coral Server URL:", CORAL_BASE_URL)
    print("📱 Frontend available at: http://localhost:8080")
    print("🔧 Available API endpoints:")
    print("   POST /api/execute-check - Execute feed check via DirectMCP")
    print("   POST /api/execute-pipeline - Execute full pipeline")
    print("   GET  /api/health - Check MCP agents health")
    print("   POST /api/start-scheduler - Start background scheduler")
    print("   POST /api/reset-feed-state - Reset feed state to detect all episodes as new")
    print("   GET  /api/stats - Get monitoring statistics")
    print("   POST /api/reset-stats - Reset statistics")
    
    app.run(host='0.0.0.0', port=8080, debug=False)