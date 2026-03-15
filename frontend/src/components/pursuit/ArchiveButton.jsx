/**
 * ArchiveButton Component
 * Allows archiving/restoring pursuits from the workspace.
 *
 * v3.13: Innovator Experience Polish
 */

import { useState } from 'react';
import { Archive, ArchiveRestore, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';
import { useAuthStore } from '../../stores/authStore';

export default function ArchiveButton({
  pursuitId,
  isArchived = false,
  onArchive,
  onRestore,
  variant = 'ghost',
  size = 'icon',
  showLabel = false,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const token = useAuthStore((state) => state.token);

  const handleAction = async (e) => {
    e?.stopPropagation?.();
    e?.preventDefault?.();

    console.log('[ArchiveButton] Starting action for pursuit:', pursuitId);
    console.log('[ArchiveButton] isArchived:', isArchived);
    console.log('[ArchiveButton] token present:', !!token);

    if (!pursuitId) {
      console.error('[ArchiveButton] No pursuit ID!');
      setError('No pursuit selected');
      return;
    }

    if (!token) {
      console.error('[ArchiveButton] No auth token!');
      setError('Please log in again');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const endpoint = isArchived
        ? `/api/pursuits/${pursuitId}/restore`
        : `/api/pursuits/${pursuitId}/archive`;

      console.log('[ArchiveButton] Calling endpoint:', endpoint);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      console.log('[ArchiveButton] Response status:', response.status);

      if (!response.ok) {
        const data = await response.json();
        console.error('[ArchiveButton] Error response:', data);
        throw new Error(data.detail || 'Action failed');
      }

      const data = await response.json();
      console.log('[ArchiveButton] Success response:', data);

      // Call the appropriate callback
      if (isArchived && onRestore) {
        console.log('[ArchiveButton] Calling onRestore callback');
        onRestore(pursuitId, data);
      } else if (!isArchived && onArchive) {
        console.log('[ArchiveButton] Calling onArchive callback');
        onArchive(pursuitId, data);
      }
    } catch (err) {
      setError(err.message);
      console.error('[ArchiveButton] Archive/restore failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const Icon = isArchived ? ArchiveRestore : Archive;
  const label = isArchived ? 'Restore to workspace' : 'Archive';
  const tooltipText = isArchived
    ? 'Restore this pursuit to your active workspace'
    : 'Archive this pursuit (data is preserved)';

  if (showLabel) {
    return (
      <Button
        variant={variant}
        size="sm"
        onClick={handleAction}
        disabled={loading}
        className={isArchived ? 'text-inde-400' : 'text-zinc-400 hover:text-zinc-200'}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Icon className="h-4 w-4 mr-1.5" />
        )}
        {label}
      </Button>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            onClick={handleAction}
            disabled={loading}
            className={isArchived ? 'text-inde-400 hover:text-inde-300' : 'text-zinc-500 hover:text-zinc-300'}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Icon className="h-4 w-4" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
