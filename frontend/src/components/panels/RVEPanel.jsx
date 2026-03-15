import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FlaskConical,
  Plus,
  ChevronRight,
  Lightbulb,
  Target,
  Scale,
  Printer,
} from 'lucide-react';
import { rveApi } from '../../api/rve';
import { pursuitsApi } from '../../api/pursuits';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';
import { printRVE } from '../../lib/print';

// Risk severity colors
const SEVERITY_CONFIG = {
  high: { color: 'text-health-atrisk', bg: 'bg-health-atrisk/10', border: 'border-health-atrisk/30' },
  medium: { color: 'text-health-caution', bg: 'bg-health-caution/10', border: 'border-health-caution/30' },
  low: { color: 'text-zinc-400', bg: 'bg-zinc-500/10', border: 'border-zinc-500/30' },
};

// Risk status icons
const STATUS_ICONS = {
  identified: AlertTriangle,
  validating: FlaskConical,
  validated: CheckCircle2,
  mitigated: Shield,
  accepted: Target,
  rejected: XCircle,
};

// Risk card component
function RiskCard({ risk, onSelect, isSelected }) {
  const severity = risk.severity?.toLowerCase() || 'medium';
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
  const StatusIcon = STATUS_ICONS[risk.status] || AlertTriangle;

  return (
    <button
      onClick={() => onSelect(risk)}
      className={cn(
        'w-full text-left p-3 rounded-card border transition-all',
        config.bg,
        config.border,
        isSelected ? 'ring-2 ring-inde-500' : 'hover:border-zinc-600'
      )}
    >
      <div className="flex items-start gap-2">
        <StatusIcon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', config.color)} />
        <div className="flex-1 min-w-0">
          <div className="text-caption font-medium text-zinc-300 line-clamp-1">
            {risk.title || risk.type?.replace(/_/g, ' ')}
          </div>
          {risk.description && (
            <p className="text-caption text-zinc-500 mt-0.5 line-clamp-2">
              {risk.description}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1.5">
            <span className={cn('text-caption capitalize', config.color)}>
              {severity}
            </span>
            <span className="text-caption text-zinc-600">|</span>
            <span className="text-caption text-zinc-500 capitalize">
              {risk.status || 'identified'}
            </span>
          </div>
        </div>
        <ChevronRight className="h-4 w-4 text-zinc-600 flex-shrink-0" />
      </div>
    </button>
  );
}

// Experiment card component
function ExperimentCard({ experiment }) {
  const statusColors = {
    planned: 'text-zinc-400 bg-zinc-500/10',
    running: 'text-inde-400 bg-inde-500/10',
    completed: 'text-health-healthy bg-health-healthy/10',
    failed: 'text-health-atrisk bg-health-atrisk/10',
  };
  const statusClass = statusColors[experiment.status] || statusColors.planned;

  return (
    <div className="p-2 rounded-card bg-surface-3 border border-surface-border">
      <div className="flex items-center gap-2 mb-1">
        <FlaskConical className="h-3.5 w-3.5 text-inde-400" />
        <span className="text-caption font-medium text-zinc-300 flex-1 truncate">
          {experiment.title || 'Experiment'}
        </span>
        <span className={cn('text-caption px-1.5 py-0.5 rounded', statusClass)}>
          {experiment.status}
        </span>
      </div>
      {experiment.hypothesis && (
        <p className="text-caption text-zinc-500 line-clamp-2 ml-5">
          {experiment.hypothesis}
        </p>
      )}
    </div>
  );
}

// Risk detail view
function RiskDetailView({ risk, pursuitId, onBack }) {
  const queryClient = useQueryClient();

  // Fetch experiments for this risk
  const { data: experimentsData } = useQuery({
    queryKey: ['experiments', risk.id],
    queryFn: async () => {
      const response = await rveApi.getExperiments(risk.id);
      return response.data;
    },
    enabled: !!risk.id,
  });

  // Fetch decision support
  const { data: decisionData } = useQuery({
    queryKey: ['decision-support', risk.id],
    queryFn: async () => {
      const response = await rveApi.getDecisionSupport(risk.id);
      return response.data;
    },
    enabled: !!risk.id,
  });

  const experiments = experimentsData?.experiments || [];
  const decision = decisionData;

  const config = SEVERITY_CONFIG[risk.severity?.toLowerCase()] || SEVERITY_CONFIG.medium;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-surface-border">
        <button
          onClick={onBack}
          className="text-caption text-inde-400 hover:text-inde-300 mb-2 flex items-center gap-1"
        >
          <ChevronRight className="h-3 w-3 rotate-180" />
          Back to risks
        </button>
        <h3 className="text-body-sm font-medium text-zinc-200">
          {risk.title || risk.type?.replace(/_/g, ' ')}
        </h3>
        <div className="flex items-center gap-2 mt-1">
          <span className={cn('text-caption capitalize', config.color)}>
            {risk.severity || 'medium'} severity
          </span>
          <span className="text-caption text-zinc-600">|</span>
          <span className="text-caption text-zinc-500 capitalize">
            {risk.status || 'identified'}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Description */}
        {risk.description && (
          <div className="p-3 border-b border-surface-border">
            <div className="text-caption text-zinc-500 mb-1">Description</div>
            <p className="text-caption text-zinc-300">{risk.description}</p>
          </div>
        )}

        {/* Decision Support */}
        {decision?.recommendation && (
          <div className="p-3 border-b border-surface-border">
            <div className="flex items-center gap-2 mb-2">
              <Scale className="h-4 w-4 text-inde-400" />
              <span className="text-caption text-zinc-500">Decision Support</span>
            </div>
            <div className="p-2 rounded-card bg-inde-500/10 border border-inde-500/20">
              <p className="text-caption text-zinc-300">{decision.recommendation}</p>
              {decision.confidence > 0 && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-caption text-zinc-500">Confidence:</span>
                  <div className="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-inde-500"
                      style={{ width: `${decision.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-caption text-zinc-400">
                    {Math.round(decision.confidence * 100)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Experiments */}
        <div className="p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-inde-400" />
              <span className="text-caption text-zinc-500">Validation Experiments</span>
            </div>
            <span className="text-caption text-zinc-600">({experiments.length})</span>
          </div>

          {experiments.length === 0 ? (
            <div className="text-center py-4">
              <Lightbulb className="h-6 w-6 text-zinc-600 mx-auto mb-2" />
              <p className="text-caption text-zinc-500">No experiments yet</p>
              <p className="text-caption text-zinc-600 mt-1">
                Design experiments to validate this risk
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {experiments.map((exp, i) => (
                <ExperimentCard key={exp.id || i} experiment={exp} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * RVEPanel - Risk Validation Engine panel for the right sidebar.
 * Shows risks, validation status, experiments, and decision support.
 */
export function RVEPanel({ pursuitId, onSendMessage, onDataChange }) {
  const [selectedRisk, setSelectedRisk] = useState(null);

  // Fetch risks for the pursuit
  const { data: risksData, isLoading } = useQuery({
    queryKey: ['risks', pursuitId],
    queryFn: async () => {
      // Try RVE endpoint first, fallback to pursuit health risks
      try {
        const response = await rveApi.getRisks(pursuitId);
        if (response.data?.risks?.length > 0) {
          return response.data;
        }
      } catch {
        // Fall through to pursuit health
      }
      // Fallback: get risks from pursuit health data
      const healthResponse = await pursuitsApi.getHealth(pursuitId);
      return { risks: healthResponse.data?.risks || healthResponse.data?.active_risks || [] };
    },
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 30000,
  });

  const risks = risksData?.risks || [];

  // Group risks by severity
  const groupedRisks = useMemo(() => {
    const groups = { high: [], medium: [], low: [] };
    risks.forEach((risk) => {
      const severity = risk.severity?.toLowerCase() || 'medium';
      if (groups[severity]) {
        groups[severity].push(risk);
      } else {
        groups.medium.push(risk);
      }
    });
    return groups;
  }, [risks]);

  const handleDiscussRisk = (risk) => {
    if (onSendMessage) {
      const riskTitle = risk.title || risk.type?.replace(/_/g, ' ') || 'this risk';
      onSendMessage(`Let's discuss ${riskTitle} and explore validation approaches.`);
    }
  };

  // Handle print
  const handlePrint = () => {
    printRVE({ risks });
  };

  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-inde-500/30 border-t-inde-500 rounded-full animate-spin" />
      </div>
    );
  }

  // Show detail view if a risk is selected
  if (selectedRisk) {
    return (
      <RiskDetailView
        risk={selectedRisk}
        pursuitId={pursuitId}
        onBack={() => setSelectedRisk(null)}
      />
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-surface-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-inde-400" />
            <h3 className="text-body-sm font-medium text-zinc-300">Risk Validation</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-caption text-zinc-500">({risks.length})</span>
            <button
              onClick={handlePrint}
              className="p-1.5 hover:bg-surface-3 rounded transition-colors"
              title="Print risk report"
            >
              <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
            </button>
          </div>
        </div>
      </div>

      {/* Risk list */}
      <div className="flex-1 overflow-y-auto">
        {risks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <Shield className="h-8 w-8 text-health-healthy mb-3" />
            <p className="text-body-sm text-zinc-400 mb-1">No risks identified</p>
            <p className="text-caption text-zinc-600">
              Risks will appear here as they're detected during coaching
            </p>
          </div>
        ) : (
          <div className="p-3 space-y-4">
            {/* High severity */}
            {groupedRisks.high.length > 0 && (
              <div>
                <div className="text-caption text-health-atrisk mb-2 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  High Priority ({groupedRisks.high.length})
                </div>
                <div className="space-y-2">
                  {groupedRisks.high.map((risk, i) => (
                    <RiskCard
                      key={risk.id || i}
                      risk={risk}
                      onSelect={setSelectedRisk}
                      isSelected={false}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Medium severity */}
            {groupedRisks.medium.length > 0 && (
              <div>
                <div className="text-caption text-health-caution mb-2 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Medium Priority ({groupedRisks.medium.length})
                </div>
                <div className="space-y-2">
                  {groupedRisks.medium.map((risk, i) => (
                    <RiskCard
                      key={risk.id || i}
                      risk={risk}
                      onSelect={setSelectedRisk}
                      isSelected={false}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Low severity */}
            {groupedRisks.low.length > 0 && (
              <div>
                <div className="text-caption text-zinc-400 mb-2 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Low Priority ({groupedRisks.low.length})
                </div>
                <div className="space-y-2">
                  {groupedRisks.low.map((risk, i) => (
                    <RiskCard
                      key={risk.id || i}
                      risk={risk}
                      onSelect={setSelectedRisk}
                      isSelected={false}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default RVEPanel;
