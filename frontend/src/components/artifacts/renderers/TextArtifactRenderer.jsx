/**
 * TextArtifactRenderer - Renders text-based artifacts with markdown support
 *
 * Used for: vision, vision_statement, elevator_pitch, value_proposition,
 * hypothesis, fear_register, summary, document
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function TextArtifactRenderer({ artifact }) {
  // Get content - could be string or in data.content
  const content = typeof artifact.content === 'string'
    ? artifact.content
    : artifact.data?.content || JSON.stringify(artifact.data, null, 2);

  return (
    <div className="prose prose-invert prose-sm max-w-none
      prose-p:my-3 prose-ul:my-3 prose-ol:my-3 prose-li:my-1
      prose-headings:text-zinc-200 prose-headings:font-semibold
      prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
      prose-a:text-inde-400 prose-a:no-underline hover:prose-a:underline
      prose-code:text-inde-300 prose-code:bg-surface-4 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
      prose-code:before:content-none prose-code:after:content-none
      prose-pre:bg-surface-0 prose-pre:border prose-pre:border-surface-border prose-pre:rounded-lg
      prose-blockquote:border-l-inde-500 prose-blockquote:bg-surface-3/50 prose-blockquote:py-1 prose-blockquote:px-4
      prose-table:border-collapse prose-th:bg-surface-3 prose-th:p-2 prose-td:p-2 prose-td:border prose-td:border-surface-border
      prose-strong:text-zinc-200 prose-em:text-zinc-300"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default TextArtifactRenderer;
