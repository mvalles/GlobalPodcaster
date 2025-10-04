export interface User {
  uid: string; // Firebase UID, también usado como id
  email: string | null;
  // Usamos sólo full_name (Firestore) en todo el frontend
  full_name?: string | null;
  photoURL?: string | null;
  // Campos personalizados opcionales
  onboarding_completed?: boolean;
  preferred_languages?: string[];
  voice_sample_url?: string;
  voice_prompt_seen?: boolean; // Whether user has been shown or skipped the voice sample prompt
  notification_preferences?: {
    email_alerts: boolean;
  };
}

export interface Podcast {
  id: number;
  title: string;
  description: string;
  original_language: string;
  cover_image: string;
  episode_count: number;
  rss_feed_url: string;
  created_date: string;
  updated_date: string;
}

export interface Translation {
  id: number;
  podcast_id: number;
  target_language: string;
  status: 'processing' | 'in_progress' | 'published' | 'error';
  progress: number;
  episode_count: number;
  created_date: string;
  updated_date: string;
}

export interface Episode {
  id: number;
  podcast_id: number;
  title: string;
  description: string;
  audio_url: string;
  transcript?: string;
  translations?: {
    [language: string]: {
      text: string;
      audio_url?: string;
    };
  };
  published_date: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface AppState {
  auth: AuthState;
  podcasts: Podcast[];
  translations: Translation[];
  episodes: Episode[];
  isLoading: boolean;
  error: string | null;
}
