/**
 * ConversationSearch Component
 * Full-text search across coaching session history.
 *
 * v3.13: Innovator Experience Polish
 */

import { useState, useEffect, useCallback } from 'react';
import { Search, X, Loader2, MessageSquare, ChevronRight } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../lib/utils';

// Debounce hook
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

export default function ConversationSearch({
  pursuitId,
  isOpen,
  onClose,
  onJumpToSession,
}) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [totalMatches, setTotalMatches] = useState(0);
  const token = useAuthStore((state) => state.token);

  const debouncedQuery = useDebounce(query, 300);

  const searchConversations = useCallback(async (searchQuery) => {
    if (!searchQuery || searchQuery.length < 2) {
      setResults([]);
      setTotalMatches(0);
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(
        `/api/coaching/${pursuitId}/search?q=${encodeURIComponent(searchQuery)}&limit=20`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setResults(data.results || []);
      setTotalMatches(data.total_matches || 0);
    } catch (err) {
      setError('Search failed. Please try again.');
      console.error('Conversation search failed:', err);
    } finally {
      setLoading(false);
    }
  }, [pursuitId, token]);

  // Search when debounced query changes
  useEffect(() => {
    searchConversations(debouncedQuery);
  }, [debouncedQuery, searchConversations]);

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setTotalMatches(0);
    onClose?.();
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  // Highlight matching text
  const highlightMatch = (content, searchQuery) => {
    if (!searchQuery || !content) return content;

    try {
      const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      const parts = content.split(regex);

      return parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-inde-500/30 text-inde-200 px-0.5 rounded">
            {part}
          </mark>
        ) : (
          part
        )
      );
    } catch {
      return content;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="border-b border-surface-border bg-surface-2/80 p-4">
      {/* Search input */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
          <Input
            type="text"
            placeholder="Search conversations..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9 pr-9 bg-surface-3 border-surface-border"
            autoFocus
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={handleClear}>
          Close
        </Button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
          <span className="ml-2 text-sm text-zinc-500">Searching...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="text-sm text-red-400 py-2">{error}</div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="mt-4 space-y-3 max-h-80 overflow-y-auto">
          <div className="text-caption text-zinc-500 mb-2">
            Found {totalMatches} match{totalMatches !== 1 ? 'es' : ''}
          </div>

          {results.map((result, idx) => (
            <div
              key={idx}
              className={cn(
                'p-3 rounded-lg bg-surface-3 border border-surface-border/50',
                'hover:border-inde-500/30 cursor-pointer transition-colors'
              )}
              onClick={() => onJumpToSession?.(result.timestamp)}
            >
              {/* Date and phase */}
              <div className="flex items-center gap-2 mb-2">
                <span className="text-caption text-zinc-500">
                  {formatDate(result.timestamp)}
                </span>
                {result.pursuit_phase && (
                  <>
                    <span className="text-zinc-700">|</span>
                    <span className="text-caption text-inde-400">
                      {result.pursuit_phase}
                    </span>
                  </>
                )}
              </div>

              {/* Context before */}
              {result.context_before?.map((turn, i) => (
                <div key={`before-${i}`} className="text-caption text-zinc-600 mb-1 pl-2 border-l-2 border-surface-border">
                  <span className="text-zinc-500">{turn.role === 'user' ? 'You' : 'Coach'}:</span>{' '}
                  {turn.content?.slice(0, 100)}...
                </div>
              ))}

              {/* Match */}
              <div className="flex items-start gap-2 py-2">
                <MessageSquare className="h-4 w-4 text-inde-400 mt-0.5 shrink-0" />
                <div>
                  <span className="text-caption text-inde-400 font-medium">
                    {result.match_turn.role === 'user' ? 'You' : 'InDE Coach'}:
                  </span>
                  <p className="text-body-sm text-zinc-300 mt-0.5">
                    {highlightMatch(result.match_turn.content?.slice(0, 200), query)}
                    {result.match_turn.content?.length > 200 && '...'}
                  </p>
                </div>
              </div>

              {/* Context after */}
              {result.context_after?.map((turn, i) => (
                <div key={`after-${i}`} className="text-caption text-zinc-600 mt-1 pl-2 border-l-2 border-surface-border">
                  <span className="text-zinc-500">{turn.role === 'user' ? 'You' : 'Coach'}:</span>{' '}
                  {turn.content?.slice(0, 100)}...
                </div>
              ))}

              {/* Jump indicator */}
              <div className="flex items-center justify-end mt-2 text-caption text-zinc-500">
                <span>Jump to conversation</span>
                <ChevronRight className="h-3 w-3 ml-1" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && query.length >= 2 && results.length === 0 && (
        <div className="text-center py-4 text-zinc-500">
          <p className="text-sm">No results for "{query}"</p>
          <p className="text-caption mt-1">Try different keywords</p>
        </div>
      )}

      {/* Minimum query hint */}
      {!loading && query.length > 0 && query.length < 2 && (
        <div className="text-caption text-zinc-500 py-2">
          Type at least 2 characters to search
        </div>
      )}
    </div>
  );
}
