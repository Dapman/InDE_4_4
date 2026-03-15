import { useDisplayLabel } from '../hooks/useDisplayLabel';
import { cn } from '../lib/utils';

/**
 * Renders a Display Label with optional icon.
 * Falls back to humanized raw value if label not found.
 */
export function DisplayLabel({ category, value, showIcon = true, className }) {
  const { label, icon } = useDisplayLabel(category, value);

  return (
    <span className={cn('inline-flex items-center gap-1', className)}>
      {showIcon && icon && <span>{icon}</span>}
      <span>{label}</span>
    </span>
  );
}

export default DisplayLabel;
