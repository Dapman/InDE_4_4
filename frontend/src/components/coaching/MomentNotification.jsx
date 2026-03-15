import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

const MOMENT_CONFIG = {
  TEACHING_MOMENT: {
    icon: '💡',
    label: 'Teaching Moment',
    accent: 'border-amber-500/50 bg-amber-500/5',
    iconBg: 'bg-amber-500/10',
  },
  FEAR_DETECTED: {
    icon: '🛡️',
    label: 'Concern Detected',
    accent: 'border-violet-500/50 bg-violet-500/5',
    iconBg: 'bg-violet-500/10',
  },
  READINESS_SIGNAL: {
    icon: '🚀',
    label: 'Readiness Signal',
    accent: 'border-emerald-500/50 bg-emerald-500/5',
    iconBg: 'bg-emerald-500/10',
  },
  HEALTH_WARNING: {
    icon: '⚠️',
    label: 'Health Warning',
    accent: 'border-rose-500/50 bg-rose-500/5',
    iconBg: 'bg-rose-500/10',
  },
  PORTFOLIO_INSIGHT: {
    icon: '📊',
    label: 'Portfolio Insight',
    accent: 'border-blue-500/50 bg-blue-500/5',
    iconBg: 'bg-blue-500/10',
  },
  EXPERIMENT_COMPLETE: {
    icon: '🧪',
    label: 'Experiment Complete',
    accent: 'border-emerald-500/50 bg-emerald-500/5',
    iconBg: 'bg-emerald-500/10',
  },
};

export function MomentNotification({ moment, onClick, className }) {
  const { type, content, data } = moment;
  const config = MOMENT_CONFIG[type] || MOMENT_CONFIG.TEACHING_MOMENT;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={cn('w-full', className)}
    >
      <button
        onClick={onClick}
        disabled={!onClick}
        className={cn(
          'w-full text-left border-l-2 rounded-r-card px-4 py-3 transition-colors',
          config.accent,
          onClick && 'hover:bg-surface-4/50 cursor-pointer'
        )}
      >
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div
            className={cn(
              'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
              config.iconBg
            )}
          >
            <span className="text-base">{config.icon}</span>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-body-sm font-medium text-zinc-300">
                {config.label}
              </span>
            </div>
            <p className="text-body-sm text-zinc-500 mt-0.5 line-clamp-2">
              {content}
            </p>
          </div>

          {/* Action hint */}
          {onClick && (
            <div className="flex-shrink-0 text-caption text-zinc-600">
              Click to explore
            </div>
          )}
        </div>
      </button>
    </motion.div>
  );
}

export default MomentNotification;
