/**
 * HelpTooltip - Contextual help icon that shows a brief explanation on hover/click.
 *
 * v3.15: Part of the Guided Discovery Layer for first-time users.
 */

import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

export function HelpTooltip({ title, helpText, placement = 'right' }) {
  const [visible, setVisible] = useState(false);

  const placementClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div className="relative inline-flex">
      <button
        className="p-1 text-zinc-500 hover:text-zinc-300 hover:bg-surface-4 rounded transition-colors"
        aria-label={`Help: ${title}`}
        onClick={() => setVisible((v) => !v)}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
      >
        <HelpCircle className="w-4 h-4" />
      </button>

      {visible && (
        <div
          className={cn(
            'absolute z-50 w-64 p-3 bg-surface-3 border border-surface-border rounded-lg shadow-lg',
            placementClasses[placement] || placementClasses.right
          )}
        >
          {title && (
            <div className="text-body-sm font-medium text-zinc-200 mb-1">
              {title}
            </div>
          )}
          <p className="text-caption text-zinc-400 leading-relaxed">{helpText}</p>
        </div>
      )}
    </div>
  );
}

export default HelpTooltip;
