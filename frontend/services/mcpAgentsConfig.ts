// mcpAgentsConfig.ts
// Configuración de dominios MCP agents

export const MCP_AGENTS: Record<string, string> = {
  'feed-monitor-agent': import.meta.env?.VITE_FEED_MONITOR_URL || 'http://localhost:8000',
  // Agrega aquí los demás agentes cuando estén desplegados
  // 'transcription-agent': import.meta.env?.VITE_TRANSCRIPTION_AGENT_URL || 'https://transcription-agent.railway.app',
  // 'translation-agent': import.meta.env?.VITE_TRANSLATION_AGENT_URL || 'https://translation-agent.railway.app',
  // 'rss-publisher-agent': import.meta.env?.VITE_RSS_PUBLISHER_AGENT_URL || 'https://rss-publisher-agent.railway.app',
  // 'tts-agent': import.meta.env?.VITE_TTS_AGENT_URL || 'https://tts-agent.railway.app',
};
