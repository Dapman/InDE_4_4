/*
 * ExperienceModeToggle - Settings UI for experience_mode preference
 *
 * Displays 3 options with Display Label Registry copy:
 *   - novice:       "Show me depth and richness"
 *   - intermediate: "Show me steps and depth"
 *   - expert:       "Show me phases and detail"
 *
 * Changes are persisted immediately via ExperienceContext.
 */
import { useExperienceMode } from '../../context/ExperienceContext';
import { cn } from '../../lib/utils';

const MODE_OPTIONS = [
  {
    value: 'novice',
    label: 'Show me depth and richness',
    description: 'Progress shown as how rich and specific your idea is becoming.',
  },
  {
    value: 'intermediate',
    label: 'Show me steps and depth',
    description: 'Combination of depth language and progress milestones.',
  },
  {
    value: 'expert',
    label: 'Show me phases and detail',
    description: 'Full methodology visibility including phase indicators.',
  },
];

export function ExperienceModeToggle() {
  const { experienceMode, setExperienceMode } = useExperienceMode();

  return (
    <div className="space-y-2">
      <label className="block text-body-sm text-zinc-400 mb-3">
        How would you like to see your progress?
      </label>

      <div className="space-y-2">
        {MODE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setExperienceMode(option.value)}
            className={cn(
              'w-full p-3 rounded-lg border text-left transition-colors',
              experienceMode === option.value
                ? 'border-inde-500 bg-inde-500/10'
                : 'border-surface-border hover:border-surface-border-light bg-surface-3'
            )}
          >
            <div className="flex items-center gap-3">
              {/* Radio indicator */}
              <div
                className={cn(
                  'w-4 h-4 rounded-full border-2 flex-shrink-0',
                  experienceMode === option.value
                    ? 'border-inde-500 bg-inde-500'
                    : 'border-zinc-600'
                )}
              >
                {experienceMode === option.value && (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-white" />
                  </div>
                )}
              </div>

              <div>
                <div className="text-body-sm text-zinc-200">{option.label}</div>
                <div className="text-caption text-zinc-500 mt-0.5">
                  {option.description}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
