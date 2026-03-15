import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '../../lib/utils';
import { parseArtifactContent } from '../../lib/artifactParser';
import { ArtifactCard, ArtifactPopup } from '../artifacts';
import { usePursuitStore } from '../../stores/pursuitStore';
import { artifactsApi } from '../../api/artifacts';

// v4.0: Mode badges use innovator-facing goal vocabulary
const MODE_BADGES = {
  vision: { icon: '📖', label: 'Your Story' },
  fear: { icon: '🛡️', label: 'Protecting Your Idea' },
  retrospective: { icon: '💡', label: 'Lessons Learned' },
  ems_review: { icon: '✨', label: 'Your Methodology' },
};

export function CoachMessage({ message, className }) {
  const { content, timestamp, mode } = message;
  const modeBadge = mode && mode !== 'coaching' ? MODE_BADGES[mode] : null;
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const activePursuitId = usePursuitStore((state) => state.activePursuitId);

  // Parse content for artifacts
  const parsedContent = useMemo(() => parseArtifactContent(content), [content]);

  // Auto-save artifacts when they're first detected
  useEffect(() => {
    if (parsedContent.artifacts.length > 0 && activePursuitId) {
      parsedContent.artifacts.forEach(async (artifact) => {
        try {
          // Create artifact in IML storage
          await artifactsApi.create({
            pursuit_id: activePursuitId,
            type: artifact.type,
            title: artifact.title,
            content: artifact.content,
            data: artifact.data,
            metadata: {
              source: 'coaching',
              autoExtracted: true,
              messageTimestamp: timestamp,
            },
          });
        } catch (error) {
          // Silently fail - artifact may already exist or be duplicate
          console.debug('Artifact auto-save skipped:', error.message);
        }
      });
    }
  }, [parsedContent.artifacts, activePursuitId, timestamp]);

  const handleArtifactClick = (artifact) => {
    setSelectedArtifact(artifact);
  };

  const handleClosePopup = () => {
    setSelectedArtifact(null);
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className={cn('flex gap-3 items-start', className)}
      >
        {/* Coach avatar */}
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center flex-shrink-0 shadow-glow-inde">
          <span className="text-white text-xs font-bold font-display">ID</span>
        </div>

        {/* Message bubble */}
        <div className="max-w-[90%] sm:max-w-[75%] min-w-0">
          {/* Mode badge if in special mode */}
          {modeBadge && (
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className="text-sm">{modeBadge.icon}</span>
              <span className="text-caption text-zinc-500">{modeBadge.label}</span>
            </div>
          )}

          <div className="bg-surface-2 border-l-2 border-inde-500 rounded-tr-panel rounded-b-panel px-4 py-3">
            {/* Render segments - text or artifact cards */}
            <div className="space-y-3">
              {parsedContent.segments.map((segment, index) => (
                segment.type === 'text' ? (
                  <div
                    key={index}
                    className="prose prose-invert prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:text-zinc-200 prose-a:text-inde-400 prose-a:no-underline hover:prose-a:underline prose-code:text-inde-300 prose-code:bg-surface-4 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-surface-0 prose-pre:border prose-pre:border-surface-border"
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {segment.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <ArtifactCard
                    key={segment.artifact.id}
                    artifact={segment.artifact}
                    onClick={() => handleArtifactClick(segment.artifact)}
                  />
                )
              ))}
            </div>
          </div>

          {/* Timestamp */}
          {timestamp && (
            <div className="mt-1.5 text-caption text-zinc-600">
              {formatDistanceToNow(new Date(timestamp), { addSuffix: true })}
            </div>
          )}
        </div>
      </motion.div>

      {/* Artifact popup */}
      <ArtifactPopup
        artifact={selectedArtifact}
        isOpen={!!selectedArtifact}
        onClose={handleClosePopup}
      />
    </>
  );
}

export default CoachMessage;
