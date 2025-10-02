// mcpAgentsConfig.ts
// Configuración de dominios MCP agents

const getEnvVariable = (key: string, fallback: string): string => {
  if (typeof process !== 'undefined' && process.env && process.env[key]) {
    return process.env[key] as string;
  }
  return fallback;
};

export const MCP_AGENTS: Record<string, string> = {
  'feed-monitor-agent': getEnvVariable('REACT_APP_FEED_MONITOR_URL', 'http://localhost:8000'),
  // Agrega aquí los demás agentes cuando estén desplegados
  // 'transcription-agent': getEnvVariable('REACT_APP_TRANSCRIPTION_AGENT_URL', 'https://transcription-agent.railway.app'),
  // 'translation-agent': getEnvVariable('REACT_APP_TRANSLATION_AGENT_URL', 'https://translation-agent.railway.app'),
  // 'rss-publisher-agent': getEnvVariable('REACT_APP_RSS_PUBLISHER_AGENT_URL', 'https://rss-publisher-agent.railway.app'),
  // 'tts-agent': getEnvVariable('REACT_APP_TTS_AGENT_URL', 'https://tts-agent.railway.app'),
};
