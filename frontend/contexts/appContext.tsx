import React, { createContext, useContext, useReducer, useEffect, type ReactNode } from 'react';
import { appReducer, initialState } from 'reducers/appReducer';
import type { AppState, User } from '../types';
import * as api from '../services/api';
import { auth, storage } from '../firebaseConfig';
import { ref as storageRef, uploadBytes, getDownloadURL } from 'firebase/storage';
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<any>;
  // Action creators
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  fetchUser: () => Promise<void>;
  updateUser: (userData: Partial<User>) => Promise<void>;
  fetchPodcasts?: () => Promise<void>;
  createPodcast?: (podcastData: CreatePodcastData) => Promise<void>;
  fetchTranslations?: () => Promise<void>;
  uploadVoiceSample: (file: File) => Promise<string>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

interface RegisterData {
  full_name: string;
  email: string;
  password: string;
}

interface CreatePodcastData {
  rss_feed_url: string;
  title?: string;
  description?: string;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Initialize app - check for existing auth
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      dispatch({ type: 'SET_LOADING', payload: true });
      if (firebaseUser) {
        // Fetch user from Firestore to get onboarding_completed and other fields
        try {
          const firestoreUser = await api.fetchUser(firebaseUser.uid);
          const userData: User = {
            uid: firebaseUser.uid,
            email: firebaseUser.email || null,
            full_name: firestoreUser.full_name ?? firebaseUser.displayName ?? null,
            photoURL: firebaseUser.photoURL,
            onboarding_completed: Boolean(firestoreUser?.onboarding_completed),
            preferred_languages: firestoreUser?.preferred_languages,
            voice_sample_url: firestoreUser?.voice_sample_url,
            voice_prompt_seen: Boolean(firestoreUser?.voice_prompt_seen),
            notification_preferences: firestoreUser?.notification_preferences,
          };
          dispatch({ type: 'LOGIN_SUCCESS', payload: userData });
        } catch (err) {
          // Fallback to basic user if Firestore fetch fails
          const userData: User = {
            uid: firebaseUser.uid,
            email: firebaseUser.email || null,
            full_name: firebaseUser.displayName ?? null,
            photoURL: firebaseUser.photoURL,
            onboarding_completed: false,
          };
          dispatch({ type: 'LOGIN_SUCCESS', payload: userData });
        }
      } else {
        dispatch({ type: 'LOGOUT' });
      }
      dispatch({ type: 'SET_LOADING', payload: false });
    });
    return () => unsubscribe();
  }, []);

  const login = async (email: string, password: string) => {
    dispatch({ type: 'SET_AUTH_LOADING', payload: true });
    dispatch({ type: 'SET_AUTH_ERROR', payload: null });
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;
      // Obtener datos completos del usuario desde Firestore
      const firestoreUser = await api.fetchUser(firebaseUser.uid);
      const userData: User = {
        uid: firebaseUser.uid,
        email: firebaseUser.email || null,
        full_name: firestoreUser.full_name ?? firebaseUser.displayName ?? null,
        photoURL: firebaseUser.photoURL,
        onboarding_completed: Boolean(firestoreUser?.onboarding_completed),
        preferred_languages: firestoreUser?.preferred_languages,
        voice_sample_url: firestoreUser?.voice_sample_url,
        voice_prompt_seen: Boolean(firestoreUser?.voice_prompt_seen),
        notification_preferences: firestoreUser?.notification_preferences,
      };
      dispatch({ type: 'LOGIN_SUCCESS', payload: userData });
      // Si tienes onboarding, puedes llamar a fetchPodcasts y fetchTranslations aquí
    } catch (error: any) {
      dispatch({ type: 'SET_AUTH_ERROR', payload: error.message || 'Login failed' });
    } finally {
      dispatch({ type: 'SET_AUTH_LOADING', payload: false });
    }
  };

  const logout = async () => {
    try {
      await signOut(auth);
      dispatch({ type: 'LOGOUT' });
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const register = async (userData: RegisterData) => {
    dispatch({ type: 'SET_AUTH_LOADING', payload: true });
    dispatch({ type: 'SET_AUTH_ERROR', payload: null });
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, userData.email, userData.password);
      const firebaseUser = userCredential.user;
      // Crear usuario en Firestore
      await api.createUserInFirestore({
        uid: firebaseUser.uid,
        email: firebaseUser.email ?? userData.email,
        full_name: userData.full_name
      });
      // Obtener datos completos del usuario desde Firestore
      const firestoreUser = await api.fetchUser(firebaseUser.uid);
      const userDataObj: User = {
        uid: firebaseUser.uid,
        email: (firebaseUser.email ?? userData.email) || null,
        full_name: firestoreUser.full_name ?? userData.full_name ?? null,
        photoURL: firebaseUser.photoURL,
        onboarding_completed: Boolean(firestoreUser?.onboarding_completed),
        preferred_languages: firestoreUser?.preferred_languages,
        voice_sample_url: firestoreUser?.voice_sample_url,
        voice_prompt_seen: Boolean(firestoreUser?.voice_prompt_seen),
        notification_preferences: firestoreUser?.notification_preferences,
      };
      dispatch({ type: 'LOGIN_SUCCESS', payload: userDataObj });
    } catch (error: any) {
      dispatch({ type: 'SET_AUTH_ERROR', payload: error.message || 'Registration failed' });
    } finally {
      dispatch({ type: 'SET_AUTH_LOADING', payload: false });
    }
  };

  const fetchUser = async () => {
    try {
      const uid = state.auth.user?.uid;
      if (!uid || uid === 'undefined') {
        dispatch({ type: 'SET_AUTH_ERROR', payload: 'No authenticated user (uid undefined)' });
        throw new Error('No authenticated user (uid undefined)');
      }
      const user = await api.fetchUser(uid);
      const merged: User = {
        ...(state.auth.user || {} as User),
        ...user,
        uid: state.auth.user?.uid || uid,
      } as User;
      dispatch({ type: 'UPDATE_USER', payload: merged });
      return user;
    } catch (error: any) {
      dispatch({ type: 'SET_AUTH_ERROR', payload: error.message });
      throw error;
    }
  };

  const updateUser = async (userData: Partial<User>) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const updatedUser = await api.updateUser(userData);
      const merged: User = {
        ...(state.auth.user || {} as User),
        ...updatedUser,
        uid: state.auth.user?.uid || updatedUser?.uid,
      } as User;
      dispatch({ type: 'UPDATE_USER', payload: merged });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to update user' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const fetchPodcasts = async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const userId = state.auth.user?.uid;
      if (!userId) throw new Error('No authenticated user');
      const result = await api.getUserFeeds(userId);
      // Map backend feeds to frontend Podcast format
      const podcasts = (result.feeds || []).map((feed: any) => ({
        id: feed.feed_id,
        title: feed.custom_name || feed.feed_url,
        description: 'TODO',
        rss_feed_url: feed.feed_url,
        status: feed.active ? 'active' : 'paused',
        created_date: feed.added_at || '',
      }));
      dispatch({ type: 'SET_PODCASTS', payload: podcasts });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to fetch podcasts' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const fetchTranslations = async () => {
    try {
      const translations = await api.fetchTranslations();
      dispatch({ type: 'SET_TRANSLATIONS', payload: translations });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to fetch translations' });
    }
  };

  const uploadVoiceSample = async (file: File) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const uid = state.auth.user?.uid;
      if (!uid) throw new Error('No authenticated user');
      const path = `voice-samples/${uid}/${Date.now()}_${file.name}`;
      const ref = storageRef(storage, path);
      await uploadBytes(ref, file);
      const url = await getDownloadURL(ref);
      // Persist in backend/Firestore
  await api.updateUser({ uid, voice_sample_url: url, voice_prompt_seen: true });
  const updatedUser = { ...state.auth.user!, voice_sample_url: url, voice_prompt_seen: true };
      dispatch({ type: 'UPDATE_USER', payload: updatedUser });
      return url;
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to upload voice sample' });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const createPodcast = async (podcastData: CreatePodcastData) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
  const userId = state.auth.user?.uid;
  const email = state.auth.user?.email;
  if (!userId || !email) throw new Error('No authenticated user or email');
  const newPodcast = await api.createPodcast({ ...podcastData, user_id: userId, email });
      dispatch({ type: 'ADD_PODCAST', payload: newPodcast });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to create podcast' });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const contextValue: AppContextType = {
    state,
    dispatch,
    login,
    logout,
    register,
    fetchUser,
    updateUser,
    fetchPodcasts,
    createPodcast,
    fetchTranslations,
    uploadVoiceSample,
  };

  return <AppContext.Provider value={contextValue}>
    {children}
  </AppContext.Provider>;
}

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};