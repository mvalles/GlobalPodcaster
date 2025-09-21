#!/usr/bin/env python3
"""
🎼 GlobalPodcaster Scheduler
Alternativa inteligente a cron con mejor manejo de errores y logging

Funciones:
- Verificación automática de feeds cada 15 minutos
- Pipeline completo cada 6 horas (solo si hay episodios nuevos)
- Limpieza semanal los domingos a las 2 AM
- Logging detallado y métricas
- Manejo robusto de errores con reintentos

Uso:
    python scheduler.py                    # Ejecutar scheduler
    python scheduler.py --dry-run          # Modo de prueba (no ejecuta comandos)
    python scheduler.py --check-now        # Forzar verificación inmediata
    python scheduler.py --pipeline-now     # Forzar pipeline inmediato
"""

import schedule
import time
import subprocess
import logging
import sys
import os
import signal
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# Configuración
SCRIPT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = SCRIPT_DIR.parent
LOG_DIR = BACKEND_DIR / "logs"

# Crear directorio de logs
LOG_DIR.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('GlobalPodcaster')

class GlobalPodcasterScheduler:
    """Scheduler inteligente para GlobalPodcaster"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'feed_checks': 0,
            'pipeline_runs': 0,
            'cleanups': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        # Configurar manejador de señales para cierre limpio
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🎼 Iniciando GlobalPodcaster Scheduler")
        if dry_run:
            logger.info("🧪 Modo DRY-RUN activado - no se ejecutarán comandos reales")
    
    def _signal_handler(self, signum, frame):
        """Manejo de señales para cierre limpio"""
        logger.info(f"🛑 Señal {signum} recibida, cerrando scheduler...")
        self._cleanup_and_exit()
    
    def _cleanup_and_exit(self):
        """Limpieza final y estadísticas antes de salir"""
        uptime = datetime.now() - self.stats['start_time']
        
        logger.info("📊 Estadísticas del scheduler:")
        logger.info(f"  ⏱️ Tiempo activo: {uptime}")
        logger.info(f"  🔍 Verificaciones de feeds: {self.stats['feed_checks']}")
        logger.info(f"  🚀 Ejecuciones de pipeline: {self.stats['pipeline_runs']}")
        logger.info(f"  🧹 Limpiezas ejecutadas: {self.stats['cleanups']}")
        logger.info(f"  ❌ Errores encontrados: {self.stats['errors']}")
        
        sys.exit(0)
    
    def _run_command(self, cmd: list, timeout: int = 300, description: str = "") -> Dict[str, Any]:
        """Ejecutar comando con manejo robusto de errores"""
        if self.dry_run:
            logger.info(f"🧪 DRY-RUN: {description} - Comando: {' '.join(cmd)}")
            return {"success": True, "dry_run": True, "stdout": "", "stderr": ""}
        
        try:
            logger.info(f"🔧 Ejecutando: {description}")
            
            result = subprocess.run(
                cmd,
                cwd=BACKEND_DIR,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {description} completado exitosamente")
                return {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            else:
                logger.error(f"❌ {description} falló (código {result.returncode})")
                logger.error(f"stderr: {result.stderr}")
                self.stats['errors'] += 1
                return {
                    "success": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ {description} terminado por timeout ({timeout}s)")
            self.stats['errors'] += 1
            return {
                "success": False,
                "error": "timeout",
                "timeout": timeout
            }
            
        except Exception as e:
            logger.error(f"💥 Excepción ejecutando {description}: {e}")
            self.stats['errors'] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_feed_check(self) -> bool:
        """Ejecutar verificación de feeds con reintentos"""
        logger.info("🔍 Iniciando verificación de feeds RSS...")
        self.stats['feed_checks'] += 1
        
        # Intentar hasta 3 veces
        for attempt in range(1, 4):
            if attempt > 1:
                logger.info(f"🔄 Intento {attempt}/3 para verificación de feeds...")
            
            result = self._run_command(
                ['python', 'multi_agent_mcp_client.py', 'check'],
                timeout=300,
                description=f"Verificación de feeds (intento {attempt})"
            )
            
            if result["success"]:
                # Analizar resultado para estadísticas
                try:
                    if not result.get("dry_run"):
                        output_data = json.loads(result["stdout"])
                        new_episodes = output_data.get("new_episodes_count", 0)
                        
                        if new_episodes > 0:
                            logger.info(f"📢 ¡{new_episodes} nuevos episodios encontrados!")
                            # Marcar flag para pipeline
                            flag_file = BACKEND_DIR / ".new_episodes_detected"
                            flag_file.touch()
                        else:
                            logger.info("📭 No hay nuevos episodios")
                            
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"⚠️ No se pudo parsear resultado de feeds: {e}")
                
                return True
            
            # Si falla, esperar antes del siguiente intento
            if attempt < 3:
                wait_time = attempt * 30  # 30s, 60s
                logger.warning(f"⏳ Esperando {wait_time}s antes del siguiente intento...")
                time.sleep(wait_time)
        
        logger.error("❌ Verificación de feeds falló después de 3 intentos")
        return False
    
    def run_full_pipeline(self, force: bool = False) -> bool:
        """Ejecutar pipeline completo con verificación inteligente"""
        logger.info("🚀 Evaluando ejecución de pipeline completo...")
        
        # Verificar si hay trabajo que hacer (a menos que se fuerce)
        if not force:
            flag_file = BACKEND_DIR / ".new_episodes_detected"
            
            if not flag_file.exists():
                logger.info("⏭️ No hay flag de nuevos episodios, verificando...")
                
                # Verificación rápida
                check_result = self._run_command(
                    ['python', 'multi_agent_mcp_client.py', 'check'],
                    timeout=120,
                    description="Verificación rápida pre-pipeline"
                )
                
                if check_result["success"] and not check_result.get("dry_run"):
                    try:
                        output_data = json.loads(check_result["stdout"])
                        new_episodes = output_data.get("new_episodes_count", 0)
                        
                        if new_episodes == 0:
                            logger.info("📭 No hay episodios nuevos, omitiendo pipeline")
                            return True
                        else:
                            logger.info(f"📢 Verificación encontró {new_episodes} episodios nuevos")
                            
                    except json.JSONDecodeError:
                        logger.warning("⚠️ No se pudo parsear verificación, ejecutando pipeline por seguridad")
        
        self.stats['pipeline_runs'] += 1
        
        # Ejecutar pipeline con timeout de 2 horas
        result = self._run_command(
            ['python', 'multi_agent_mcp_client.py', 'pipeline'],
            timeout=7200,  # 2 horas
            description="Pipeline completo"
        )
        
        if result["success"]:
            # Limpiar flag de nuevos episodios
            flag_file = BACKEND_DIR / ".new_episodes_detected"
            if flag_file.exists():
                flag_file.unlink()
                
            # Analizar estadísticas del pipeline
            if not result.get("dry_run"):
                try:
                    # Buscar estadísticas en la salida
                    output = result["stdout"]
                    if "summary" in output:
                        logger.info("📊 Pipeline completado con estadísticas detalladas")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudieron extraer estadísticas: {e}")
            
            return True
        else:
            if result.get("error") == "timeout":
                logger.warning("⏱️ Pipeline terminado por timeout - puede haber procesado algunos episodios")
            
            return False
    
    def run_cleanup(self) -> bool:
        """Ejecutar limpieza semanal"""
        logger.info("🧹 Iniciando limpieza semanal...")
        self.stats['cleanups'] += 1
        
        script_path = SCRIPT_DIR / "cleanup.sh"
        
        result = self._run_command(
            ['bash', str(script_path)],
            timeout=1800,  # 30 minutos
            description="Limpieza semanal"
        )
        
        return result["success"]
    
    def setup_schedule(self):
        """Configurar horarios del scheduler"""
        logger.info("⏰ Configurando horarios del scheduler...")
        
        # Verificación de feeds cada 15 minutos
        schedule.every(15).minutes.do(self.run_feed_check)
        logger.info("  🔍 Verificación de feeds: cada 15 minutos")
        
        # Pipeline completo cada 6 horas
        schedule.every(6).hours.do(self.run_full_pipeline)
        logger.info("  🚀 Pipeline completo: cada 6 horas")
        
        # Limpieza semanal los domingos a las 2 AM
        schedule.every().sunday.at("02:00").do(self.run_cleanup)
        logger.info("  🧹 Limpieza semanal: domingos a las 2:00 AM")
        
        logger.info("✅ Scheduler configurado correctamente")
    
    def run_forever(self):
        """Ejecutar scheduler indefinidamente"""
        self.setup_schedule()
        
        logger.info("🎼 Scheduler activo - presiona Ctrl+C para detener")
        logger.info(f"📊 Próximas ejecuciones:")
        
        for job in schedule.jobs:
            logger.info(f"  ⏰ {job.job_func.__name__}: {job.next_run}")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Revisar cada minuto
                
                # Log de estado cada hora
                current_time = datetime.now()
                if current_time.minute == 0:  # Al inicio de cada hora
                    uptime = current_time - self.stats['start_time']
                    logger.info(f"💓 Scheduler activo - Uptime: {uptime}")
                    
            except KeyboardInterrupt:
                logger.info("🛑 Interrumpido por usuario")
                break
            except Exception as e:
                logger.error(f"💥 Error en loop principal del scheduler: {e}")
                self.stats['errors'] += 1
                time.sleep(60)  # Esperar un minuto antes de continuar
        
        self._cleanup_and_exit()

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GlobalPodcaster Scheduler')
    parser.add_argument('--dry-run', action='store_true', help='Modo de prueba (no ejecuta comandos)')
    parser.add_argument('--check-now', action='store_true', help='Ejecutar verificación de feeds inmediatamente')
    parser.add_argument('--pipeline-now', action='store_true', help='Ejecutar pipeline inmediatamente')
    parser.add_argument('--cleanup-now', action='store_true', help='Ejecutar limpieza inmediatamente')
    
    args = parser.parse_args()
    
    scheduler = GlobalPodcasterScheduler(dry_run=args.dry_run)
    
    # Verificar si estamos en el directorio correcto
    if not (BACKEND_DIR / "multi_agent_mcp_client.py").exists():
        logger.error("❌ No se encontró multi_agent_mcp_client.py - ejecuta desde el directorio correcto")
        sys.exit(1)
    
    # Ejecutar acción inmediata si se solicita
    if args.check_now:
        success = scheduler.run_feed_check()
        sys.exit(0 if success else 1)
    
    elif args.pipeline_now:
        success = scheduler.run_full_pipeline(force=True)
        sys.exit(0 if success else 1)
    
    elif args.cleanup_now:
        success = scheduler.run_cleanup()
        sys.exit(0 if success else 1)
    
    else:
        # Ejecutar scheduler normal
        scheduler.run_forever()

if __name__ == "__main__":
    main()