/*
 * ExperienceContext - v4.3
 *
 * Provides experience_mode ('novice' | 'intermediate' | 'expert') to all
 * components that need to adapt their display. Reads from user preferences
 * on mount. Default: 'novice' (safe fallback).
 *
 * Usage:
 *   const { experienceMode, isNovice, isExpert } = useExperienceMode();
 */
import { createContext, useContext, useState, useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';

const ExperienceContext = createContext({
  experienceMode: 'novice',
  isNovice: true,
  isIntermediate: false,
  isExpert: false,
  setExperienceMode: () => {},
});

export function ExperienceProvider({ children }) {
  const [experienceMode, setExperienceMode] = useState('novice');
  const { token } = useAuthStore();

  useEffect(() => {
    if (!token) {
      setExperienceMode('novice');
      return;
    }

    // Load from preferences API on mount
    const loadPreferences = async () => {
      try {
        const response = await fetch('/api/auth/me', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (response.ok) {
          const userData = await response.json();
          const mode = userData.preferences?.experience_mode ?? 'novice';
          setExperienceMode(mode);
        }
      } catch (error) {
        console.warn('Could not load experience mode preference:', error);
        setExperienceMode('novice'); // safe fallback
      }
    };

    loadPreferences();
  }, [token]);

  const updateExperienceMode = async (newMode) => {
    setExperienceMode(newMode);

    // Persist to API
    if (token) {
      try {
        await fetch('/api/auth/preferences', {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ experience_mode: newMode }),
        });
      } catch (error) {
        console.warn('Could not save experience mode preference:', error);
      }
    }
  };

  return (
    <ExperienceContext.Provider
      value={{
        experienceMode,
        setExperienceMode: updateExperienceMode,
        isNovice: experienceMode === 'novice',
        isIntermediate: experienceMode === 'intermediate',
        isExpert: experienceMode === 'expert',
      }}
    >
      {children}
    </ExperienceContext.Provider>
  );
}

export const useExperienceMode = () => useContext(ExperienceContext);
