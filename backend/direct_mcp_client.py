#!/usr/bin/env python3
"""
Cliente MCP directo para conectarse al feed-monitor-agent
Bypass de Coral Protocol para acceso directo a herramientas MCP
"""

import asyncio
import json
import sys
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

class DirectMCPClient:
    """Cliente MCP directo que se conecta al feed-monitor-agent"""
    
    def __init__(self):
        self.process = None
        self.initialized = False
        
    async def connect(self) -> bool:
        """Conecta directamente al agente MCP feed-monitor"""
        try:
            print(f"🔗 [{datetime.now().strftime('%H:%M:%S')}] Connecting to feed-monitor-agent via direct MCP...")
            
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                '/workspaces/GlobalPodcaster/backend/agents/feed-monitor-agent/feed_monitor_mcp_server.py',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize MCP session
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "coral-bridge-direct", "version": "1.0.0"}
                }
            }
            
            await self._send_message(init_request)
            response = await self._read_message()
            
            if response and response.get('result'):
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] MCP initialization successful")
                
                # Send initialized notification
                initialized = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                
                await self._send_message(initialized)
                self.initialized = True
                return True
            else:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] MCP initialization failed: {response}")
                return False
                
        except Exception as e:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Connection error: {e}")
            return False
    
    async def _send_message(self, message: Dict[str, Any]):
        """Envía mensaje JSON-RPC al proceso MCP"""
        if not self.process or not self.process.stdin:
            raise Exception("MCP process not connected")
            
        message_str = json.dumps(message) + '\n'
        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()
    
    async def _read_message(self) -> Optional[Dict[str, Any]]:
        """Lee mensaje JSON-RPC del proceso MCP"""
        if not self.process or not self.process.stdout:
            raise Exception("MCP process not connected")
            
        try:
            line = await self.process.stdout.readline()
            if line:
                return json.loads(line.decode().strip())
            return None
        except Exception as e:
            print(f"⚠️ Error reading message: {e}")
            return None
    
    async def list_tools(self) -> Dict[str, Any]:
        """Lista las herramientas disponibles en el agente MCP"""
        if not self.initialized:
            raise Exception("MCP client not initialized")
            
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        await self._send_message(tools_request)
        response = await self._read_message()
        
        return response or {}
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Ejecuta una herramienta MCP específica"""
        if not self.initialized:
            raise Exception("MCP client not initialized")
            
        tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        print(f"🔧 [{datetime.now().strftime('%H:%M:%S')}] Calling MCP tool: {tool_name}")
        
        await self._send_message(tool_request)
        response = await self._read_message()
        
        return response or {}
    
    async def check_feeds(self) -> Dict[str, Any]:
        """Ejecuta check_feeds directamente via MCP"""
        try:
            print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Executing check_feeds via direct MCP connection...")
            
            response = await self.call_tool("check_feeds", {})
            
            if response.get('result'):
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] check_feeds executed successfully")
                return {
                    "success": True,
                    "method": "direct_mcp",
                    "response": response
                }
            else:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] check_feeds failed: {response}")
                return {
                    "success": False,
                    "method": "direct_mcp", 
                    "error": response.get('error', 'Unknown error'),
                    "response": response
                }
                
        except Exception as e:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Direct MCP error: {e}")
            return {
                "success": False,
                "method": "direct_mcp",
                "error": str(e)
            }
    
    async def disconnect(self):
        """Desconecta del agente MCP"""
        if self.process:
            print(f"🔌 [{datetime.now().strftime('%H:%M:%S')}] Disconnecting from MCP agent...")
            self.process.terminate()
            await self.process.wait()
            self.process = None
            self.initialized = False

# Singleton instance
direct_mcp_client = DirectMCPClient()

async def test_direct_mcp_connection():
    """Test function para probar la conexión directa MCP"""
    print("🧪 Testing Direct MCP Connection")
    print("=" * 50)
    
    # Connect
    if await direct_mcp_client.connect():
        
        # List tools
        print("\n📋 Listing available tools...")
        tools = await direct_mcp_client.list_tools()
        if tools.get('result', {}).get('tools'):
            for tool in tools['result']['tools']:
                print(f"  🔧 {tool['name']}: {tool['description']}")
        
        # Execute check_feeds
        print("\n🚀 Executing check_feeds...")
        result = await direct_mcp_client.check_feeds()
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Disconnect
        await direct_mcp_client.disconnect()
    else:
        print("❌ Failed to connect to MCP agent")

if __name__ == "__main__":
    asyncio.run(test_direct_mcp_connection())