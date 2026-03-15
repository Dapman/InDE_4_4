/**
 * Theme management.
 * - Detects system preference on first load
 * - Persists preference (in-memory via Zustand -- no localStorage in Anthropic env)
 * - Applies 'dark' or 'light' class to <html>
 */

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === 'dark') {
    root.classList.add('dark');
    root.classList.remove('light');
  } else {
    root.classList.add('light');
    root.classList.remove('dark');
  }
}

export function getSystemPreference() {
  if (window.matchMedia?.('(prefers-color-scheme: light)').matches) {
    return 'light';
  }
  return 'dark';
}

export function initializeTheme(preferredTheme) {
  // Use preferred theme if set, otherwise detect system preference
  const theme = preferredTheme || getSystemPreference();
  applyTheme(theme);
  return theme;
}
