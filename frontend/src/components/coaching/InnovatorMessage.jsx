import { motion } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';
import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuthStore } from '../../stores/authStore';

export function InnovatorMessage({ message, className }) {
  const { content, timestamp } = message;
  const user = useAuthStore((s) => s.user);

  // Generate initials from user name or email
  const getInitials = () => {
    if (user?.name) {
      return user.name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase();
    }
    if (user?.email) {
      return user.email.slice(0, 2).toUpperCase();
    }
    return 'ME';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={cn('flex gap-3 items-start flex-row-reverse', className)}
    >
      {/* User avatar */}
      <div className="w-8 h-8 rounded-lg bg-surface-4 flex items-center justify-center flex-shrink-0">
        <span className="text-zinc-300 text-xs font-bold font-display">
          {getInitials()}
        </span>
      </div>

      {/* Message bubble */}
      <div className="max-w-[90%] sm:max-w-[75%] min-w-0">
        <div className="bg-inde-500/10 border border-inde-500/20 rounded-tl-panel rounded-b-panel px-4 py-3">
          <p className="text-body-md text-zinc-200 whitespace-pre-wrap break-words">
            {content}
          </p>
        </div>

        {/* Timestamp and sent indicator */}
        <div className="mt-1.5 flex items-center justify-end gap-2">
          {timestamp && (
            <span className="text-caption text-zinc-600">
              {formatDistanceToNow(new Date(timestamp), { addSuffix: true })}
            </span>
          )}
          <Check className="w-3.5 h-3.5 text-zinc-600" />
        </div>
      </div>
    </motion.div>
  );
}

export default InnovatorMessage;
