/**
 * GettingStartedChecklist - A sidebar widget showing pursuit setup progress.
 *
 * v3.15: Part of the Guided Discovery Layer for first-time users.
 * Collapses automatically when all items are complete.
 */

import { CheckCircle, Circle, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';

const CHECKLIST_ITEMS = [
  { key: 'vision_created', label: 'Describe your innovation idea' },
  { key: 'fear_identified', label: 'Identify a challenge or concern' },
  { key: 'methodology_selected', label: 'Choose your innovation approach' },
  { key: 'coaching_conversation_started', label: 'Have your first coaching conversation' },
  { key: 'first_artifact_generated', label: 'Generate your first artifact' },
];

export function GettingStartedChecklist({ discoveryState, isCollapsed = false }) {
  // If checklist is complete, show a minimal completed badge
  if (discoveryState?.checklist_complete) {
    if (isCollapsed) {
      return (
        <div className="flex justify-center py-2" title="Getting Started complete">
          <div className="w-8 h-8 flex items-center justify-center bg-emerald-500/10 rounded-lg">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2 px-3 py-2 text-caption text-emerald-400">
        <CheckCircle className="w-4 h-4" />
        <span>Getting Started complete</span>
      </div>
    );
  }

  const items = discoveryState?.checklist_items ?? {};
  const completedCount = CHECKLIST_ITEMS.filter((item) => items[item.key]).length;

  // Collapsed view - just show progress
  if (isCollapsed) {
    return (
      <div className="flex justify-center py-2" title={`Getting Started: ${completedCount}/${CHECKLIST_ITEMS.length}`}>
        <div className="w-8 h-8 flex items-center justify-center bg-inde-500/10 rounded-lg">
          <span className="text-xs font-medium text-inde-400">
            {completedCount}/{CHECKLIST_ITEMS.length}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 border-t border-surface-border">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-inde-400" />
        <span className="text-overline text-zinc-500 uppercase">Getting Started</span>
      </div>

      {/* Progress */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-caption text-zinc-500 mb-1">
          <span>{completedCount} of {CHECKLIST_ITEMS.length}</span>
          <span>{Math.round((completedCount / CHECKLIST_ITEMS.length) * 100)}%</span>
        </div>
        <div className="h-1 bg-surface-4 rounded-full overflow-hidden">
          <div
            className="h-full bg-inde-500 transition-all duration-300"
            style={{ width: `${(completedCount / CHECKLIST_ITEMS.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Checklist */}
      <ul className="space-y-2">
        {CHECKLIST_ITEMS.map((item) => {
          const isComplete = items[item.key];
          return (
            <li
              key={item.key}
              className={cn(
                'flex items-center gap-2 text-caption transition-colors',
                isComplete ? 'text-zinc-500' : 'text-zinc-400'
              )}
            >
              {isComplete ? (
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
              ) : (
                <Circle className="w-3.5 h-3.5 text-zinc-600 flex-shrink-0" />
              )}
              <span className={cn(isComplete && 'line-through')}>{item.label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default GettingStartedChecklist;
