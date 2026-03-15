/**
 * SessionManagement Component
 * Displays active sessions and allows users to terminate them.
 *
 * v3.12: Account Trust & Completeness
 */

import { useState, useEffect } from 'react';
import { Monitor, Smartphone, Globe, Trash2, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';
import { useAuthStore } from '../../stores/authStore';

// Parse user agent to get readable device info
function parseDeviceInfo(userAgent) {
  if (!userAgent || userAgent === 'Unknown device') {
    return { type: 'unknown', name: 'Unknown Device' };
  }

  const ua = userAgent.toLowerCase();

  // Detect device type and browser
  let type = 'desktop';
  let browser = 'Browser';
  let os = 'Unknown';

  // OS detection
  if (ua.includes('windows')) os = 'Windows';
  else if (ua.includes('mac os') || ua.includes('macos')) os = 'macOS';
  else if (ua.includes('linux')) os = 'Linux';
  else if (ua.includes('android')) { os = 'Android'; type = 'mobile'; }
  else if (ua.includes('iphone') || ua.includes('ipad')) { os = 'iOS'; type = 'mobile'; }

  // Browser detection
  if (ua.includes('chrome') && !ua.includes('edge')) browser = 'Chrome';
  else if (ua.includes('firefox')) browser = 'Firefox';
  else if (ua.includes('safari') && !ua.includes('chrome')) browser = 'Safari';
  else if (ua.includes('edge')) browser = 'Edge';

  return { type, name: `${browser} on ${os}` };
}

export default function SessionManagement() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [terminating, setTerminating] = useState(null);
  const token = useAuthStore((state) => state.token);

  const fetchSessions = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/account/sessions', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch sessions');
      }

      const data = await response.json();
      setSessions(data);
    } catch (err) {
      setError('Unable to load sessions');
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchSessions();
    }
  }, [token]);

  const terminateSession = async (sessionId) => {
    setTerminating(sessionId);
    try {
      const response = await fetch(`/api/account/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to terminate session');
      }

      // Remove from list
      setSessions(sessions.filter(s => s.session_id !== sessionId));
    } catch (err) {
      setError('Failed to terminate session');
      console.error('Failed to terminate session:', err);
    } finally {
      setTerminating(null);
    }
  };

  const terminateAllOthers = async () => {
    setTerminating('all');
    try {
      const response = await fetch('/api/account/sessions', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to terminate sessions');
      }

      // Refresh the list
      await fetchSessions();
    } catch (err) {
      setError('Failed to terminate sessions');
      console.error('Failed to terminate sessions:', err);
    } finally {
      setTerminating(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="h-5 w-5 animate-spin text-zinc-500" />
        <span className="ml-2 text-zinc-500">Loading sessions...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with refresh and terminate all */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchSessions}
            className="text-zinc-400 hover:text-zinc-200"
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        </div>
        {sessions.length > 1 && (
          <Button
            variant="outline"
            size="sm"
            onClick={terminateAllOthers}
            disabled={terminating === 'all'}
            className="text-amber-400 border-amber-400/30 hover:bg-amber-400/10"
          >
            {terminating === 'all' ? 'Signing out...' : 'Sign out all other devices'}
          </Button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <AlertCircle className="h-4 w-4 text-red-400" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {/* Sessions list */}
      {sessions.length === 0 ? (
        <p className="text-zinc-500 text-center py-4">No active sessions found</p>
      ) : (
        <div className="space-y-2">
          {sessions.map((session, index) => {
            const device = parseDeviceInfo(session.device_info);
            const DeviceIcon = device.type === 'mobile' ? Smartphone : Monitor;
            const isFirst = index === 0;

            return (
              <div
                key={session.session_id}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg border',
                  isFirst
                    ? 'bg-inde-500/10 border-inde-500/30'
                    : 'bg-surface-3 border-surface-border/50'
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    'p-2 rounded-lg',
                    isFirst ? 'bg-inde-500/20' : 'bg-surface-4'
                  )}>
                    <DeviceIcon className={cn(
                      'h-5 w-5',
                      isFirst ? 'text-inde-400' : 'text-zinc-400'
                    )} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-body-sm text-zinc-200">{device.name}</span>
                      {isFirst && (
                        <span className="px-1.5 py-0.5 text-xs bg-inde-500/20 text-inde-400 rounded">
                          This device
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-caption text-zinc-500 flex items-center gap-1">
                        <Globe className="h-3 w-3" />
                        {session.ip_address || 'Unknown IP'}
                      </span>
                      <span className="text-caption text-zinc-600">
                        {formatDate(session.created_at)}
                      </span>
                    </div>
                  </div>
                </div>

                {!isFirst && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => terminateSession(session.session_id)}
                    disabled={terminating === session.session_id}
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  >
                    {terminating === session.session_id ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}

      <p className="text-caption text-zinc-600 mt-4">
        Active sessions may take up to 30 minutes to fully terminate after signing out.
      </p>
    </div>
  );
}
