import { useEffect, useCallback } from 'react';

/**
 * Register a keyboard shortcut.
 *
 * Usage:
 *   useKeyboardShortcut('k', { meta: true }, () => openCommandPalette());
 *   useKeyboardShortcut('Escape', {}, () => closeModal());
 */
export function useKeyboardShortcut(key, modifiers = {}, callback) {
  const handleKeyDown = useCallback(
    (event) => {
      // Check if we're in an input or textarea
      const target = event.target;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // Allow Escape to work everywhere, but other shortcuts only outside inputs
      if (isInput && key.toLowerCase() !== 'escape') {
        return;
      }

      const metaMatch = modifiers.meta ? event.metaKey || event.ctrlKey : !event.metaKey && !event.ctrlKey;
      const shiftMatch = modifiers.shift ? event.shiftKey : !modifiers.shift || !event.shiftKey;
      const altMatch = modifiers.alt ? event.altKey : !modifiers.alt || !event.altKey;

      // Handle special case where we explicitly want meta to be false
      const metaRequired = modifiers.meta === true;
      const metaForbidden = modifiers.meta === false;

      let metaOk = true;
      if (metaRequired) {
        metaOk = event.metaKey || event.ctrlKey;
      } else if (metaForbidden) {
        metaOk = !event.metaKey && !event.ctrlKey;
      }

      if (
        event.key.toLowerCase() === key.toLowerCase() &&
        metaOk &&
        (modifiers.shift ? event.shiftKey : true) &&
        (modifiers.alt ? event.altKey : true)
      ) {
        event.preventDefault();
        callback();
      }
    },
    [key, modifiers, callback]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

/**
 * Register multiple keyboard shortcuts.
 *
 * Usage:
 *   useKeyboardShortcuts([
 *     { key: 'k', modifiers: { meta: true }, callback: openPalette },
 *     { key: 'Escape', callback: closePalette },
 *   ]);
 */
export function useKeyboardShortcuts(shortcuts) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      const target = event.target;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      for (const { key, modifiers = {}, callback } of shortcuts) {
        if (isInput && key.toLowerCase() !== 'escape') {
          continue;
        }

        const metaRequired = modifiers.meta === true;
        let metaOk = true;
        if (metaRequired) {
          metaOk = event.metaKey || event.ctrlKey;
        }

        if (
          event.key.toLowerCase() === key.toLowerCase() &&
          metaOk &&
          (modifiers.shift ? event.shiftKey : true) &&
          (modifiers.alt ? event.altKey : true)
        ) {
          event.preventDefault();
          callback();
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}
