import { useEffect } from 'react';
import { Outlet, useParams } from 'react-router-dom';
import { usePursuit } from '../hooks/usePursuit';
import { usePursuitStore } from '../stores/pursuitStore';
import { useCoachingStore } from '../stores/coachingStore';
import { useUIStore } from '../stores/uiStore';
import { LoadingSpinner } from '../components/LoadingSpinner';

export default function PursuitPage() {
  const { id } = useParams();
  const { pursuit, isLoading, error } = usePursuit(id);
  const setActivePursuit = usePursuitStore((s) => s.setActivePursuit);
  const clearMessages = useCoachingStore((s) => s.clearMessages);
  const openRightSidebarForPursuit = useUIStore((s) => s.openRightSidebarForPursuit);

  // Set active pursuit and clear previous chat state on mount/change
  useEffect(() => {
    setActivePursuit(id);
    clearMessages();
    // Auto-open right sidebar when viewing a pursuit (desktop only)
    openRightSidebarForPursuit();

    return () => {
      // Don't clear active pursuit on unmount - sidebar handles navigation
    };
  }, [id, setActivePursuit, clearMessages, openRightSidebarForPursuit]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !pursuit) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="text-display-sm text-zinc-400 mb-3">Pursuit Not Found</div>
        <p className="text-body-md text-zinc-500 max-w-md">
          The pursuit you're looking for doesn't exist or you don't have access to it.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 flex flex-col">
      <div className="flex-1 min-h-0 overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
