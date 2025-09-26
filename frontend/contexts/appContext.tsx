import React, { createContext, useContext, useReducer, useEffect, type ReactNode } from 'react';
import { appReducer, initialState } from 'reducers/appReducer';
import type { AppState, User } from '../types';
import * as api from '../services/api';
import { auth } from '../firebaseConfig';
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
  uploadVoiceSample?: (file: File) => Promise<string>;
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
        // Opcional: puedes obtener datos adicionales del usuario aquí
        const userData = {
          uid: firebaseUser.uid,
          email: firebaseUser.email,
          displayName: firebaseUser.displayName,
          id: firebaseUser.uid,
          full_name: firebaseUser.displayName,
          photoURL: firebaseUser.photoURL,
        };
        dispatch({ type: 'LOGIN_SUCCESS', payload: userData });
        // Si tienes onboarding, puedes llamar a fetchPodcasts y fetchTranslations aquí
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
      const userData = {
        uid: firebaseUser.uid,
        email: firebaseUser.email,
        displayName: firebaseUser.displayName,
          id: firebaseUser.uid,
          full_name: firebaseUser.displayName,
          photoURL: firebaseUser.photoURL,
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
      // Opcional: puedes actualizar el perfil con el nombre
      // await updateProfile(firebaseUser, { displayName: userData.full_name });
      const userDataObj = {
        uid: firebaseUser.uid,
        email: firebaseUser.email,
        displayName: userData.full_name,
          id: firebaseUser.uid,
          full_name: userData.full_name,
          photoURL: firebaseUser.photoURL,
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
      const user = await api.fetchUser();
      dispatch({ type: 'UPDATE_USER', payload: user });
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
      dispatch({ type: 'UPDATE_USER', payload: updatedUser });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to update user' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // const fetchPodcasts = async () => {
  //   try {
  //     const podcasts = await api.fetchPodcasts();
  //     dispatch({ type: 'SET_PODCASTS', payload: podcasts });
  //   } catch (error: any) {
  //     dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to fetch podcasts' });
  //   }
  // };

  // const fetchTranslations = async () => {
  //   try {
  //     const translations = await api.fetchTranslations();
  //     dispatch({ type: 'SET_TRANSLATIONS', payload: translations });
  //   } catch (error: any) {
  //     dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to fetch translations' });
  //   }
  // };

  // const uploadVoiceSample = async (file: File) => {
  //   dispatch({ type: 'SET_LOADING', payload: true });
  //   try {
  //     const response = await api.uploadVoiceSample(file);
  //     
  //     // Update user with new voice sample URL
  //     const updatedUser = { ...state.auth.user!, voice_sample_url: response.file_url };
  //     dispatch({ type: 'UPDATE_USER', payload: updatedUser });
  //     
  //     return response.file_url;
  //   } catch (error: any) {
  //     dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to upload voice sample' });
  //     throw error;
  //   } finally {
  //     dispatch({ type: 'SET_LOADING', payload: false });
  //   }
  // };


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
    // fetchPodcasts,
    createPodcast,
    // fetchTranslations,
    // uploadVoiceSample,
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