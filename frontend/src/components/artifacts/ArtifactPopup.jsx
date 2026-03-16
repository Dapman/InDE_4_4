/**
 * ArtifactPopup - Full-screen modal for viewing artifact content
 *
 * Uses the Radix UI Dialog primitive to display artifacts with
 * type-specific rich rendering.
 */

import { useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Printer, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getRendererCategory } from '../../lib/artifactParser';
import { ArtifactRenderer } from './ArtifactRenderer';
import { printArtifact } from '../../lib/print';

// Category badge colors
const CATEGORY_BADGES = {
  text: 'bg-blue-500/20 text-blue-400',
  chart: 'bg-emerald-500/20 text-emerald-400',
  positioning: 'bg-orange-500/20 text-orange-400',
  matrix: 'bg-purple-500/20 text-purple-400',
  form: 'bg-cyan-500/20 text-cyan-400',
};

export function ArtifactPopup({
  artifact,
  isOpen,
  onClose,
  pursuitId,
}) {
  const category = getRendererCategory(artifact?.type);
  const badgeClass = CATEGORY_BADGES[category] || CATEGORY_BADGES.text;

  // Format type for display
  const typeLabel = artifact?.type
    ?.replace(/_/g, ' ')
    ?.replace(/\b\w/g, c => c.toUpperCase()) || 'Artifact';

  // Handle print
  const handlePrint = useCallback(() => {
    if (!artifact) return;

    const printContent = {
      title: artifact.title,
      type: typeLabel,
      content: artifact.data || artifact.content,
      createdAt: artifact.createdAt,
    };

    printArtifact(printContent);
  }, [artifact, typeLabel]);

  if (!artifact) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl w-[90vw] max-h-[85vh] flex flex-col bg-surface-2 border-surface-border p-0 gap-0">
        {/* Header */}
        <DialogHeader className="flex-shrink-0 px-6 py-4 border-b border-surface-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <DialogTitle className="text-lg font-semibold text-zinc-100">
                {artifact.title}
              </DialogTitle>
              <span className={cn(
                'px-2 py-0.5 rounded-full text-caption font-medium',
                badgeClass
              )}>
                {typeLabel}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePrint}
                className="text-zinc-400 hover:text-zinc-200"
              >
                <Printer className="w-4 h-4 mr-1" />
                Print
              </Button>
            </div>
          </div>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 py-6">
          <ArtifactRenderer artifact={artifact} />
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 px-6 py-3 border-t border-surface-border bg-surface-3/50">
          <div className="flex items-center justify-between text-caption text-zinc-500">
            <span>
              {artifact.createdAt && (
                <>Created: {new Date(artifact.createdAt).toLocaleString()}</>
              )}
            </span>
            <span className="text-zinc-600">View Only</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default ArtifactPopup;
