# React Test Directory# GlobalPodcaster - Sistema de Monitoreo Continuo



Este directorio contiene los componentes de prueba e integración para el frontend React con el backend GlobalPodcaster.Este directorio contiene el **Sistema de Monitoreo Continuo** para GlobalPodcaster - una interfaz web avanzada con timer automático para monitoreo 24/7 de feeds RSS.



## Archivos:## 🎯 Sistema MCP + Coral Protocol (Puerto 8080)



- `coral-bridge.py` - Servidor HTTP que actúa como bridge entre React frontend y los agentes MCP### ✅ Usar el Sistema:

- Utiliza DirectMCPClient para acceso directo a las herramientas de los agentes```bash

# 1. Iniciar Coral Server (desde /workspaces/GlobalPodcaster/backend/coral)

## Uso:./start-server.sh



```bash# 2. Iniciar Coral Bridge para React

cd /workspaces/GlobalPodcaster/backend/test/react-testpython coral-bridge.py

python coral-bridge.py

```# 3. Abrir navegador en:

http://localhost:8080  # ← Interfaz Coral Protocol

El servidor estará disponible en http://localhost:8080```

### 📁 Archivos del Sistema (MCP Optimizado):
- `continuous-monitor-coral.html` - **🌟 Interfaz Coral Protocol** con agentes MCP
- `coral-bridge.py` - **🔧 Coral Protocol Bridge** que comunica con agentes MCP  
- `session_data.json` - **📊 Datos** de episodios procesados
- `README.md` - **📋 Esta documentación**

## 🚀 Características del Sistema

### ⏰ **Monitoreo Automático**
- Timer configurable (10s - 10min)
- Ejecución continua en background
- Start/Stop desde interfaz web

### 📊 **Dashboard Completo**
- Estadísticas en tiempo real
- Contador de verificaciones y episodios
- Uptime del sistema
- Lista de episodios recientes

### 🎛️ **Control Granular**
- Start/Stop monitoreo continuo
- Ejecución manual (una vez)
- Reset de estadísticas
- Configuración de intervalos

### 🔗 **APIs RESTful**
- `POST /api/execute-check` - Ejecutar verificación
- `GET /api/stats` - Obtener estadísticas
- `POST /api/reset-stats` - Resetear contadores

## 📋 Diferencias vs Sistemas Anteriores

| Característica | Puerto 3000 (Eliminado) | Puerto 8080 (Actual) |
|---------------|-------------------------|----------------------|
| **Monitoreo Continuo** | ❌ Solo ejecución única | ✅ Timer automático configurable |
| **Dashboard** | ❌ Logs básicos | ✅ Estadísticas completas |
| **Control** | ❌ Solo botón ejecutar | ✅ Start/Stop/Reset/Manual |
| **Pipeline Real** | ⚠️ Solo SSE básico | ✅ Ejecución completa del agent |
| **Producción** | ❌ Solo para testing | ✅ Listo para 24/7 |

## 🎯 Migración Completa

### ❌ **Sistema Eliminado (Puerto 3000):**
- Archivos React/Vite eliminados
- `node_modules/`, `package.json`, `vite.config.ts` borrados
- `index.html` eliminado
- Solo quedó redirección en `test.html`

### ✅ **Sistema Actual (Puerto 8080):**
- Backend Flask con APIs
- Frontend HTML/JS puro (sin dependencias)
- Integración directa con `agent_coral_compatible.py`
- Sistema completo y autónomo

## 🛠️ Testing y Uso

### Verificación Rápida:
```bash
./test-continuous.sh
```

### Monitoreo en Producción:
1. Iniciar backend: `python frontend-bridge.py`
2. Abrir: `http://localhost:8080`
3. Configurar intervalo (300+ segundos para prod)
4. Click "Start Continuous Monitoring"
5. Monitorear dashboard 24/7

¡El sistema está completamente funcional y optimizado! 🎉