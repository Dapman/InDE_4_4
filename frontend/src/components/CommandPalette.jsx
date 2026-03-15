import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePursuitStore } from '../stores/pursuitStore';
import { useCoachingStore } from '../stores/coachingStore';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from './ui/command';
import {
  Home,
  BarChart3,
  Sparkles,
  Globe,
  Settings,
  Plus,
  Rocket,
  Eye,
  Shield,
  History,
  FileText,
  Beaker,
  MessageSquare,
} from 'lucide-react';

const ARCHETYPE_EMOJIS = {
  lean_startup: '🔬',
  design_thinking: '🎨',
  stage_gate: '🏗️',
  triz: '🧩',
  blue_ocean: '🌊',
  freeform: '✨',
};

const NAVIGATION_ITEMS = [
  { id: 'dashboard', label: 'Go to Dashboard', icon: Home, path: '/' },
  { id: 'analytics', label: 'Go to Analytics', icon: BarChart3, path: '/analytics' },
  { id: 'ems', label: 'Go to EMS', icon: Sparkles, path: '/ems' },
  { id: 'ikf', label: 'Go to IKF', icon: Globe, path: '/ikf' },
  { id: 'settings', label: 'Go to Settings', icon: Settings, path: '/settings' },
];

const COACHING_ACTIONS = [
  // v4.0: Commands use innovator-facing goal vocabulary
  {
    id: 'vision',
    label: 'Tell Your Story',
    icon: Eye,
    emoji: '📖',
    mode: 'vision',
    description: 'Articulate what you\'re building and who it\'s for',
  },
  {
    id: 'fear',
    label: 'Protect Your Idea',
    icon: Shield,
    emoji: '🛡️',
    mode: 'fear',
    description: 'Identify what could get in the way',
  },
  {
    id: 'retrospective',
    label: 'Capture What You Learned',
    icon: History,
    emoji: '💡',
    mode: 'retrospective',
    description: 'Reflect on your innovation journey',
  },
  {
    id: 'experiment',
    label: 'Design Experiment',
    icon: Beaker,
    emoji: '🧪',
    mode: 'coaching',
    description: 'Create a validation experiment',
  },
];

export function CommandPalette({ open, onOpenChange }) {
  const navigate = useNavigate();
  const { pursuitList, activePursuitId, setActivePursuit } = usePursuitStore();
  const setMode = useCoachingStore((s) => s.setMode);
  const [search, setSearch] = useState('');

  const activePursuits = useMemo(
    () => pursuitList.filter((p) => p.state === 'ACTIVE' || p.state === 'PENDING'),
    [pursuitList]
  );

  // Get keyboard shortcut display
  const getShortcutKey = (index) => {
    const isMac = navigator.platform.includes('Mac');
    return index < 9 ? `${isMac ? '⌘' : 'Ctrl+'}${index + 1}` : null;
  };

  const handleSelect = useCallback(
    (callback) => {
      onOpenChange(false);
      setSearch('');
      callback();
    },
    [onOpenChange]
  );

  const handleNavigation = useCallback(
    (path) => {
      handleSelect(() => navigate(path));
    },
    [handleSelect, navigate]
  );

  const handlePursuitSelect = useCallback(
    (pursuit) => {
      handleSelect(() => {
        setActivePursuit(pursuit.id);
        navigate(`/pursuit/${pursuit.id}`);
      });
    },
    [handleSelect, setActivePursuit, navigate]
  );

  const handleNewPursuit = useCallback(() => {
    handleSelect(() => navigate('/pursuit/new'));
  }, [handleSelect, navigate]);

  const handleCoachingAction = useCallback(
    (action) => {
      handleSelect(() => {
        // Set the coaching mode
        if (action.mode) {
          setMode(action.mode);
        }
        // If not on a pursuit, navigate to active one or dashboard
        if (!activePursuitId && activePursuits.length > 0) {
          setActivePursuit(activePursuits[0].id);
          navigate(`/pursuit/${activePursuits[0].id}`);
        }
      });
    },
    [handleSelect, setMode, activePursuitId, activePursuits, setActivePursuit, navigate]
  );

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        placeholder="Search commands, pursuits..."
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Quick Actions */}
        <CommandGroup heading="Quick Actions">
          <CommandItem value="new-pursuit create" onSelect={handleNewPursuit}>
            <Plus className="mr-2 h-4 w-4 text-inde-400" />
            <span>New Innovation Pursuit</span>
            <CommandShortcut>
              {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl+'}N
            </CommandShortcut>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Pursuits */}
        {activePursuits.length > 0 && (
          <>
            <CommandGroup heading="Switch Pursuit">
              {activePursuits.slice(0, 9).map((pursuit, index) => {
                const emoji = ARCHETYPE_EMOJIS[pursuit.archetype] || '✨';
                const isActive = pursuit.id === activePursuitId;
                const shortcut = getShortcutKey(index);

                return (
                  <CommandItem
                    key={pursuit.id}
                    value={`pursuit-${pursuit.name} ${pursuit.archetype}`}
                    onSelect={() => handlePursuitSelect(pursuit)}
                  >
                    <span className="mr-2 text-base">{emoji}</span>
                    <span className={isActive ? 'text-inde-400' : ''}>
                      {pursuit.name}
                    </span>
                    {isActive && (
                      <span className="ml-2 text-caption text-zinc-600">(current)</span>
                    )}
                    {shortcut && <CommandShortcut>{shortcut}</CommandShortcut>}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {/* Coaching Actions */}
        {activePursuitId && (
          <>
            <CommandGroup heading="Coaching">
              {COACHING_ACTIONS.map((action) => {
                const Icon = action.icon;
                return (
                  <CommandItem
                    key={action.id}
                    value={`${action.label} ${action.description}`}
                    onSelect={() => handleCoachingAction(action)}
                  >
                    <span className="mr-2 text-base">{action.emoji}</span>
                    <div className="flex-1">
                      <span>{action.label}</span>
                      <span className="ml-2 text-caption text-zinc-600">
                        {action.description}
                      </span>
                    </div>
                  </CommandItem>
                );
              })}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {/* Navigation */}
        <CommandGroup heading="Navigation">
          {NAVIGATION_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <CommandItem
                key={item.id}
                value={item.label}
                onSelect={() => handleNavigation(item.path)}
              >
                <Icon className="mr-2 h-4 w-4 text-zinc-400" />
                <span>{item.label}</span>
              </CommandItem>
            );
          })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

export default CommandPalette;
