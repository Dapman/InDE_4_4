/**
 * HintCard - A dismissable hint card for empty or first-use workspace zones.
 *
 * v3.15: Part of the Guided Discovery Layer for first-time users.
 * Disappears after the user dismisses it or engages with the zone.
 */

import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

export function HintCard({ hintId, icon: Icon, message, onDismiss, className }) {
  return (
    <div
      className={cn(
        'relative flex items-start gap-3 p-4 bg-inde-500/5 border border-inde-500/20 rounded-lg',
        className
      )}
      role="note"
    >
      {Icon && (
        <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-inde-500/10 rounded-lg">
          <Icon className="w-4 h-4 text-inde-400" />
        </div>
      )}

      <p className="flex-1 text-body-sm text-zinc-400 leading-relaxed pr-6">
        {message}
      </p>

      <button
        className="absolute top-2 right-2 p-1 text-zinc-600 hover:text-zinc-400 transition-colors"
        aria-label="Dismiss this hint"
        onClick={() => onDismiss?.(hintId)}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export default HintCard;
