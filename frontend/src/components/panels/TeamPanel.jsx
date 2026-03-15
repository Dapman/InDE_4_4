import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Users,
  Activity,
  BarChart3,
  User,
  UserPlus,
  Circle,
  FileText,
  GitMerge,
  Zap,
  ArrowRight,
  Printer,
} from 'lucide-react';
import { pursuitsApi } from '../../api/pursuits';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';
import { cn } from '../../lib/utils';
import { formatDistanceToNow } from '../../lib/dateUtils';
import { printTeam } from '../../lib/print';

// Sub-tab definitions
const SUB_TABS = [
  { id: 'roster', icon: Users, label: 'Roster' },
  { id: 'activity', icon: Activity, label: 'Activity' },
  { id: 'gaps', icon: BarChart3, label: 'Gaps' },
];

// Role badge colors
const ROLE_COLORS = {
  owner: 'bg-inde-500/20 text-inde-400',
  editor: 'bg-phase-vision/20 text-phase-vision',
  contributor: 'bg-health-healthy/20 text-health-healthy',
  viewer: 'bg-zinc-500/20 text-zinc-400',
};

// Activity type icons
const ACTIVITY_ICONS = {
  capture: FileText,
  generate: Zap,
  advance: ArrowRight,
  converge: GitMerge,
  default: Activity,
};

// Team member card component
function MemberCard({ member }) {
  const isOnline = member.status === 'online' || member.is_online;
  const roleColor = ROLE_COLORS[member.role?.toLowerCase()] || ROLE_COLORS.viewer;

  return (
    <div className="flex items-center gap-3 py-3 border-b border-surface-border/50 last:border-0">
      {/* Avatar */}
      <div className="relative">
        <div className="w-8 h-8 rounded-full bg-surface-3 flex items-center justify-center text-caption font-medium text-zinc-400">
          {member.name?.charAt(0)?.toUpperCase() || member.email?.charAt(0)?.toUpperCase() || 'U'}
        </div>
        {/* Online indicator */}
        <span
          className={cn(
            'absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-surface-2',
            isOnline ? 'bg-health-healthy' : 'bg-zinc-500'
          )}
        />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-caption text-zinc-300 truncate">
            {member.name || member.email}
          </span>
          <span className={cn('text-caption px-1.5 py-0.5 rounded-badge', roleColor)}>
            {member.role}
          </span>
        </div>
        <div className="text-caption text-zinc-500">
          {isOnline ? (
            'Active now'
          ) : member.last_seen ? (
            `Last seen ${formatDistanceToNow(member.last_seen)}`
          ) : (
            'Never active'
          )}
        </div>
      </div>

      {/* Contribution count */}
      {member.contributions !== undefined && (
        <div className="text-caption text-zinc-500">
          {member.contributions} contrib.
        </div>
      )}
    </div>
  );
}

// Activity event component
function ActivityEvent({ event }) {
  const Icon = ACTIVITY_ICONS[event.type?.toLowerCase()] || ACTIVITY_ICONS.default;

  // Color based on event type
  const colors = {
    capture: 'text-blue-400',
    generate: 'text-purple-400',
    advance: 'text-health-healthy',
    converge: 'text-inde-400',
    default: 'text-zinc-400',
  };
  const color = colors[event.type?.toLowerCase()] || colors.default;

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-surface-border/50 last:border-0">
      <div className={cn('p-1.5 rounded-full bg-surface-3', color)}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-caption text-zinc-300">
          <span className="font-medium">{event.user || event.actor}</span>
          {' '}
          <span className="text-zinc-500">{event.action || event.description}</span>
        </div>
        {event.target && (
          <div className="text-caption text-zinc-400 truncate mt-0.5">
            "{event.target}"
          </div>
        )}
        <div className="text-caption text-zinc-600 mt-0.5">
          {formatDistanceToNow(event.timestamp || event.created_at)}
        </div>
      </div>
    </div>
  );
}

// Gap item component
function GapItem({ element, suggestedAssignee }) {
  const displayLabel = useDisplayLabel('scaffolding_elements', element);

  return (
    <div className="flex items-center justify-between py-2 border-b border-surface-border/50 last:border-0">
      <div className="flex items-center gap-2">
        <Circle className="h-3 w-3 text-zinc-600" />
        <span className="text-caption text-zinc-400">
          {displayLabel.label}
        </span>
      </div>
      {suggestedAssignee && (
        <span className="text-caption text-inde-400">
          Suggested: {suggestedAssignee}
        </span>
      )}
    </div>
  );
}

// Contribution balance bar
function ContributionBar({ member, percentage }) {
  return (
    <div className="py-1.5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-caption text-zinc-400 truncate">
          {member.name || member.email}
        </span>
        <span className="text-caption text-zinc-500">{percentage}%</span>
      </div>
      <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
        <div
          className="h-full bg-inde-500 transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

/**
 * TeamPanel - Shows team roster, activity stream, and gap analysis.
 */
export function TeamPanel({ pursuitId, onSendMessage, onDataChange }) {
  const [activeTab, setActiveTab] = useState('roster');

  // Fetch team data
  const { data: teamData, isLoading: teamLoading } = useQuery({
    queryKey: ['team', pursuitId],
    queryFn: async () => {
      const response = await pursuitsApi.getTeam(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 30000,
  });

  // Fetch activity data (only when activity tab is active)
  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['activity', pursuitId],
    queryFn: async () => {
      // Activity endpoint would be at /api/pursuits/{id}/activity
      try {
        const response = await pursuitsApi.get(pursuitId);
        return response.data?.activity || response.data?.recent_activity || [];
      } catch (err) {
        return [];
      }
    },
    enabled: !!pursuitId && activeTab === 'activity',
    staleTime: 30000,
    refetchInterval: 30000,
  });

  // Parse team data
  const { members, activity, gaps, contributions } = useMemo(() => {
    const data = teamData || {};

    const memberList = data.members || data.team || [];
    const activityList = activityData || data.activity || [];
    const gapsList = data.gaps || data.unaddressed_elements || [];

    // Calculate contribution percentages
    const totalContributions = memberList.reduce((sum, m) => sum + (m.contributions || 0), 0);
    const contribData = memberList.map((m) => ({
      ...m,
      percentage: totalContributions > 0
        ? Math.round(((m.contributions || 0) / totalContributions) * 100)
        : 0,
    }));

    return {
      members: memberList,
      activity: activityList,
      gaps: gapsList,
      contributions: contribData,
    };
  }, [teamData, activityData]);

  const isLoading = teamLoading || (activeTab === 'activity' && activityLoading);

  // Handle print
  const handlePrint = () => {
    printTeam({
      members,
      activity,
      gaps,
    });
  };

  if (isLoading && !teamData) {
    return (
      <div className="p-4 flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-inde-500/30 border-t-inde-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Sub-tab bar */}
      <div className="flex border-b border-surface-border">
        <button
          onClick={handlePrint}
          className="p-2 hover:bg-surface-3 transition-colors"
          title="Print team report"
        >
          <Printer className="h-3.5 w-3.5 text-zinc-500 hover:text-zinc-300" />
        </button>
        {SUB_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 px-2 py-2 text-caption transition-colors',
              activeTab === tab.id
                ? 'text-inde-400 border-b-2 border-inde-500 -mb-px'
                : 'text-zinc-500 hover:text-zinc-300'
            )}
          >
            <tab.icon className="h-3.5 w-3.5" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Roster tab */}
        {activeTab === 'roster' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-caption text-zinc-500">
                Team ({members.length} members)
              </span>
              <button
                className="text-caption text-inde-400 hover:text-inde-300 flex items-center gap-1"
                title="Invite functionality coming soon"
              >
                <UserPlus className="h-3.5 w-3.5" />
                Invite
              </button>
            </div>

            {members.length > 0 ? (
              <div>
                {members.map((member, i) => (
                  <MemberCard key={member.id || member.user_id || i} member={member} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Users className="h-8 w-8 text-zinc-600 mx-auto mb-2" />
                <p className="text-caption text-zinc-500">Solo pursuit</p>
                <p className="text-caption text-zinc-600 mt-1">
                  Invite team members to collaborate
                </p>
              </div>
            )}
          </div>
        )}

        {/* Activity tab */}
        {activeTab === 'activity' && (
          <div>
            <div className="text-caption text-zinc-500 mb-3">Recent Activity</div>

            {activity.length > 0 ? (
              <div>
                {activity.slice(0, 20).map((event, i) => (
                  <ActivityEvent key={event.id || i} event={event} />
                ))}
                {activity.length > 20 && (
                  <button className="w-full py-2 text-caption text-inde-400 hover:text-inde-300">
                    Load more...
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <Activity className="h-8 w-8 text-zinc-600 mx-auto mb-2" />
                <p className="text-caption text-zinc-500">No recent activity</p>
              </div>
            )}
          </div>
        )}

        {/* Gaps tab */}
        {activeTab === 'gaps' && (
          <div>
            {/* Unaddressed elements */}
            <div className="mb-6">
              <div className="text-caption text-zinc-500 mb-3">
                Unaddressed ({gaps.length} elements)
              </div>

              {gaps.length > 0 ? (
                <div>
                  {gaps.map((gap, i) => (
                    <GapItem
                      key={gap.element || gap || i}
                      element={gap.element || gap}
                      suggestedAssignee={gap.suggested_assignee}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-caption text-health-healthy">
                    All elements addressed
                  </p>
                </div>
              )}
            </div>

            {/* Contribution balance */}
            {members.length > 1 && (
              <div>
                <div className="text-caption text-zinc-500 mb-3">
                  Contribution Balance
                </div>
                <div className="space-y-1">
                  {contributions
                    .sort((a, b) => b.percentage - a.percentage)
                    .map((member, i) => (
                      <ContributionBar
                        key={member.id || member.user_id || i}
                        member={member}
                        percentage={member.percentage}
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

export default TeamPanel;
