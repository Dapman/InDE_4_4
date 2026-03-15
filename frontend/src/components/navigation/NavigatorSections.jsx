/*
 * NavigatorSections - v4.3 Goal-language navigation sections
 *
 * Replaces module-named sections with goal-language equivalents:
 *   "Tell Your Story"       - Vision, storytelling, impact
 *   "Protect Your Idea"     - Fear extraction, risk assessment
 *   "Test Your Assumptions" - Hypothesis, experiments, validation
 *   "Sharpen and Refine"    - Differentiation, MVP scope, refinement
 *   "Prepare to Launch"     - Pitch preparation, stakeholder readiness
 *
 * Experience mode behavior:
 *   - novice: shows only active section (current work)
 *   - intermediate: shows current + adjacent sections
 *   - expert: shows all sections with methodology labels
 */
import { useMemo } from 'react';
import { useExperienceMode } from '../../context/ExperienceContext';
import {
  MessageSquare,
  Shield,
  Beaker,
  Sparkles,
  Rocket,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// Goal-language section definitions
const NAVIGATION_SECTIONS = [
  {
    key: 'tell_your_story',
    label: 'Tell Your Story',
    icon: MessageSquare,
    expertLabel: 'Vision Formulation',
    items: ['vision', 'impact', 'target_persona'],
  },
  {
    key: 'protect_your_idea',
    label: 'Protect Your Idea',
    icon: Shield,
    expertLabel: 'Risk Extraction',
    items: ['fear', 'risk_assessment', 'contingency'],
  },
  {
    key: 'test_your_assumptions',
    label: 'Test Your Assumptions',
    icon: Beaker,
    expertLabel: 'Validation Engine',
    items: ['hypothesis', 'experiment', 'evidence'],
  },
  {
    key: 'sharpen_and_refine',
    label: 'Sharpen and Refine',
    icon: Sparkles,
    expertLabel: 'Differentiation',
    items: ['value_prop', 'differentiation', 'mvp_scope'],
  },
  {
    key: 'prepare_to_launch',
    label: 'Prepare to Launch',
    icon: Rocket,
    expertLabel: 'Pitch Orchestration',
    items: ['pitch', 'stakeholder', 'launch_plan'],
  },
];

export function NavigatorSections({
  activeSectionKey,
  onSectionClick,
  compact = false,
}) {
  const { experienceMode, isNovice, isExpert } = useExperienceMode();

  // Determine which sections to show based on experience mode
  const visibleSections = useMemo(() => {
    if (isExpert) {
      // Expert: show all sections
      return NAVIGATION_SECTIONS;
    }

    if (isNovice) {
      // Novice: show only active section or first section
      const activeIndex = NAVIGATION_SECTIONS.findIndex(
        (s) => s.key === activeSectionKey
      );
      if (activeIndex >= 0) {
        return [NAVIGATION_SECTIONS[activeIndex]];
      }
      return [NAVIGATION_SECTIONS[0]];
    }

    // Intermediate: show active + adjacent sections
    const activeIndex = NAVIGATION_SECTIONS.findIndex(
      (s) => s.key === activeSectionKey
    );
    const start = Math.max(0, activeIndex - 1);
    const end = Math.min(NAVIGATION_SECTIONS.length, activeIndex + 2);
    return NAVIGATION_SECTIONS.slice(start, end);
  }, [experienceMode, activeSectionKey, isNovice, isExpert]);

  return (
    <div className={cn('space-y-1', compact && 'space-y-0.5')}>
      {visibleSections.map((section) => {
        const Icon = section.icon;
        const isActive = section.key === activeSectionKey;
        const label = isExpert ? section.expertLabel : section.label;

        return (
          <button
            key={section.key}
            onClick={() => onSectionClick?.(section.key)}
            className={cn(
              'w-full flex items-center gap-2 rounded-lg transition-colors text-left',
              compact ? 'px-2 py-1.5' : 'px-3 py-2',
              isActive
                ? 'bg-inde-500/10 text-inde-400'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-surface-4'
            )}
          >
            <Icon
              className={cn(
                'flex-shrink-0',
                compact ? 'w-4 h-4' : 'w-5 h-5'
              )}
            />
            <span
              className={cn(
                'truncate',
                compact ? 'text-caption' : 'text-body-sm'
              )}
            >
              {label}
            </span>
            {isActive && !compact && (
              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-inde-400" />
            )}
          </button>
        );
      })}

      {/* Show expansion indicator for novice/intermediate modes */}
      {!isExpert && visibleSections.length < NAVIGATION_SECTIONS.length && (
        <div className="px-3 py-1">
          <span className="text-caption text-zinc-600">
            {NAVIGATION_SECTIONS.length - visibleSections.length} more sections
          </span>
        </div>
      )}
    </div>
  );
}

// Export section keys for use by other components
export const SECTION_KEYS = NAVIGATION_SECTIONS.map((s) => s.key);
export { NAVIGATION_SECTIONS };
