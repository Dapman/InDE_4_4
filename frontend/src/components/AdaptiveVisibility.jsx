import { useUIStore } from '../stores/uiStore';

/**
 * Conditionally renders children based on complexity tier.
 *
 * @param {string} minTier - Minimum tier to show content ('guided' | 'standard' | 'streamlined' | 'minimal')
 * @param {string} maxTier - Maximum tier to show content (default: 'minimal')
 * @param {ReactNode} children - Content to conditionally render
 * @param {ReactNode} fallback - Optional fallback content when not visible
 *
 * @example
 * <AdaptiveVisibility minTier="guided" maxTier="standard">
 *   <Tooltip>This only shows for novice and competent users</Tooltip>
 * </AdaptiveVisibility>
 *
 * @example
 * <AdaptiveVisibility minTier="streamlined">
 *   <KeyboardHint>⌘K for commands</KeyboardHint>
 * </AdaptiveVisibility>
 */
export function AdaptiveVisibility({
  minTier = 'guided',
  maxTier = 'minimal',
  children,
  fallback = null
}) {
  const complexityTier = useUIStore((s) => s.complexityTier);

  const tiers = ['guided', 'standard', 'streamlined', 'minimal'];
  const currentIdx = tiers.indexOf(complexityTier);
  const minIdx = tiers.indexOf(minTier);
  const maxIdx = tiers.indexOf(maxTier);

  const isVisible = currentIdx >= minIdx && currentIdx <= maxIdx;

  return isVisible ? children : fallback;
}

/**
 * Show content only for guided (novice) users
 */
export function GuidedOnly({ children, fallback = null }) {
  return (
    <AdaptiveVisibility minTier="guided" maxTier="guided" fallback={fallback}>
      {children}
    </AdaptiveVisibility>
  );
}

/**
 * Show content only for expert/streamlined users
 */
export function ExpertOnly({ children, fallback = null }) {
  return (
    <AdaptiveVisibility minTier="streamlined" maxTier="minimal" fallback={fallback}>
      {children}
    </AdaptiveVisibility>
  );
}

/**
 * Show content for standard and above (hide from guided)
 */
export function StandardAndAbove({ children, fallback = null }) {
  return (
    <AdaptiveVisibility minTier="standard" maxTier="minimal" fallback={fallback}>
      {children}
    </AdaptiveVisibility>
  );
}

/**
 * Show content for guided and standard (hide from expert)
 */
export function BeginnerFriendly({ children, fallback = null }) {
  return (
    <AdaptiveVisibility minTier="guided" maxTier="standard" fallback={fallback}>
      {children}
    </AdaptiveVisibility>
  );
}

export default AdaptiveVisibility;
