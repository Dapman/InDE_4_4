import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Sparkles, MessageCircle, Lightbulb } from 'lucide-react';
import { pursuitsApi } from '../api/pursuits';
import { Button } from '../components/ui/button';
import { cn } from '../lib/utils';

/**
 * NewPursuitPage - Simplified conversational approach
 *
 * v3.7.4: Removed methodology selection wizard. Instead:
 * - User describes their innovation idea/spark
 * - Pursuit is created immediately
 * - User enters coaching conversation
 * - InDE detects appropriate methodology through conversational scaffolding
 */
export default function NewPursuitPage() {
  const navigate = useNavigate();
  const [spark, setSpark] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Create pursuit mutation
  const createPursuit = useMutation({
    mutationFn: (data) => pursuitsApi.create(data),
    onSuccess: (response) => {
      const pursuitId = response.data.id || response.data.pursuit_id;
      // Navigate directly to the coaching conversation
      // Pass the spark text as initial message to auto-send
      navigate(`/pursuit/${pursuitId}`, {
        state: { initialMessage: spark },
      });
    },
    onError: (error) => {
      console.error('Failed to create pursuit:', error);
      setIsCreating(false);
    },
  });

  const handleStartConversation = () => {
    if (spark.trim().length < 10) return;

    setIsCreating(true);

    // Create pursuit with just the spark description
    // Methodology will be detected through conversation (freeform by default)
    createPursuit.mutate({
      title: generateTitle(spark),
      description: spark,
      // No archetype specified - InDE will detect through conversation
    });
  };

  const handleKeyDown = (e) => {
    // Enter to start (Shift+Enter for new line)
    if (e.key === 'Enter' && !e.shiftKey && spark.trim().length >= 10) {
      e.preventDefault();
      handleStartConversation();
    }
  };

  const canStart = spark.trim().length >= 10;

  return (
    <div className="h-full flex flex-col items-center justify-center px-8 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-2xl w-full text-center"
      >
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-violet-500/20
                          flex items-center justify-center border border-inde-500/30">
              <Lightbulb className="w-8 h-8 text-inde-400" />
            </div>
          </div>
          <h1 className="text-display-lg inde-gradient-text mb-4">
            What's on your mind?
          </h1>
          <p className="text-body-lg text-zinc-400 max-w-lg mx-auto">
            Share your innovation idea, problem you're trying to solve, or opportunity
            you've spotted. Let's explore it together through conversation.
          </p>
        </div>

        {/* Input area */}
        <div className="relative mb-6">
          <textarea
            value={spark}
            onChange={(e) => setSpark(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="I've been thinking about..."
            rows={5}
            className="w-full bg-surface-2 border border-surface-border rounded-panel px-6 py-4
                       text-body-lg text-zinc-200 placeholder:text-zinc-600
                       focus:outline-none focus:ring-2 focus:ring-inde-500/50 focus:border-inde-500
                       resize-none transition-all"
            autoFocus
            disabled={isCreating}
          />
          <div className="absolute bottom-3 right-3 text-caption text-zinc-600">
            {spark.length} characters
          </div>
        </div>

        {/* Hint text */}
        <p className="text-caption text-zinc-600 mb-6">
          {spark.length < 10
            ? `${10 - spark.length} more characters to start`
            : 'Ready to start the conversation'}
        </p>

        {/* Start button */}
        <Button
          onClick={handleStartConversation}
          disabled={!canStart || isCreating}
          size="lg"
          className={cn(
            'gap-3 px-8 py-6 text-body-lg transition-all',
            canStart && !isCreating
              ? 'bg-gradient-to-r from-blue-500 to-violet-500 hover:from-blue-600 hover:to-violet-600 shadow-glow-inde'
              : 'bg-surface-4 text-zinc-500'
          )}
        >
          {isCreating ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Starting...
            </>
          ) : (
            <>
              <MessageCircle className="w-5 h-5" />
              Let's Talk About It
            </>
          )}
        </Button>

        {/* Keyboard shortcut hint */}
        {canStart && !isCreating && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-caption text-zinc-600 mt-4"
          >
            <kbd className="px-1.5 py-0.5 bg-surface-3 rounded text-xs font-mono">
              Enter
            </kbd>
            <span className="ml-1.5">to start</span>
            <span className="mx-2 text-zinc-700">|</span>
            <kbd className="px-1.5 py-0.5 bg-surface-3 rounded text-xs font-mono">
              Shift+Enter
            </kbd>
            <span className="ml-1.5">for new line</span>
          </motion.p>
        )}

        {/* What happens next */}
        <div className="mt-12 pt-8 border-t border-surface-border">
          <h3 className="text-body-sm text-zinc-400 mb-4">What happens next?</h3>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <div className="flex items-center gap-3 text-caption text-zinc-500">
              <div className="w-8 h-8 rounded-full bg-surface-4 flex items-center justify-center">
                <span className="text-inde-400">1</span>
              </div>
              <span>Your coach greets you</span>
            </div>
            <div className="flex items-center gap-3 text-caption text-zinc-500">
              <div className="w-8 h-8 rounded-full bg-surface-4 flex items-center justify-center">
                <span className="text-inde-400">2</span>
              </div>
              <span>Explore your idea together</span>
            </div>
            <div className="flex items-center gap-3 text-caption text-zinc-500">
              <div className="w-8 h-8 rounded-full bg-surface-4 flex items-center justify-center">
                <span className="text-inde-400">3</span>
              </div>
              <span>Build clarity naturally</span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

/**
 * Generate a title from the spark description.
 * Extracts key phrases or uses first N words.
 */
function generateTitle(spark) {
  // Clean and truncate
  const cleaned = spark.trim().replace(/\s+/g, ' ');

  // If it starts with common phrases, skip them
  const skipPhrases = [
    "i've been thinking about",
    "i want to",
    "i'm thinking about",
    "what if",
    "i have an idea for",
    "i'd like to",
    "my idea is",
  ];

  let title = cleaned;
  for (const phrase of skipPhrases) {
    if (cleaned.toLowerCase().startsWith(phrase)) {
      title = cleaned.substring(phrase.length).trim();
      break;
    }
  }

  // Capitalize first letter
  title = title.charAt(0).toUpperCase() + title.slice(1);

  // Truncate to reasonable length
  if (title.length > 60) {
    // Find a good break point
    const breakPoint = title.lastIndexOf(' ', 60);
    title = title.substring(0, breakPoint > 30 ? breakPoint : 60) + '...';
  }

  return title || 'New Innovation Pursuit';
}
