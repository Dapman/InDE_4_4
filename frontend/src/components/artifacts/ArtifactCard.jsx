/**
 * ArtifactCard - Inline clickable card for artifacts in coaching messages
 *
 * Displays a compact card representing an artifact that can be clicked
 * to open the full artifact popup viewer.
 */

import { motion } from 'framer-motion';
import {
  Lightbulb,
  Megaphone,
  Target,
  FlaskConical,
  AlertTriangle,
  FileText,
  BarChart3,
  LineChart,
  PieChart,
  BarChart2,
  Grid3X3,
  Table2,
  Grid2X2,
  Table,
  ClipboardList,
  FileInput,
  File,
  ExternalLink,
  Loader2,
  Check,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { getArtifactIcon, getRendererCategory } from '../../lib/artifactParser';

// Icon component mapping
const ICON_COMPONENTS = {
  Lightbulb,
  Megaphone,
  Target,
  FlaskConical,
  AlertTriangle,
  FileText,
  BarChart3,
  LineChart,
  PieChart,
  BarChart2,
  Grid3X3,
  Table2,
  Grid2X2,
  Table,
  ClipboardList,
  FileInput,
  File,
};

// Category colors
const CATEGORY_COLORS = {
  text: 'from-blue-500/20 to-violet-500/20 border-blue-500/30',
  chart: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/30',
  positioning: 'from-orange-500/20 to-amber-500/20 border-orange-500/30',
  matrix: 'from-purple-500/20 to-pink-500/20 border-purple-500/30',
  form: 'from-cyan-500/20 to-sky-500/20 border-cyan-500/30',
};

const CATEGORY_ICON_COLORS = {
  text: 'text-blue-400',
  chart: 'text-emerald-400',
  positioning: 'text-orange-400',
  matrix: 'text-purple-400',
  form: 'text-cyan-400',
};

export function ArtifactCard({
  artifact,
  onClick,
  isSaving = false,
  isSaved = false,
  className,
}) {
  const iconName = getArtifactIcon(artifact.type);
  const IconComponent = ICON_COMPONENTS[iconName] || File;
  const category = getRendererCategory(artifact.type);
  const colorClass = CATEGORY_COLORS[category] || CATEGORY_COLORS.text;
  const iconColorClass = CATEGORY_ICON_COLORS[category] || CATEGORY_ICON_COLORS.text;

  // Format type for display
  const typeLabel = artifact.type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className={cn(
        'w-full my-3 p-4 rounded-lg border bg-gradient-to-br',
        'flex items-start gap-3 text-left',
        'transition-all duration-200 cursor-pointer',
        'hover:shadow-lg hover:shadow-inde-500/10',
        colorClass,
        className
      )}
    >
      {/* Icon */}
      <div className={cn(
        'flex-shrink-0 w-10 h-10 rounded-lg',
        'bg-surface-3 flex items-center justify-center'
      )}>
        <IconComponent className={cn('w-5 h-5', iconColorClass)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h4 className="text-body-sm font-medium text-zinc-200 truncate">
            {artifact.title}
          </h4>
          {isSaving && (
            <Loader2 className="w-3 h-3 text-zinc-500 animate-spin flex-shrink-0" />
          )}
          {isSaved && !isSaving && (
            <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
          )}
        </div>
        <p className="text-caption text-zinc-500">
          {typeLabel}
        </p>
      </div>

      {/* View indicator */}
      <div className="flex-shrink-0 flex items-center gap-1 text-caption text-zinc-500">
        <span>View</span>
        <ExternalLink className="w-3 h-3" />
      </div>
    </motion.button>
  );
}

export default ArtifactCard;
