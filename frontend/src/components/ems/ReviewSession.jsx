import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emsApi } from '../../api/ems';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../lib/utils';
import {
  GripVertical,
  X,
  Plus,
  Check,
  Star,
  Lock,
  Users,
  Building2,
  Globe,
  ChevronRight,
  ChevronDown,
  Loader2,
  Send,
  ArrowLeft,
  Edit3,
  GitCompare,
  FileText,
  ArrowRight,
} from 'lucide-react';

// Confidence tier configuration
const CONFIDENCE_CONFIG = {
  HIGH: { label: 'High', color: 'text-emerald-400', bg: 'bg-emerald-500/10', stars: 3 },
  MODERATE: { label: 'Moderate', color: 'text-amber-400', bg: 'bg-amber-500/10', stars: 2 },
  LOW: { label: 'Low', color: 'text-rose-400', bg: 'bg-rose-500/10', stars: 1 },
};

// Visibility configuration
const VISIBILITY_CONFIG = {
  personal: { label: 'Personal', icon: Lock, description: 'Only you can see and use this methodology' },
  team: { label: 'Team', icon: Users, description: 'Shared with your pursuit team members' },
  organization: { label: 'Organization', icon: Building2, description: 'Available to everyone in your organization' },
  indaverse: { label: 'InDEVerse', icon: Globe, description: 'Shared with the global Innovation Network' },
};

/**
 * ConfidenceStars - Displays confidence as stars
 */
function ConfidenceStars({ tier }) {
  const config = CONFIDENCE_CONFIG[tier] || CONFIDENCE_CONFIG.MODERATE;
  return (
    <div className={cn('flex items-center gap-1 px-2 py-0.5 rounded', config.bg)}>
      {[1, 2, 3].map((n) => (
        <Star
          key={n}
          className={cn('w-3 h-3', n <= config.stars ? config.color : 'text-zinc-600')}
          fill={n <= config.stars ? 'currentColor' : 'none'}
        />
      ))}
    </div>
  );
}

/**
 * ActivityChip - Interactive activity chip
 */
function ActivityChip({ activity, onToggle, onRemove }) {
  const isOptional = activity.optional;
  const name = typeof activity === 'string' ? activity : activity.name;

  return (
    <div
      className={cn(
        'group flex items-center gap-1.5 px-2.5 py-1 rounded-full text-caption transition-colors cursor-pointer',
        isOptional
          ? 'border border-zinc-600 text-zinc-400 hover:border-zinc-500'
          : 'bg-surface-5 text-zinc-300 hover:bg-surface-4'
      )}
      onClick={onToggle}
    >
      <span className={isOptional ? 'italic' : ''}>{name}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-rose-400 transition-opacity"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

/**
 * AddActivityInput - Inline input for adding activities
 */
function AddActivityInput({ onAdd, onCancel }) {
  const [value, setValue] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    if (value.trim()) {
      onAdd(value.trim());
      setValue('');
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSubmit();
          if (e.key === 'Escape') onCancel();
        }}
        placeholder="Activity name..."
        className="w-32 px-2 py-1 bg-surface-5 border border-surface-border rounded text-caption text-zinc-200 placeholder:text-zinc-600"
      />
      <button onClick={handleSubmit} className="text-emerald-400 hover:text-emerald-300">
        <Check className="w-4 h-4" />
      </button>
      <button onClick={onCancel} className="text-zinc-500 hover:text-zinc-400">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

/**
 * PhaseCard - Draggable phase card for review
 */
function PhaseCard({ phase, index, isActive, onRename, onActivityToggle, onActivityRemove, onActivityAdd, onDragStart, onDragOver, onDrop }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(phase.name);
  const [showAddActivity, setShowAddActivity] = useState(false);
  const config = CONFIDENCE_CONFIG[phase.confidence_tier] || CONFIDENCE_CONFIG.MODERATE;

  const handleNameSave = () => {
    if (editedName.trim() && editedName !== phase.name) {
      onRename(editedName.trim());
    }
    setIsEditing(false);
  };

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, index)}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, index)}
      className={cn(
        'bg-surface-4 border rounded-xl p-4 transition-all cursor-move',
        isActive ? 'border-inde-500 ring-1 ring-inde-500/20' : 'border-surface-border hover:border-zinc-600'
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="p-1 text-zinc-600 cursor-grab active:cursor-grabbing">
          <GripVertical className="w-4 h-4" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-caption text-zinc-500 font-mono">Phase {index + 1}</span>
            <ConfidenceStars tier={phase.confidence_tier} />
          </div>
          {isEditing ? (
            <input
              type="text"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              onBlur={handleNameSave}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleNameSave();
                if (e.key === 'Escape') {
                  setEditedName(phase.name);
                  setIsEditing(false);
                }
              }}
              autoFocus
              className="w-full px-2 py-1 bg-surface-5 border border-inde-500 rounded text-body-sm text-zinc-200"
            />
          ) : (
            <h4
              className="text-body-sm font-medium text-zinc-200 cursor-pointer hover:text-inde-400 flex items-center gap-2"
              onDoubleClick={() => setIsEditing(true)}
            >
              {phase.name}
              <Edit3 className="w-3 h-3 opacity-0 group-hover:opacity-50" />
            </h4>
          )}
        </div>
        {phase.occurrence_rate && (
          <span className="text-caption text-zinc-500">
            {phase.occurrence_rate}% occurrence
          </span>
        )}
      </div>

      {/* Activities */}
      <div className="flex flex-wrap gap-2 mb-3">
        {phase.activities?.map((activity, idx) => (
          <ActivityChip
            key={idx}
            activity={activity}
            onToggle={() => onActivityToggle(phase.id, idx)}
            onRemove={() => onActivityRemove(phase.id, idx)}
          />
        ))}
        {showAddActivity ? (
          <AddActivityInput
            onAdd={(name) => {
              onActivityAdd(phase.id, name);
              setShowAddActivity(false);
            }}
            onCancel={() => setShowAddActivity(false)}
          />
        ) : (
          <button
            onClick={() => setShowAddActivity(true)}
            className="flex items-center gap-1 px-2 py-1 text-caption text-inde-400 hover:text-inde-300 border border-dashed border-inde-500/30 rounded-full"
          >
            <Plus className="w-3 h-3" />
            <span>Add</span>
          </button>
        )}
      </div>

      {/* Tools */}
      {phase.tools && phase.tools.length > 0 && (
        <div className="text-caption text-zinc-600">
          Tools: {phase.tools.join(', ')}
        </div>
      )}
    </div>
  );
}

/**
 * ProcessFlowVisualization - SVG flow diagram
 */
function ProcessFlowVisualization({ phases }) {
  if (!phases || phases.length === 0) return null;

  const width = 600;
  const height = 80;
  const nodeWidth = 100;
  const nodeHeight = 36;
  const nodeGap = 40;
  const startX = 20;
  const centerY = height / 2;

  return (
    <div className="bg-surface-4 rounded-xl p-4 overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-20 min-w-[500px]">
        {phases.map((phase, idx) => {
          const x = startX + idx * (nodeWidth + nodeGap);
          const y = centerY - nodeHeight / 2;

          return (
            <g key={phase.id || idx}>
              {/* Connection arrow */}
              {idx > 0 && (
                <g>
                  <line
                    x1={x - nodeGap + 10}
                    y1={centerY}
                    x2={x - 10}
                    y2={centerY}
                    stroke="rgb(113 113 122)"
                    strokeWidth="2"
                  />
                  <polygon
                    points={`${x - 10},${centerY - 4} ${x - 10},${centerY + 4} ${x - 4},${centerY}`}
                    fill="rgb(113 113 122)"
                  />
                </g>
              )}

              {/* Phase node */}
              <rect
                x={x}
                y={y}
                width={nodeWidth}
                height={nodeHeight}
                rx="8"
                fill="rgb(39 39 42)"
                stroke="rgb(99 102 241)"
                strokeWidth="2"
              />
              <text
                x={x + nodeWidth / 2}
                y={centerY + 4}
                textAnchor="middle"
                className="fill-zinc-200 text-[11px]"
              >
                {(phase.name || `Phase ${idx + 1}`).slice(0, 12)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/**
 * ComparisonView - Split-screen comparison
 */
function ComparisonView({ methodology, archetypes, selectedArchetype, onSelectArchetype, onClose }) {
  const selected = archetypes?.find((a) => a.id === selectedArchetype) || archetypes?.[0];

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex">
      {/* Left side - Your methodology */}
      <div className="flex-1 bg-surface-2 p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-body-lg font-medium text-zinc-200">Your Methodology</h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="space-y-4">
          {methodology.phases?.map((phase, idx) => (
            <div key={idx} className="bg-surface-4 rounded-lg p-4">
              <h4 className="text-body-sm font-medium text-zinc-200 mb-2">
                {idx + 1}. {phase.name}
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {phase.activities?.map((act, i) => (
                  <span
                    key={i}
                    className={cn(
                      'px-2 py-0.5 rounded text-caption',
                      act.optional ? 'text-blue-400 bg-blue-500/10' : 'text-zinc-300 bg-surface-5'
                    )}
                  >
                    {act.name || act}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="w-px bg-surface-border" />

      {/* Right side - Selected archetype */}
      <div className="flex-1 bg-surface-3 p-6 overflow-y-auto">
        <div className="mb-6">
          <label className="text-caption text-zinc-500 block mb-2">Compare with:</label>
          <select
            value={selectedArchetype || ''}
            onChange={(e) => onSelectArchetype(e.target.value)}
            className="w-full px-3 py-2 bg-surface-4 border border-surface-border rounded-lg text-body-sm text-zinc-200"
          >
            {archetypes?.map((arch) => (
              <option key={arch.id} value={arch.id}>
                {arch.name}
              </option>
            ))}
          </select>
        </div>

        {selected && (
          <div className="space-y-4">
            {selected.phases?.map((phase, idx) => (
              <div key={idx} className="bg-surface-4 rounded-lg p-4">
                <h4 className="text-body-sm font-medium text-zinc-400 mb-2">
                  {idx + 1}. {phase.name}
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {phase.activities?.map((act, i) => {
                    const actName = act.name || act;
                    const isShared = methodology.phases?.some((p) =>
                      p.activities?.some((a) => (a.name || a) === actName)
                    );
                    return (
                      <span
                        key={i}
                        className={cn(
                          'px-2 py-0.5 rounded text-caption',
                          isShared ? 'text-emerald-400 bg-emerald-500/10' : 'text-zinc-500 bg-surface-5'
                        )}
                      >
                        {actName}
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * NamingPanel - Name and describe the methodology
 */
function NamingPanel({ name, description, principles, suggestions, onChange, onClose }) {
  const [localName, setLocalName] = useState(name || '');
  const [localDesc, setLocalDesc] = useState(description || '');
  const [localPrinciples, setLocalPrinciples] = useState(principles || []);
  const [newPrinciple, setNewPrinciple] = useState('');

  const handleSave = () => {
    onChange({
      name: localName,
      description: localDesc,
      principles: localPrinciples,
    });
    onClose();
  };

  const addPrinciple = (text) => {
    if (text && !localPrinciples.includes(text)) {
      setLocalPrinciples([...localPrinciples, text]);
    }
    setNewPrinciple('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-surface-3 border border-surface-border rounded-xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="text-body-lg font-medium text-zinc-100">Name Your Methodology</h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Name */}
          <div>
            <label className="text-body-sm text-zinc-300 block mb-2">Methodology Name *</label>
            <input
              type="text"
              value={localName}
              onChange={(e) => setLocalName(e.target.value)}
              placeholder="e.g., Customer-First Discovery"
              className="w-full px-3 py-2 bg-surface-4 border border-surface-border rounded-lg text-body-sm text-zinc-200 placeholder:text-zinc-600"
            />
            {suggestions?.names?.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {suggestions.names.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setLocalName(s)}
                    className="px-2 py-1 bg-surface-5 hover:bg-surface-4 text-caption text-zinc-400 rounded"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="text-body-sm text-zinc-300 block mb-2">Description *</label>
            <textarea
              value={localDesc}
              onChange={(e) => setLocalDesc(e.target.value)}
              placeholder="Describe what makes this methodology unique..."
              rows={3}
              className="w-full px-3 py-2 bg-surface-4 border border-surface-border rounded-lg text-body-sm text-zinc-200 placeholder:text-zinc-600 resize-none"
            />
          </div>

          {/* Key Principles */}
          <div>
            <label className="text-body-sm text-zinc-300 block mb-2">Key Principles</label>
            <div className="space-y-2 mb-3">
              {localPrinciples.map((p, i) => (
                <div key={i} className="flex items-center gap-2 bg-surface-4 px-3 py-2 rounded-lg">
                  <span className="flex-1 text-body-sm text-zinc-300">{p}</span>
                  <button
                    onClick={() => setLocalPrinciples(localPrinciples.filter((_, idx) => idx !== i))}
                    className="text-zinc-500 hover:text-rose-400"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newPrinciple}
                onChange={(e) => setNewPrinciple(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') addPrinciple(newPrinciple);
                }}
                placeholder="Add a principle..."
                className="flex-1 px-3 py-2 bg-surface-4 border border-surface-border rounded-lg text-body-sm text-zinc-200 placeholder:text-zinc-600"
              />
              <button
                onClick={() => addPrinciple(newPrinciple)}
                className="px-3 py-2 bg-inde-500/10 text-inde-400 rounded-lg"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            {suggestions?.principles?.length > 0 && (
              <div className="mt-3">
                <p className="text-caption text-zinc-500 mb-2">Suggested by coach:</p>
                <div className="space-y-1">
                  {suggestions.principles.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => addPrinciple(s)}
                      className="w-full text-left px-3 py-2 bg-surface-5 hover:bg-surface-4 text-caption text-zinc-400 rounded"
                    >
                      + {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-surface-border flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-body-sm text-zinc-400">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!localName.trim() || !localDesc.trim()}
            className="px-4 py-2 bg-inde-500 hover:bg-inde-600 text-white rounded-lg text-body-sm disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * VisibilitySelector - Radio group for visibility
 */
function VisibilitySelector({ value, onChange }) {
  return (
    <div className="space-y-2">
      {Object.entries(VISIBILITY_CONFIG).map(([key, config]) => {
        const Icon = config.icon;
        return (
          <button
            key={key}
            onClick={() => onChange(key)}
            className={cn(
              'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors',
              value === key
                ? 'bg-inde-500/10 border border-inde-500/30 text-inde-400'
                : 'bg-surface-4 border border-surface-border text-zinc-400 hover:bg-surface-5'
            )}
          >
            <Icon className="w-5 h-5" />
            <div>
              <p className="text-body-sm font-medium">{config.label}</p>
              <p className="text-caption text-zinc-500">{config.description}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

/**
 * PublishConfirmationModal - Confirmation before publishing
 */
function PublishConfirmationModal({ methodology, visibility, onConfirm, onCancel, isPublishing }) {
  const visConfig = VISIBILITY_CONFIG[visibility] || VISIBILITY_CONFIG.personal;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-surface-3 border border-surface-border rounded-xl w-full max-w-md">
        <div className="p-6">
          <h3 className="text-body-lg font-medium text-zinc-100 mb-4">
            Publish "{methodology.name}"?
          </h3>

          <div className="space-y-3 mb-6">
            <div className="flex items-center justify-between text-body-sm">
              <span className="text-zinc-500">Phases</span>
              <span className="text-zinc-200">{methodology.phases?.length || 0}</span>
            </div>
            <div className="flex items-center justify-between text-body-sm">
              <span className="text-zinc-500">Confidence</span>
              <span className="text-zinc-200 capitalize">{methodology.confidence_tier || 'Moderate'}</span>
            </div>
            <div className="flex items-center justify-between text-body-sm">
              <span className="text-zinc-500">Visibility</span>
              <span className="text-zinc-200">{visConfig.label}</span>
            </div>
            <div className="flex items-center justify-between text-body-sm">
              <span className="text-zinc-500">Version</span>
              <span className="text-zinc-200">1.0</span>
            </div>
          </div>

          <p className="text-body-sm text-zinc-400 mb-6">
            Once published, this methodology will appear in your archetype selection for future pursuits.
          </p>

          <div className="flex justify-end gap-3">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-body-sm text-zinc-400"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isPublishing}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-body-sm disabled:opacity-50"
            >
              {isPublishing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              Publish
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ReviewChat - Coaching chat for review session
 */
function ReviewChat({ sessionId, messages, onSendMessage, isSending }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages?.map((msg, idx) => (
          <div
            key={idx}
            className={cn(
              'max-w-[85%] p-3 rounded-xl',
              msg.role === 'coach'
                ? 'bg-surface-4 text-zinc-200 mr-auto'
                : 'bg-inde-500/10 text-inde-300 ml-auto'
            )}
          >
            <p className="text-body-sm">{msg.content}</p>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-surface-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Discuss with your coach..."
            className="flex-1 px-3 py-2 bg-surface-4 border border-surface-border rounded-lg text-body-sm text-zinc-200 placeholder:text-zinc-600"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className="px-3 py-2 bg-inde-500 hover:bg-inde-600 text-white rounded-lg disabled:opacity-50"
          >
            {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * ReviewSession - Main review session component
 */
export function ReviewSession() {
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  // Local state
  const [phases, setPhases] = useState([]);
  const [dragIndex, setDragIndex] = useState(null);
  const [showComparison, setShowComparison] = useState(false);
  const [showNaming, setShowNaming] = useState(false);
  const [showPublishConfirm, setShowPublishConfirm] = useState(false);
  const [selectedArchetype, setSelectedArchetype] = useState(null);
  const [methodology, setMethodology] = useState({
    name: '',
    description: '',
    principles: [],
    visibility: 'personal',
  });
  const [messages, setMessages] = useState([]);

  // Fetch session status
  const { data: sessionData, isLoading } = useQuery({
    queryKey: ['ems-review-session', sessionId],
    queryFn: async () => {
      const response = await emsApi.getReviewStatus(sessionId);
      return response.data;
    },
    enabled: !!sessionId,
    onSuccess: (data) => {
      if (data.refined_archetype?.phases) {
        setPhases(data.refined_archetype.phases);
      }
      if (data.messages) {
        setMessages(data.messages);
      }
      if (data.methodology_name) {
        setMethodology((m) => ({ ...m, name: data.methodology_name }));
      }
    },
  });

  // Fetch comparison archetypes
  const { data: archetypes } = useQuery({
    queryKey: ['ems-comparison-archetypes', sessionId],
    queryFn: async () => {
      const response = await emsApi.getComparison(sessionId);
      return response.data?.archetypes || [];
    },
    enabled: !!sessionId,
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (message) => {
      return emsApi.sendReviewMessage(sessionId, message);
    },
    onSuccess: (response) => {
      const newMessages = response.data?.messages || [];
      setMessages((prev) => [...prev, ...newMessages]);
      if (response.data?.refined_archetype?.phases) {
        setPhases(response.data.refined_archetype.phases);
      }
    },
  });

  // Set name mutation
  const setNameMutation = useMutation({
    mutationFn: async ({ name }) => {
      return emsApi.setMethodologyName(sessionId, name);
    },
  });

  // Set visibility mutation
  const setVisibilityMutation = useMutation({
    mutationFn: async (visibility) => {
      return emsApi.setVisibility(sessionId, visibility);
    },
  });

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: async () => {
      return emsApi.approvePublication(sessionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['ems-archetypes-mine']);
      navigate('/ems');
    },
  });

  // Drag handlers
  const handleDragStart = (e, index) => {
    setDragIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e, targetIndex) => {
    e.preventDefault();
    if (dragIndex === null || dragIndex === targetIndex) return;

    const newPhases = [...phases];
    const [removed] = newPhases.splice(dragIndex, 1);
    newPhases.splice(targetIndex, 0, removed);
    setPhases(newPhases);
    setDragIndex(null);

    // Send reorder refinement
    sendMessageMutation.mutate('');
  };

  // Activity handlers
  const handleActivityToggle = (phaseId, activityIndex) => {
    setPhases((prev) =>
      prev.map((p) => {
        if (p.id !== phaseId) return p;
        const newActivities = [...p.activities];
        const activity = newActivities[activityIndex];
        if (typeof activity === 'string') {
          newActivities[activityIndex] = { name: activity, optional: true };
        } else {
          newActivities[activityIndex] = { ...activity, optional: !activity.optional };
        }
        return { ...p, activities: newActivities };
      })
    );
  };

  const handleActivityRemove = (phaseId, activityIndex) => {
    setPhases((prev) =>
      prev.map((p) => {
        if (p.id !== phaseId) return p;
        return {
          ...p,
          activities: p.activities.filter((_, i) => i !== activityIndex),
        };
      })
    );
  };

  const handleActivityAdd = (phaseId, activityName) => {
    setPhases((prev) =>
      prev.map((p) => {
        if (p.id !== phaseId) return p;
        return {
          ...p,
          activities: [...p.activities, { name: activityName, optional: false }],
        };
      })
    );
  };

  const handlePhaseRename = (phaseId, newName) => {
    setPhases((prev) =>
      prev.map((p) => (p.id === phaseId ? { ...p, name: newName } : p))
    );
  };

  const handleNamingChange = (data) => {
    setMethodology((m) => ({ ...m, ...data }));
    if (data.name) {
      setNameMutation.mutate({ name: data.name });
    }
  };

  const handleVisibilityChange = (visibility) => {
    setMethodology((m) => ({ ...m, visibility }));
    setVisibilityMutation.mutate(visibility);
  };

  const handlePublish = () => {
    publishMutation.mutate();
  };

  const handleSendMessage = (message) => {
    setMessages((prev) => [...prev, { role: 'innovator', content: message }]);
    sendMessageMutation.mutate(message);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-inde-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/ems')}
            className="p-2 hover:bg-surface-4 rounded-lg text-zinc-500"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-body-lg font-medium text-zinc-100">
              Review Your Discovered Methodology
            </h1>
            <p className="text-caption text-zinc-500">
              Phase {sessionData?.current_phase || 1} of {sessionData?.total_phases || phases.length}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowComparison(true)}
            className="flex items-center gap-2 px-3 py-2 bg-surface-4 hover:bg-surface-5 text-zinc-300 rounded-lg text-body-sm"
          >
            <GitCompare className="w-4 h-4" />
            Compare
          </button>
          <button
            onClick={() => setShowNaming(true)}
            className="flex items-center gap-2 px-3 py-2 bg-surface-4 hover:bg-surface-5 text-zinc-300 rounded-lg text-body-sm"
          >
            <FileText className="w-4 h-4" />
            Name & Describe
          </button>
          <button
            onClick={() => setShowPublishConfirm(true)}
            disabled={!methodology.name}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-body-sm disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            Publish
          </button>
        </div>
      </div>

      {/* Main content - split view */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left side - Phase cards (60%) */}
        <div className="w-3/5 flex flex-col overflow-hidden border-r border-surface-border">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {phases.map((phase, idx) => (
              <PhaseCard
                key={phase.id || idx}
                phase={phase}
                index={idx}
                isActive={idx === sessionData?.current_phase - 1}
                onRename={(name) => handlePhaseRename(phase.id, name)}
                onActivityToggle={handleActivityToggle}
                onActivityRemove={handleActivityRemove}
                onActivityAdd={handleActivityAdd}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              />
            ))}
          </div>

          {/* Process flow visualization */}
          <div className="p-4 border-t border-surface-border">
            <ProcessFlowVisualization phases={phases} />
          </div>

          {/* Visibility selector */}
          <div className="p-4 border-t border-surface-border">
            <h4 className="text-body-sm font-medium text-zinc-300 mb-3">Visibility</h4>
            <VisibilitySelector
              value={methodology.visibility}
              onChange={handleVisibilityChange}
            />
          </div>
        </div>

        {/* Right side - Coach chat (40%) */}
        <div className="w-2/5 bg-surface-2">
          <ReviewChat
            sessionId={sessionId}
            messages={messages}
            onSendMessage={handleSendMessage}
            isSending={sendMessageMutation.isPending}
          />
        </div>
      </div>

      {/* Modals */}
      {showComparison && (
        <ComparisonView
          methodology={{ ...methodology, phases }}
          archetypes={archetypes}
          selectedArchetype={selectedArchetype}
          onSelectArchetype={setSelectedArchetype}
          onClose={() => setShowComparison(false)}
        />
      )}

      {showNaming && (
        <NamingPanel
          name={methodology.name}
          description={methodology.description}
          principles={methodology.principles}
          suggestions={sessionData?.suggestions}
          onChange={handleNamingChange}
          onClose={() => setShowNaming(false)}
        />
      )}

      {showPublishConfirm && (
        <PublishConfirmationModal
          methodology={{ ...methodology, phases }}
          visibility={methodology.visibility}
          onConfirm={handlePublish}
          onCancel={() => setShowPublishConfirm(false)}
          isPublishing={publishMutation.isPending}
        />
      )}
    </div>
  );
}

export default ReviewSession;
