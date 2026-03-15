import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useCoachingStore } from '../../stores/coachingStore';
import { cn } from '../../lib/utils';

export function StreamingMessage({ className }) {
  const streamBuffer = useCoachingStore((s) => s.streamBuffer);
  const isStreaming = useCoachingStore((s) => s.isStreaming);

  // Don't render if not streaming and no buffer content
  if (!isStreaming && !streamBuffer) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15, ease: 'easeOut' }}
      className={cn('flex gap-3 items-start', className)}
    >
      {/* Coach avatar */}
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center flex-shrink-0 shadow-glow-inde">
        <span className="text-white text-xs font-bold font-display">ID</span>
      </div>

      {/* Message bubble */}
      <div className="max-w-[75%] min-w-0">
        <div className="bg-surface-2 border-l-2 border-inde-500 rounded-tr-panel rounded-b-panel px-4 py-3">
          {streamBuffer ? (
            <div className="prose prose-invert prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:text-zinc-200 prose-a:text-inde-400 prose-a:no-underline hover:prose-a:underline prose-code:text-inde-300 prose-code:bg-surface-4 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-surface-0 prose-pre:border prose-pre:border-surface-border">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {streamBuffer}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <span className="text-body-sm text-zinc-500">Thinking</span>
              <span className="flex gap-0.5">
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className="w-1 h-1 bg-inde-400 rounded-full"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      delay: i * 0.15,
                    }}
                  />
                ))}
              </span>
            </div>
          )}

          {/* Streaming cursor */}
          {isStreaming && streamBuffer && (
            <span className="inline-block w-0.5 h-4 bg-inde-400 animate-pulse-gentle ml-0.5 -mb-0.5" />
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default StreamingMessage;
