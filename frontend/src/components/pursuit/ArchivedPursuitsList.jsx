/**
 * ArchivedPursuitsList Component
 * Displays archived pursuits with restore functionality.
 *
 * v3.13: Innovator Experience Polish
 */

import { useState, useEffect } from 'react';
import { Archive, ArchiveRestore, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../lib/utils';

export default function ArchivedPursuitsList({ onRestored }) {
  const [pursuits, setPursuits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [restoringId, setRestoringId] = useState(null);
  const [total, setTotal] = useState(0);
  const token = useAuthStore((state) => state.token);

  const fetchArchivedPursuits = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/pursuits/archived/list', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch archived pursuits');
      }

      const data = await response.json();
      setPursuits(data.pursuits || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError('Unable to load archived pursuits');
      console.error('Fetch archived pursuits failed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchArchivedPursuits();
    }
  }, [token]);

  const handleRestore = async (pursuitId) => {
    setRestoringId(pursuitId);

    try {
      const response = await fetch(`/api/pursuits/${pursuitId}/restore`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to restore pursuit');
      }

      // Remove from list
      setPursuits((prev) => prev.filter((p) => p.pursuit_id !== pursuitId));
      setTotal((prev) => prev - 1);

      // Notify parent
      if (onRestored) {
        onRestored(pursuitId);
      }
    } catch (err) {
      setError('Failed to restore pursuit');
      console.error('Restore failed:', err);
    } finally {
      setRestoringId(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="h-5 w-5 animate-spin text-zinc-500" />
        <span className="ml-2 text-zinc-500">Loading archived pursuits...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Archive className="h-5 w-5 text-zinc-500" />
          <h3 className="text-body-lg text-zinc-200">Archived Pursuits</h3>
          <span className="text-caption text-zinc-500">({total})</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchArchivedPursuits}
          className="text-zinc-400 hover:text-zinc-200"
        >
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <AlertCircle className="h-4 w-4 text-red-400" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {/* Empty state */}
      {pursuits.length === 0 ? (
        <div className="text-center py-8 text-zinc-500">
          <Archive className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="text-body-sm">No archived pursuits</p>
          <p className="text-caption mt-1">
            Archive a pursuit to remove it from your workspace while keeping all its data.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {pursuits.map((pursuit) => (
            <div
              key={pursuit.pursuit_id}
              className={cn(
                'flex items-center justify-between p-4 rounded-lg border',
                'bg-surface-3 border-surface-border/50 hover:border-surface-border'
              )}
            >
              <div className="flex-1 min-w-0">
                <h4 className="text-body-sm text-zinc-200 truncate">
                  {pursuit.title}
                </h4>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-caption text-zinc-500">
                    {pursuit.status}
                  </span>
                  <span className="text-caption text-zinc-600">
                    Archived {formatDate(pursuit.archived_at)}
                  </span>
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handleRestore(pursuit.pursuit_id)}
                disabled={restoringId === pursuit.pursuit_id}
                className="ml-4 text-inde-400 border-inde-400/30 hover:bg-inde-400/10"
              >
                {restoringId === pursuit.pursuit_id ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <ArchiveRestore className="h-4 w-4 mr-1" />
                    Restore
                  </>
                )}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
