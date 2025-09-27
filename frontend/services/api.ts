import type { User } from "types";
import { MCP_AGENTS } from "./mcpAgentsConfig";

//const API_BASE_URL = 'http://localhost:5555'; // Backend principal (Development)
const API_BASE_URL = 'https://user-api-production-daed.up.railway.app'; // Backend principal (Production)

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}


async function fetchWithAuth(url: string, options: RequestInit = {}, baseUrl: string = API_BASE_URL): Promise<Response> {
  const token = localStorage.getItem('auth_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)["authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${baseUrl}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.text();
    let errorMessage = 'An error occurred';

    try {
      const errorData = JSON.parse(error);
      errorMessage = errorData.message || errorData.detail || errorMessage;
    } catch {
      errorMessage = error || `HTTP ${response.status}`;
    }

    throw new ApiError(response.status, errorMessage);
  }

  return response;
}

// Auth API
export async function login(credentials: { email: string; password: string }) {
  const response = await fetchWithAuth('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
  return response.json();
}

export async function register(userData: {
  full_name: string;
  email: string;
  password: string;
}) {
  const response = await fetchWithAuth('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(userData),
  });
  return response.json();
}

export async function logout() {
  const response = await fetchWithAuth('/auth/logout', {
    method: 'POST',
  });
  return response.json();
}

export async function fetchUser(uid: string) {
  const response = await fetchWithAuth(`/user/me?uid=${uid}`);
  return response.json();
}

export async function updateUser(userData: Partial<User>) {
  const response = await fetchWithAuth('/user/me', {
    method: 'PUT',
    body: JSON.stringify(userData),
  });
  return response.json();
}


export async function validateRssFeed(feed_url: string) {
  const agentUrl = MCP_AGENTS['feed-monitor-agent'];
  if (!agentUrl) throw new Error('MCP agent domain not configured for: feed-monitor-agent');
  const response = await fetchWithAuth('/call_tool', {
    method: 'POST',
    body: JSON.stringify({
      name: 'validateRssFeed',
      arguments: { feed_url }
    }),
  }, agentUrl);
  return response.json();
}

// Crear usuario en Firestore tras registro en Firebase Auth
export async function createUserInFirestore({ uid, email, full_name }: { uid: string; email: string; full_name: string }) {
  const response = await fetch(`${API_BASE_URL}/user/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uid, email, full_name })
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || 'Failed to create user in Firestore');
  }
  return response.json();
}
// Obtener feeds de usuario
export async function getUserFeeds(user_id: string) {
  const agentUrl = MCP_AGENTS['feed-monitor-agent'];
  if (!agentUrl) throw new Error('MCP agent domain not configured for: feed-monitor-agent');
  const response = await fetchWithAuth('/call_tool', {
    method: 'POST',
    body: JSON.stringify({
      name: 'get_user_feeds',
      arguments: { user_id }
    }),
  }, agentUrl);
  return response.json();
}
// Añadir podcast a usuario
export async function createPodcast(podcastData: { rss_feed_url: string; title?: string; description?: string; user_id: string; email: string }) {
  const agentUrl = MCP_AGENTS['feed-monitor-agent'];
  if (!agentUrl) throw new Error('MCP agent domain not configured for: feed-monitor-agent');
  const response = await fetchWithAuth('/call_tool', {
    method: 'POST',
    body: JSON.stringify({
      name: 'add_feed_to_user',
      arguments: {
        user_id: podcastData.user_id, // UID
        email: podcastData.email,     // Email
        feed_url: podcastData.rss_feed_url,
        custom_name: podcastData.title || '',
        active: true,
      }
    }),
  }, agentUrl);
  return response.json();
}