// mcpAgentsConfig.ts
// Configuración de dominios MCP agents

export const MCP_AGENTS: Record<string, string> = {
  // 'feed-monitor-agent': 'http://localhost:8000', // development
  'feed-monitor-agent': 'global-podcaster-agent': 'https://globalpodcaster-production.up.railway.app',
  // Agrega aquí los demás agentes cuando estén desplegados
  // 'transcription-agent': 'https://transcription-agent.railway.app',
  // 'translation-agent': 'https://translation-agent.railway.app',
  // 'rss-publisher-agent': 'https://rss-publisher-agent.railway.app',
  // 'tts-agent': 'https://tts-agent.railway.app',
};
