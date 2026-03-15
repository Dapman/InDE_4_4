import { cn } from '../lib/utils';

export function LoadingSpinner({ size = 'md', className }) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
    xl: 'w-12 h-12 border-4',
  };

  return (
    <div
      className={cn(
        'animate-spin rounded-full border-t-transparent border-inde-500',
        sizeClasses[size],
        className
      )}
    />
  );
}

export function LoadingOverlay({ message = 'Loading...' }) {
  return (
    <div className="fixed inset-0 bg-surface-0/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="lg" />
        <p className="text-body-sm text-zinc-400">{message}</p>
      </div>
    </div>
  );
}

export function LoadingPlaceholder({ className }) {
  return (
    <div className={cn('flex items-center justify-center p-8', className)}>
      <LoadingSpinner size="md" />
    </div>
  );
}

export default LoadingSpinner;
