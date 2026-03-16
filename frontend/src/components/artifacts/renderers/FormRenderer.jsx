/**
 * FormRenderer - Renders survey/form artifacts (view only)
 *
 * Displays form fields and their values in a read-only format.
 */

import { cn } from '../../../lib/utils';

export function FormRenderer({ artifact }) {
  const data = artifact.data || parseFormData(artifact.content);

  if (!data) {
    return (
      <div className="text-center text-zinc-500 py-8">
        Unable to parse form data
      </div>
    );
  }

  const { title, description, fields = [] } = data;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Title and description */}
      {title && (
        <h3 className="text-body-md font-medium text-zinc-200 mb-2">
          {title}
        </h3>
      )}
      {description && (
        <p className="text-caption text-zinc-500 mb-6">
          {description}
        </p>
      )}

      {/* Form fields */}
      <div className="space-y-6">
        {fields.map((field, index) => (
          <FormField key={field.id || index} field={field} />
        ))}
      </div>

      {fields.length === 0 && (
        <div className="text-center text-zinc-500 py-4">
          No form fields defined
        </div>
      )}
    </div>
  );
}

function FormField({ field }) {
  const { type = 'text', label, value, options = [], required } = field;

  return (
    <div className="space-y-2">
      {/* Label */}
      <label className="block text-body-sm text-zinc-300">
        {label}
        {required && <span className="text-rose-400 ml-1">*</span>}
      </label>

      {/* Field display based on type */}
      {type === 'text' && (
        <div className="px-3 py-2 bg-surface-3 border border-surface-border rounded-lg text-caption text-zinc-400">
          {value || <span className="text-zinc-600 italic">No response</span>}
        </div>
      )}

      {type === 'textarea' && (
        <div className="px-3 py-2 bg-surface-3 border border-surface-border rounded-lg text-caption text-zinc-400 min-h-[80px] whitespace-pre-wrap">
          {value || <span className="text-zinc-600 italic">No response</span>}
        </div>
      )}

      {type === 'number' && (
        <div className="px-3 py-2 bg-surface-3 border border-surface-border rounded-lg text-caption text-zinc-400 w-32">
          {value !== undefined ? value : <span className="text-zinc-600 italic">—</span>}
        </div>
      )}

      {type === 'select' && (
        <div className="px-3 py-2 bg-surface-3 border border-surface-border rounded-lg text-caption text-zinc-400">
          {value || <span className="text-zinc-600 italic">No selection</span>}
          {options.length > 0 && (
            <div className="mt-2 text-[10px] text-zinc-600">
              Options: {options.join(', ')}
            </div>
          )}
        </div>
      )}

      {type === 'rating' && (
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <div
              key={star}
              className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm',
                value && star <= value
                  ? 'bg-amber-500 text-white'
                  : 'bg-surface-3 border border-surface-border text-zinc-600'
              )}
            >
              {star}
            </div>
          ))}
          {!value && (
            <span className="text-caption text-zinc-600 ml-2 italic">
              No rating
            </span>
          )}
        </div>
      )}

      {type === 'checkbox' && (
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'w-5 h-5 rounded border flex items-center justify-center',
              value
                ? 'bg-inde-500 border-inde-500'
                : 'bg-surface-3 border-surface-border'
            )}
          >
            {value && (
              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
          <span className="text-caption text-zinc-400">
            {value ? 'Yes' : 'No'}
          </span>
        </div>
      )}

      {type === 'radio' && options.length > 0 && (
        <div className="space-y-2">
          {options.map((option, i) => (
            <div key={i} className="flex items-center gap-2">
              <div
                className={cn(
                  'w-4 h-4 rounded-full border flex items-center justify-center',
                  value === option
                    ? 'border-inde-500'
                    : 'border-surface-border'
                )}
              >
                {value === option && (
                  <div className="w-2 h-2 rounded-full bg-inde-500" />
                )}
              </div>
              <span className={cn(
                'text-caption',
                value === option ? 'text-zinc-300' : 'text-zinc-500'
              )}>
                {option}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Scale type (1-10 or similar) */}
      {type === 'scale' && (
        <div className="flex items-center gap-1">
          {Array.from({ length: options.max || 10 }, (_, i) => i + (options.min || 1)).map((num) => (
            <div
              key={num}
              className={cn(
                'w-8 h-8 rounded flex items-center justify-center text-sm',
                value === num
                  ? 'bg-inde-500 text-white'
                  : 'bg-surface-3 border border-surface-border text-zinc-500'
              )}
            >
              {num}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Helper to parse form data from string content
function parseFormData(content) {
  if (!content) return null;

  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export default FormRenderer;
