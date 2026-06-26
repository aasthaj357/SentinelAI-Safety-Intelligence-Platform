/* eslint-disable react-refresh/only-export-components */
import { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabase';

const DEMO_USER_ID = '00000000-0000-4000-a000-000000000001';

const ActiveProjectContext = createContext(null);

export function ActiveProjectProvider({ children }) {
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [userId, setUserId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const applyUser = useCallback((uid) => {
    if (!uid) {
      setUserId(null);
      setActiveProjectId(null);
      localStorage.removeItem('activeProjectId');
      localStorage.removeItem('userId');
      return;
    }
    setUserId(uid);
    localStorage.setItem('userId', uid);
    // Restore persisted project only if it was saved for this same user
    const storedProject = localStorage.getItem('activeProjectId');
    const storedUser = localStorage.getItem('userId');
    if (storedProject && (storedUser === uid || uid === DEMO_USER_ID)) {
      setActiveProjectId(storedProject);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      try {
        // Check demo session first
        if (localStorage.getItem('demoSession')) {
          applyUser(DEMO_USER_ID);
          setIsLoading(false);
          return;
        }
        // Check real Supabase session
        const { data: { session } } = await supabase.auth.getSession();
        applyUser(session?.user?.id || null);
      } catch (err) {
        console.warn('Session init failed:', err);
        applyUser(null);
      } finally {
        setIsLoading(false);
      }
    };
    init();
  }, [applyUser]);

  // Listen for Supabase auth state changes (sign in / sign out / token refresh)
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      // If demo session active, ignore Supabase changes
      if (localStorage.getItem('demoSession')) return;
      applyUser(session?.user?.id || null);
    });
    return () => subscription.unsubscribe();
  }, [applyUser]);

  // Also listen for storage events (demo login triggers window.dispatchEvent('storage'))
  useEffect(() => {
    const onStorage = () => {
      if (localStorage.getItem('demoSession')) {
        applyUser(DEMO_USER_ID);
      } else if (!localStorage.getItem('demoSession') && userId === DEMO_USER_ID) {
        applyUser(null);
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [applyUser, userId]);

  // Persist activeProjectId whenever it changes
  useEffect(() => {
    if (isLoading) return;
    if (activeProjectId) {
      localStorage.setItem('activeProjectId', activeProjectId);
    } else {
      localStorage.removeItem('activeProjectId');
    }
  }, [activeProjectId, isLoading]);

  const setProject = (projectId) => setActiveProjectId(projectId);
  const clearProject = () => setActiveProjectId(null);
  const setUser = (uid) => applyUser(uid);

  return (
    <ActiveProjectContext.Provider value={{
      activeProjectId,
      userId,
      setProject,
      clearProject,
      setUser,
      isLoading,
    }}>
      {children}
    </ActiveProjectContext.Provider>
  );
}

export function useActiveProject() {
  const context = useContext(ActiveProjectContext);
  if (!context) throw new Error('useActiveProject must be used within ActiveProjectProvider');
  return context;
}
