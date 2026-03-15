import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  Lightbulb,
  BarChart3,
  Wrench,
  Shield,
  FlaskConical,
  Target,
  MessageSquare,
  User,
  Clock,
  Printer,
} from 'lucide-react';
import { pursuitsApi } from '../../api/pursuits';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';
import { cn } from '../../lib/utils';
import { formatDistanceToNow } from '../../lib/dateUtils';
import { printScaffolding } from '../../lib/print';

// Category definitions with icons and element groupings
// v4.0: Labels use innovator-facing goal vocabulary
// Maps to backend CRITICAL_ELEMENTS and V25_IMPORTANT_ELEMENTS
const ELEMENT_CATEGORIES = {
  vision: {
    label: 'Your Story',
    icon: Lightbulb,
    // Maps to backend vision_elements
    elements: [
      'problem_statement',
      'target_user',
      'current_situation',
      'pain_points',
      'solution_concept',
      'value_proposition',
      'differentiation',
      'success_criteria',
    ],
    backendField: 'vision_elements',
  },
  fears: {
    label: 'Risks & Protections',
    icon: Shield,
    // Maps to backend fear_elements
    elements: [
      'capability_fears',
      'market_fears',
      'resource_fears',
      'timing_fears',
      'competition_fears',
      'personal_fears',
    ],
    backendField: 'fear_elements',
  },
  validation: {
    label: 'What You\'ve Tested',
    icon: FlaskConical,
    // Maps to backend hypothesis_elements
    elements: [
      'assumption_statement',
      'testable_prediction',
      'test_method',
      'success_metric',
      'failure_criteria',
      'learning_plan',
    ],
    backendField: 'hypothesis_elements',
  },
  market: {
    label: 'Market',
    icon: BarChart3,
    // Maps to backend important_elements
    elements: [
      'competitive_landscape',
      'business_model',
      'revenue_model',
      'go_to_market',
      'market_timing',
      'adoption_barriers',
    ],
    backendField: 'important_elements',
  },
  technical: {
    label: 'Technical',
    icon: Wrench,
    // Maps to backend important_elements
    elements: [
      'technical_feasibility',
      'resource_requirements',
      'team_capabilities',
      'scalability_constraints',
      'cost_structure',
    ],
    backendField: 'important_elements',
  },
  strategy: {
    label: 'Strategy',
    icon: Target,
    // Maps to backend important_elements
    elements: [
      'risk_tolerance',
      'regulatory_concerns',
      'partnerships',
      'stakeholder_alignment',
      'exit_strategy',
    ],
    backendField: 'important_elements',
  },
};

// Progress bar color based on completeness
function getProgressColor(percentage) {
  if (percentage >= 70) return 'bg-health-healthy';
  if (percentage >= 40) return 'bg-health-caution';
  return 'bg-health-atrisk';
}

// Confidence badge component
function ConfidenceBadge({ confidence }) {
  const confidenceLabels = {
    strong: { label: 'Strong', color: 'text-health-healthy' },
    moderate: { label: 'Moderate', color: 'text-health-caution' },
    weak: { label: 'Weak', color: 'text-health-atrisk' },
  };

  // Handle both numeric (0.0-1.0) and string ("strong"/"moderate"/"weak") confidence
  let confKey = 'moderate';
  if (typeof confidence === 'number') {
    if (confidence >= 0.7) confKey = 'strong';
    else if (confidence >= 0.4) confKey = 'moderate';
    else confKey = 'weak';
  } else if (typeof confidence === 'string') {
    confKey = confidence.toLowerCase();
  }

  const conf = confidenceLabels[confKey] || confidenceLabels.moderate;

  return (
    <span className={cn('text-caption', conf.color)}>
      {conf.label}
    </span>
  );
}

// Single element item component
function ElementItem({ element, onAskCoach }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const displayLabel = useDisplayLabel('scaffolding_elements', element.name);
  const isFilled = element.value && element.value.trim() !== '';

  return (
    <div className="border-b border-surface-border/50 last:border-0">
      <button
        onClick={() => isFilled && setIsExpanded(!isExpanded)}
        className={cn(
          'w-full flex items-start gap-2 px-3 py-2 text-left transition-colors',
          isFilled
            ? 'hover:bg-surface-3 cursor-pointer'
            : 'cursor-default'
        )}
      >
        {isFilled ? (
          <CheckCircle2 className="h-4 w-4 text-health-healthy mt-0.5 flex-shrink-0" />
        ) : (
          <Circle className="h-4 w-4 text-zinc-600 mt-0.5 flex-shrink-0" />
        )}
        <span
          className={cn(
            'text-caption flex-1',
            isFilled ? 'text-zinc-300' : 'text-zinc-500'
          )}
        >
          {displayLabel.label}
        </span>
        {isFilled && (
          <ChevronDown
            className={cn(
              'h-3.5 w-3.5 text-zinc-500 transition-transform flex-shrink-0',
              isExpanded && 'rotate-180'
            )}
          />
        )}
      </button>

      {/* Expanded element detail */}
      {isExpanded && isFilled && (
        <div className="px-3 pb-3 ml-6 space-y-2">
          {/* Value preview */}
          <p className="text-caption text-zinc-400 line-clamp-3">
            "{element.value}"
          </p>

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-3 text-caption text-zinc-500">
            {element.confidence && (
              <div className="flex items-center gap-1">
                <Target className="h-3 w-3" />
                <ConfidenceBadge confidence={element.confidence} />
              </div>
            )}
            {element.captured_at && (
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{formatDistanceToNow(element.captured_at)}</span>
              </div>
            )}
            {element.captured_by && (
              <div className="flex items-center gap-1">
                <User className="h-3 w-3" />
                <span>{element.captured_by}</span>
              </div>
            )}
          </div>

          {element.extraction_method && (
            <div className="text-caption text-zinc-600">
              Method: {element.extraction_method}
            </div>
          )}
        </div>
      )}

      {/* Ask coach action for empty elements */}
      {!isFilled && onAskCoach && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAskCoach(element.name, displayLabel.label);
          }}
          className="ml-6 px-2 py-1 mb-2 text-caption text-inde-400 hover:text-inde-300
                     hover:bg-inde-500/10 rounded transition-colors flex items-center gap-1"
        >
          <MessageSquare className="h-3 w-3" />
          Ask coach
        </button>
      )}
    </div>
  );
}

// Category section component
function CategorySection({
  categoryId,
  category,
  elements,
  onAskCoach,
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const Icon = category.icon;

  const filledCount = elements.filter((el) => el.value && el.value.trim() !== '').length;
  const totalCount = elements.length;
  const percentage = totalCount > 0 ? Math.round((filledCount / totalCount) * 100) : 0;

  return (
    <div className="border-b border-surface-border last:border-0">
      {/* Category header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-surface-3 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-zinc-500" />
        ) : (
          <ChevronRight className="h-4 w-4 text-zinc-500" />
        )}
        <Icon className="h-4 w-4 text-inde-400" />
        <span className="text-body-sm font-medium text-zinc-300 flex-1 text-left">
          {category.label}
        </span>
        <span className="text-caption text-zinc-500">
          {filledCount}/{totalCount}
        </span>
        {/* Mini progress ring */}
        <div
          className="w-4 h-4 rounded-full border-2"
          style={{
            borderColor: percentage >= 70 ? '#22c55e' : percentage >= 40 ? '#f59e0b' : '#ef4444',
            background: `conic-gradient(${percentage >= 70 ? '#22c55e' : percentage >= 40 ? '#f59e0b' : '#ef4444'} ${percentage}%, transparent 0)`,
          }}
        />
      </button>

      {/* Category elements */}
      {isExpanded && (
        <div className="bg-surface-1/50">
          {elements.map((element) => (
            <ElementItem
              key={element.name}
              element={element}
              onAskCoach={onAskCoach}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * ScaffoldingPanel - Shows innovation element completion status.
 * Groups elements by category with progress visualization.
 */
export function ScaffoldingPanel({ pursuitId, onSendMessage, onDataChange }) {
  // Fetch scaffolding data
  const { data, isLoading, error } = useQuery({
    queryKey: ['scaffold', pursuitId],
    queryFn: async () => {
      const response = await pursuitsApi.getScaffold(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 30000, // 30 seconds
    refetchInterval: 30000,
  });

  // Organize elements by category - maps backend structure to frontend categories
  const categorizedElements = useMemo(() => {
    if (!data) return {};

    const result = {};

    // Backend returns: vision_elements, fear_elements, hypothesis_elements, important_elements
    // Each is an object where keys are element names and values are { text, confidence, ... } or null

    // Group by category using the backendField mapping
    Object.entries(ELEMENT_CATEGORIES).forEach(([catId, cat]) => {
      const backendData = data[cat.backendField] || {};

      result[catId] = cat.elements.map((elName) => {
        const elementData = backendData[elName];
        // Backend stores elements as { text: "...", confidence: 0.8, ... } or null
        const hasValue = elementData && (elementData.text || elementData.value);

        return {
          name: elName,
          value: elementData?.text || elementData?.value || '',
          confidence: elementData?.confidence,
          captured_at: elementData?.captured_at || elementData?.timestamp,
          captured_by: elementData?.captured_by || elementData?.author,
          extraction_method: elementData?.extraction_method || elementData?.method,
        };
      });
    });

    return result;
  }, [data]);

  // Calculate overall completeness
  const { filledCount, totalCount, percentage } = useMemo(() => {
    let filled = 0;
    let total = 0;

    Object.values(categorizedElements).forEach((elements) => {
      elements.forEach((el) => {
        total++;
        if (el.value && el.value.trim() !== '') {
          filled++;
        }
      });
    });

    return {
      filledCount: filled,
      totalCount: total,
      percentage: total > 0 ? Math.round((filled / total) * 100) : 0,
    };
  }, [categorizedElements]);

  // Handle "Ask coach" action
  const handleAskCoach = (elementName, elementLabel) => {
    if (onSendMessage) {
      onSendMessage(`Can you help me think about my ${elementLabel.toLowerCase()}?`);
    }
  };

  // Handle print
  const handlePrint = () => {
    printScaffolding(data);
  };

  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-inde-500/30 border-t-inde-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-caption text-health-atrisk mb-2">Failed to load scaffolding data</p>
        <p className="text-caption text-zinc-600">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Overall completeness header */}
      <div className="p-4 border-b border-surface-border">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-body-sm font-medium text-zinc-300">
            Innovation Completeness
          </h3>
          <button
            onClick={handlePrint}
            className="p-1.5 hover:bg-surface-3 rounded transition-colors"
            title="Print scaffolding report"
          >
            <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-surface-3 rounded-full overflow-hidden mb-2">
          <div
            className={cn('h-full transition-all duration-500', getProgressColor(percentage))}
            style={{ width: `${percentage}%` }}
          />
        </div>

        {/* Stats */}
        <div className="flex items-center justify-between">
          <span className="text-display-sm font-bold text-zinc-200">
            {percentage}%
          </span>
          <span className="text-caption text-zinc-500">
            {filledCount} of {totalCount} elements captured
          </span>
        </div>
      </div>

      {/* Category sections */}
      <div className="flex-1 overflow-y-auto">
        {Object.entries(ELEMENT_CATEGORIES).map(([catId, category]) => (
          <CategorySection
            key={catId}
            categoryId={catId}
            category={category}
            elements={categorizedElements[catId] || []}
            onAskCoach={handleAskCoach}
          />
        ))}
      </div>
    </div>
  );
}

export default ScaffoldingPanel;
