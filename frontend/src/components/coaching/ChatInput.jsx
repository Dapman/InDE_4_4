import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Paperclip, X, FileText, Loader2 } from 'lucide-react';
import { useParams } from 'react-router-dom';
import { artifactsApi } from '../../api/artifacts';
import { useCoachingStore } from '../../stores/coachingStore';
import { cn } from '../../lib/utils';

// Allowed file types for upload
const ALLOWED_TYPES = '.csv,.json,.xlsx,.xls,.txt,.md,.pdf';
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

// v4.0: Placeholders use innovator-facing goal vocabulary
// Placeholders for new pursuits (no conversation history)
const NEW_PURSUIT_PLACEHOLDERS = {
  coaching: 'Describe your innovation idea...',
  vision: 'What\'s the story behind your idea?',
  fear: 'What could get in the way of this idea?',
  retrospective: 'What did you learn from this journey?',
  ems_review: 'Share your thoughts on this approach...',
  non_directive: 'What would you like to explore?',
};

// Placeholders for ongoing pursuits (has conversation history)
const ONGOING_PLACEHOLDERS = {
  coaching: 'Share your thoughts...',
  vision: 'Tell me more about your idea...',
  fear: 'What else could get in the way?',
  retrospective: 'What else did you learn?',
  ems_review: 'Share additional thoughts...',
  non_directive: 'What else would you like to explore?',
};

export function ChatInput({ onSend, disabled = false, mode = 'coaching', hasMessages = false, className }) {
  const { id: pursuitId } = useParams();
  const { getDraftMessage, setDraftMessage, clearDraftMessage } = useCoachingStore();

  // Initialize text from persisted draft
  const [text, setText] = useState(() => pursuitId ? getDraftMessage(pursuitId) : '');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Load draft when pursuit changes
  useEffect(() => {
    if (pursuitId) {
      const draft = getDraftMessage(pursuitId);
      setText(draft);
    }
  }, [pursuitId, getDraftMessage]);

  // Save draft as user types (debounced)
  const saveDraft = useCallback((value) => {
    if (pursuitId) {
      setDraftMessage(pursuitId, value);
    }
  }, [pursuitId, setDraftMessage]);

  // Debounce draft saving to avoid excessive writes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      saveDraft(text);
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [text, saveDraft]);

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text);
    setText('');
    // Clear the persisted draft on send
    if (pursuitId) {
      clearDraftMessage(pursuitId);
    }
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    // Re-focus after send
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError(null);

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      setUploadError('File too large. Maximum size: 10MB');
      return;
    }

    setSelectedFile(file);
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !pursuitId) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      await artifactsApi.upload(pursuitId, selectedFile);
      setSelectedFile(null);
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      // Optionally send a message about the upload
      onSend(`I've uploaded a file: ${selectedFile.name}`);
    } catch (error) {
      setUploadError(error.response?.data?.detail || 'Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Enter to send, Shift+Enter for new line
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    // Shift+Enter allows default behavior (new line)
  };

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 180) + 'px'; // max ~6 lines
    }
  }, [text]);

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Select placeholder based on whether this is a new or ongoing pursuit
  const placeholders = hasMessages ? ONGOING_PLACEHOLDERS : NEW_PURSUIT_PLACEHOLDERS;
  const placeholder = placeholders[mode] || placeholders.coaching;

  return (
    <div className={cn('border-t border-surface-border p-3 sm:p-4 bg-surface-1', className)}>
      {/* Selected file preview */}
      {selectedFile && (
        <div className="max-w-3xl mx-auto mb-3">
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-3 rounded-card border border-surface-border">
            <FileText className="w-4 h-4 text-inde-400 flex-shrink-0" />
            <span className="text-body-sm text-zinc-300 truncate flex-1">
              {selectedFile.name}
            </span>
            <span className="text-caption text-zinc-500">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </span>
            {isUploading ? (
              <Loader2 className="w-4 h-4 text-inde-400 animate-spin" />
            ) : (
              <>
                <button
                  onClick={handleFileUpload}
                  className="px-2 py-1 text-caption text-inde-400 hover:text-inde-300 font-medium"
                >
                  Upload
                </button>
                <button
                  onClick={clearSelectedFile}
                  className="p-1 text-zinc-500 hover:text-zinc-300"
                >
                  <X className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
          {uploadError && (
            <div className="mt-1 text-caption text-red-400 px-1">
              {uploadError}
            </div>
          )}
        </div>
      )}

      <div className="flex items-end gap-2 sm:gap-3 max-w-3xl mx-auto">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_TYPES}
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* File upload button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isUploading}
          className="p-2.5 rounded-card text-zinc-500 hover:text-zinc-300 hover:bg-surface-4
                     disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          title="Upload file (CSV, JSON, Excel, TXT, MD, PDF)"
        >
          <Paperclip className="w-5 h-5" />
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-surface-2 border border-surface-border rounded-card px-4 py-3
                     text-body-md text-zinc-200 placeholder:text-zinc-600
                     focus:outline-none focus:ring-2 focus:ring-inde-500/50 focus:border-inde-500
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className={cn(
            'p-2.5 rounded-card transition-all flex-shrink-0',
            disabled
              ? 'bg-surface-4 cursor-not-allowed'
              : text.trim()
                ? 'bg-inde-500 hover:bg-inde-600 shadow-glow-inde'
                : 'bg-surface-4 cursor-not-allowed'
          )}
        >
          {disabled ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Send
              className={cn(
                'w-5 h-5',
                text.trim() ? 'text-white' : 'text-zinc-600'
              )}
            />
          )}
        </button>
      </div>

      {/* Keyboard shortcut hint */}
      <div className="text-center mt-2">
        <span className="text-caption text-zinc-600">
          <kbd className="px-1.5 py-0.5 bg-surface-3 rounded text-xs font-mono">
            Enter
          </kbd>
          <span className="ml-1.5 mr-3">to send</span>
          <kbd className="px-1.5 py-0.5 bg-surface-3 rounded text-xs font-mono">
            Shift
          </kbd>
          <span className="mx-1">+</span>
          <kbd className="px-1.5 py-0.5 bg-surface-3 rounded text-xs font-mono">
            Enter
          </kbd>
          <span className="ml-1.5">for new line</span>
        </span>
      </div>
    </div>
  );
}

export default ChatInput;
