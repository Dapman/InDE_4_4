/**
 * NotificationPreferences Component
 * Settings panel for controlling notification behavior.
 *
 * v3.13: Innovator Experience Polish
 */

import { useState, useEffect, useCallback } from 'react';
import { Bell, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../lib/utils';

// Debounce hook for auto-save
function useDebounce(callback, delay) {
  const [pending, setPending] = useState(false);

  const debouncedCallback = useCallback((...args) => {
    setPending(true);
    const timer = setTimeout(() => {
      callback(...args);
      setPending(false);
    }, delay);
    return () => clearTimeout(timer);
  }, [callback, delay]);

  return [debouncedCallback, pending];
}

export default function NotificationPreferences() {
  const [prefs, setPrefs] = useState({
    activity_feed: 'all',
    mentions: 'always',
    state_changes: true,
    new_members: true,
    contributions: 'direct_team',
    polling_interval_seconds: 30,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const token = useAuthStore((state) => state.token);

  const fetchPreferences = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/account/notification-preferences', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to load preferences');
      }

      const data = await response.json();
      setPrefs(data);
    } catch (err) {
      setError('Unable to load notification preferences');
      console.error('Fetch notification prefs failed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchPreferences();
    }
  }, [token]);

  const savePreferences = async (updates) => {
    setSaving(true);
    setError('');

    try {
      const response = await fetch('/api/account/notification-preferences', {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Save failed');
      }

      const data = await response.json();
      setPrefs(data);

      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError('Failed to save preferences');
      console.error('Save notification prefs failed:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key, value) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));
    // Auto-save after 500ms debounce
    const timer = setTimeout(() => {
      savePreferences({ [key]: value });
    }, 500);
    return () => clearTimeout(timer);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="h-5 w-5 animate-spin text-zinc-500" />
        <span className="ml-2 text-zinc-500">Loading preferences...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5 text-zinc-400" />
          <h3 className="text-body-lg text-zinc-200">Notification Preferences</h3>
        </div>
        {saved && (
          <span className="flex items-center gap-1 text-caption text-green-400">
            <CheckCircle className="h-3 w-3" />
            Saved
          </span>
        )}
        {saving && (
          <span className="flex items-center gap-1 text-caption text-zinc-500">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Saving...
          </span>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <AlertCircle className="h-4 w-4 text-red-400" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {/* Activity Feed */}
      <div className="space-y-2">
        <label className="text-body-sm text-zinc-300">Activity Feed</label>
        <select
          value={prefs.activity_feed}
          onChange={(e) => handleChange('activity_feed', e.target.value)}
          className="w-full px-3 py-2 bg-surface-3 border border-surface-border rounded-lg text-zinc-200 focus:outline-none focus:ring-1 focus:ring-inde-500"
        >
          <option value="all">All events</option>
          <option value="significant">Significant only</option>
          <option value="off">Off</option>
        </select>
        <p className="text-caption text-zinc-500">
          Control which events appear in your activity feed
        </p>
      </div>

      {/* Mentions */}
      <div className="space-y-2">
        <label className="text-body-sm text-zinc-300">@Mentions</label>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="mentions"
              checked={prefs.mentions === 'always'}
              onChange={() => handleChange('mentions', 'always')}
              className="w-4 h-4 text-inde-500 bg-surface-3 border-surface-border focus:ring-inde-500"
            />
            <span className="text-body-sm text-zinc-300">Always notify</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="mentions"
              checked={prefs.mentions === 'muted'}
              onChange={() => handleChange('mentions', 'muted')}
              className="w-4 h-4 text-inde-500 bg-surface-3 border-surface-border focus:ring-inde-500"
            />
            <span className="text-body-sm text-zinc-300">Muted</span>
          </label>
        </div>
      </div>

      {/* Toggles */}
      <div className="space-y-3">
        <ToggleOption
          label="Pursuit state changes"
          description="When a pursuit changes phase or status"
          checked={prefs.state_changes}
          onChange={(v) => handleChange('state_changes', v)}
        />
        <ToggleOption
          label="New team members"
          description="When someone joins your team"
          checked={prefs.new_members}
          onChange={(v) => handleChange('new_members', v)}
        />
      </div>

      {/* Contributions */}
      <div className="space-y-2">
        <label className="text-body-sm text-zinc-300">IKF Contributions</label>
        <select
          value={prefs.contributions}
          onChange={(e) => handleChange('contributions', e.target.value)}
          className="w-full px-3 py-2 bg-surface-3 border border-surface-border rounded-lg text-zinc-200 focus:outline-none focus:ring-1 focus:ring-inde-500"
        >
          <option value="all">All contributions</option>
          <option value="direct_team">Direct team only</option>
          <option value="off">Off</option>
        </select>
      </div>

      {/* Polling Interval */}
      <div className="space-y-2">
        <label className="text-body-sm text-zinc-300">Refresh Interval</label>
        <select
          value={prefs.polling_interval_seconds}
          onChange={(e) => handleChange('polling_interval_seconds', parseInt(e.target.value))}
          className="w-full px-3 py-2 bg-surface-3 border border-surface-border rounded-lg text-zinc-200 focus:outline-none focus:ring-1 focus:ring-inde-500"
        >
          <option value={15}>15 seconds</option>
          <option value={30}>30 seconds</option>
          <option value={60}>1 minute</option>
          <option value={120}>2 minutes</option>
        </select>
        <p className="text-caption text-zinc-500">
          How often to check for new notifications
        </p>
      </div>
    </div>
  );
}

function ToggleOption({ label, description, checked, onChange }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-surface-border/30">
      <div>
        <span className="text-body-sm text-zinc-300">{label}</span>
        {description && (
          <p className="text-caption text-zinc-500">{description}</p>
        )}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={cn(
          'relative w-11 h-6 rounded-full transition-colors',
          checked ? 'bg-inde-500' : 'bg-surface-4'
        )}
      >
        <span
          className={cn(
            'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
            checked ? 'left-6' : 'left-1'
          )}
        />
      </button>
    </div>
  );
}
