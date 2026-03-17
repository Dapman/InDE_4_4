/**
 * InDE v4.4.1 - Innovation Vitals Tab
 *
 * Admin-only component displaying per-user behavioral intelligence
 * for beta testing analysis. Aggregates innovation activity into
 * a single scannable table with engagement status classification.
 *
 * Features:
 * - Summary bar with status counts and color indicators
 * - Sortable table with primary columns
 * - Expandable row details (Last Login, Duration, Member Since)
 * - Status and experience level filter dropdowns
 * - Client-side search by name or email
 * - CSV export of filtered data
 * - Auto-refresh every 120 seconds
 *
 * 2026 Yul Williams | InDEVerse, Incorporated
 */

import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../../api/system';
import {
  RefreshCw,
  Download,
  Search,
  ChevronDown,
  ChevronUp,
  Users,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// =============================================================================
// STATUS COLORS AND LABELS
// =============================================================================

const STATUS_CONFIG = {
  ENGAGED: {
    color: 'bg-green-500',
    textColor: 'text-green-400',
    bgColor: 'bg-green-500/10',
    label: 'Engaged',
    description: 'Actively using the platform',
  },
  EXPLORING: {
    color: 'bg-blue-500',
    textColor: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    label: 'Exploring',
    description: 'Started but not deep',
  },
  'AT RISK': {
    color: 'bg-amber-500',
    textColor: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    label: 'At Risk',
    description: 'Gone quiet recently',
  },
  DORMANT: {
    color: 'bg-zinc-500',
    textColor: 'text-zinc-400',
    bgColor: 'bg-zinc-500/10',
    label: 'Dormant',
    description: 'Inactive or never started',
  },
  NEW: {
    color: 'bg-teal-500',
    textColor: 'text-teal-400',
    bgColor: 'bg-teal-500/10',
    label: 'New',
    description: 'Joined within 48 hours',
  },
};

const EXPERIENCE_LEVELS = ['All', 'NOVICE', 'COMPETENT', 'PROFICIENT', 'EXPERT', 'INTERMEDIATE'];

// =============================================================================
// SUMMARY BAR
// =============================================================================

function SummaryBar({ summary, generatedAt, onRefresh, isRefreshing }) {
  const getTimeSince = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  return (
    <div className="bg-surface-3 border border-surface-border rounded-lg p-4 mb-4">
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-inde-400" />
          <span className="text-body-md text-zinc-200">
            Innovators: <strong>{summary?.total || 0}</strong>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-caption text-zinc-500">
            Last updated: {getTimeSince(generatedAt)}
          </span>
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 rounded-md bg-surface-4 hover:bg-surface-border transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={cn('w-4 h-4 text-zinc-400', isRefreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Status counts */}
      <div className="flex flex-wrap items-center gap-4">
        {Object.entries(STATUS_CONFIG).map(([status, config]) => {
          const count = summary?.[status.toLowerCase().replace(' ', '_')] || 0;
          return (
            <div key={status} className="flex items-center gap-2">
              <span className={cn('w-2.5 h-2.5 rounded-full', config.color)} />
              <span className={cn('text-body-sm', config.textColor)}>
                {config.label}
              </span>
              <span className="text-body-sm text-zinc-300 font-medium">
                {count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// STATUS BADGE
// =============================================================================

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.DORMANT;

  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded text-caption font-medium',
      config.bgColor,
      config.textColor
    )}>
      {config.label}
    </span>
  );
}

// =============================================================================
// FILTER CONTROLS
// =============================================================================

function FilterControls({
  statusFilter,
  setStatusFilter,
  experienceFilter,
  setExperienceFilter,
  searchQuery,
  setSearchQuery,
  onExport,
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      {/* Status Filter */}
      <div className="flex items-center gap-2">
        <span className="text-caption text-zinc-500">Status:</span>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-surface-3 border border-surface-border rounded px-2 py-1.5 text-body-sm
                     text-zinc-300 focus:outline-none focus:ring-1 focus:ring-inde-500"
        >
          <option value="All">All Statuses</option>
          {Object.keys(STATUS_CONFIG).map((status) => (
            <option key={status} value={status}>
              {STATUS_CONFIG[status].label}
            </option>
          ))}
        </select>
      </div>

      {/* Experience Filter */}
      <div className="flex items-center gap-2">
        <span className="text-caption text-zinc-500">Experience:</span>
        <select
          value={experienceFilter}
          onChange={(e) => setExperienceFilter(e.target.value)}
          className="bg-surface-3 border border-surface-border rounded px-2 py-1.5 text-body-sm
                     text-zinc-300 focus:outline-none focus:ring-1 focus:ring-inde-500"
        >
          {EXPERIENCE_LEVELS.map((level) => (
            <option key={level} value={level}>
              {level === 'All' ? 'All Levels' : level.charAt(0) + level.slice(1).toLowerCase()}
            </option>
          ))}
        </select>
      </div>

      {/* Search */}
      <div className="flex-1 min-w-[200px] max-w-[300px]">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search name or email..."
            className="w-full bg-surface-3 border border-surface-border rounded pl-8 pr-3 py-1.5
                       text-body-sm text-zinc-300 placeholder:text-zinc-600
                       focus:outline-none focus:ring-1 focus:ring-inde-500"
          />
        </div>
      </div>

      {/* Export Button */}
      <button
        onClick={onExport}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-3 hover:bg-surface-4
                   border border-surface-border rounded text-body-sm text-zinc-300 transition-colors"
      >
        <Download className="w-4 h-4" />
        Export CSV
      </button>
    </div>
  );
}

// =============================================================================
// VITALS TABLE
// =============================================================================

function VitalsTable({ users, sortConfig, onSort }) {
  const [expandedRow, setExpandedRow] = useState(null);

  const formatDate = (timestamp) => {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays === 0) {
      const diffHours = Math.floor(diffMs / 3600000);
      if (diffHours === 0) {
        const diffMins = Math.floor(diffMs / 60000);
        return diffMins <= 1 ? 'Just now' : `${diffMins}m ago`;
      }
      return `${diffHours}h ago`;
    }
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  const getMemberSinceDays = (timestamp) => {
    if (!timestamp) return '—';
    const diffMs = Date.now() - new Date(timestamp).getTime();
    return Math.floor(diffMs / 86400000);
  };

  const SortHeader = ({ column, label, className }) => {
    const isActive = sortConfig.key === column;
    return (
      <th
        className={cn(
          'text-left py-2 px-3 text-zinc-500 font-medium cursor-pointer hover:text-zinc-300 transition-colors',
          className
        )}
        onClick={() => onSort(column)}
      >
        <div className="flex items-center gap-1">
          {label}
          {isActive && (
            sortConfig.direction === 'asc'
              ? <ChevronUp className="w-3 h-3" />
              : <ChevronDown className="w-3 h-3" />
          )}
        </div>
      </th>
    );
  };

  if (!users || users.length === 0) {
    return (
      <div className="text-center py-12 text-zinc-500">
        <Users className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-body-md">No innovators found</p>
        <p className="text-caption mt-1">Try adjusting your filters</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-body-sm">
        <thead>
          <tr className="border-b border-surface-border">
            <SortHeader column="display_name" label="Innovator" className="min-w-[180px]" />
            <SortHeader column="experience_level" label="Experience" />
            <SortHeader column="pursuits_created" label="Pursuits" />
            <SortHeader column="highest_phase_reached" label="Phase" />
            <SortHeader column="artifacts_count" label="Artifacts" />
            <SortHeader column="coaching_sessions" label="Sessions" />
            <SortHeader column="status" label="Status" />
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <>
              <tr
                key={user.user_id}
                className={cn(
                  'border-b border-surface-border/50 hover:bg-surface-3 cursor-pointer transition-colors',
                  expandedRow === user.user_id && 'bg-surface-3'
                )}
                onClick={() => setExpandedRow(expandedRow === user.user_id ? null : user.user_id)}
              >
                {/* Innovator (name + email) */}
                <td className="py-3 px-3">
                  <div>
                    <span className="text-zinc-200 font-medium block">
                      {user.display_name || 'Unknown'}
                    </span>
                    <span className="text-caption text-zinc-500">
                      {user.email || '—'}
                    </span>
                  </div>
                </td>

                {/* Experience */}
                <td className="py-3 px-3 text-zinc-400">
                  {user.experience_level
                    ? user.experience_level.charAt(0) + user.experience_level.slice(1).toLowerCase()
                    : '—'}
                </td>

                {/* Pursuits */}
                <td className="py-3 px-3 text-zinc-300 font-medium">
                  {user.pursuits_created}
                </td>

                {/* Phase */}
                <td className="py-3 px-3 text-zinc-400">
                  {user.highest_phase_reached
                    ? `Phase ${user.highest_phase_reached}`
                    : '—'}
                </td>

                {/* Artifacts */}
                <td className="py-3 px-3 text-zinc-300">
                  {user.artifacts_count}
                </td>

                {/* Sessions */}
                <td className="py-3 px-3 text-zinc-300">
                  {user.coaching_sessions}
                </td>

                {/* Status */}
                <td className="py-3 px-3">
                  <StatusBadge status={user.status} />
                </td>
              </tr>

              {/* Expanded details row */}
              {expandedRow === user.user_id && (
                <tr key={`${user.user_id}-details`} className="bg-surface-3/50">
                  <td colSpan={7} className="py-3 px-3">
                    <div className="flex gap-8 text-caption">
                      <div>
                        <span className="text-zinc-500">Last Login: </span>
                        <span className="text-zinc-300" title={user.last_login ? new Date(user.last_login).toISOString() : ''}>
                          {formatDate(user.last_login)}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Last Session: </span>
                        <span className="text-zinc-300">
                          {user.session_duration_last ? `${user.session_duration_last} min` : '—'}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Member Since: </span>
                        <span className="text-zinc-300">
                          {user.registered_at
                            ? `${getMemberSinceDays(user.registered_at)} days`
                            : '—'}
                        </span>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// =============================================================================
// CSV EXPORT
// =============================================================================

function exportToCsv(users) {
  const headers = [
    'Name',
    'Email',
    'Experience Level',
    'Pursuits Created',
    'Highest Phase',
    'Artifacts',
    'Coaching Sessions',
    'Last Login',
    'Session Duration (min)',
    'Status',
    'Member Since (days)',
  ];

  const getMemberSinceDays = (timestamp) => {
    if (!timestamp) return '';
    return Math.floor((Date.now() - new Date(timestamp).getTime()) / 86400000);
  };

  const rows = users.map((u) => [
    u.display_name || '',
    u.email || '',
    u.experience_level || '',
    u.pursuits_created,
    u.highest_phase_reached || '',
    u.artifacts_count,
    u.coaching_sessions,
    u.last_login ? new Date(u.last_login).toISOString() : '',
    u.session_duration_last || '',
    u.status,
    getMemberSinceDays(u.registered_at),
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      row.map((cell) =>
        typeof cell === 'string' && (cell.includes(',') || cell.includes('"'))
          ? `"${cell.replace(/"/g, '""')}"`
          : cell
      ).join(',')
    ),
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const date = new Date().toISOString().split('T')[0];
  link.href = url;
  link.download = `inde_innovator_vitals_${date}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function InnovatorVitalsTab() {
  // Filters
  const [statusFilter, setStatusFilter] = useState('All');
  const [experienceFilter, setExperienceFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Sorting
  const [sortConfig, setSortConfig] = useState({
    key: 'last_login',
    direction: 'desc',
  });

  // Data fetching with auto-refresh
  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['innovator-vitals'],
    queryFn: systemApi.getInnovatorVitals,
    refetchInterval: 120000, // 2 minutes
    staleTime: 60000,
  });

  // Filter and sort users
  const filteredUsers = useMemo(() => {
    if (!data?.users) return [];

    let result = [...data.users];

    // Status filter
    if (statusFilter !== 'All') {
      result = result.filter((u) => u.status === statusFilter);
    }

    // Experience filter
    if (experienceFilter !== 'All') {
      result = result.filter((u) => u.experience_level === experienceFilter);
    }

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (u) =>
          (u.display_name || '').toLowerCase().includes(query) ||
          (u.email || '').toLowerCase().includes(query)
      );
    }

    // Sort
    result.sort((a, b) => {
      let aVal = a[sortConfig.key];
      let bVal = b[sortConfig.key];

      // Handle null/undefined
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      // Handle dates
      if (sortConfig.key === 'last_login' || sortConfig.key === 'registered_at') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      }

      // Handle strings
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = (bVal || '').toLowerCase();
      }

      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [data?.users, statusFilter, experienceFilter, searchQuery, sortConfig]);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  const handleExport = () => {
    exportToCsv(filteredUsers);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-5 h-5 animate-spin text-zinc-500" />
        <span className="ml-2 text-zinc-500">Loading innovator vitals...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>Failed to load innovator vitals</span>
        </div>
        <p className="text-caption text-red-400/80 mt-1">
          {error.response?.data?.detail || error.message}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Warnings */}
      {data?.warnings?.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
          <div className="flex items-center gap-2 text-amber-400 text-body-sm">
            <AlertTriangle className="w-4 h-4" />
            <span>Some data may be incomplete:</span>
          </div>
          <ul className="text-caption text-amber-400/80 mt-1 ml-6 list-disc">
            {data.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary Bar */}
      <SummaryBar
        summary={data?.summary}
        generatedAt={data?.generated_at}
        onRefresh={refetch}
        isRefreshing={isFetching}
      />

      {/* Filter Controls */}
      <FilterControls
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        experienceFilter={experienceFilter}
        setExperienceFilter={setExperienceFilter}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onExport={handleExport}
      />

      {/* Results count */}
      <p className="text-caption text-zinc-500">
        Showing {filteredUsers.length} of {data?.users?.length || 0} innovators
      </p>

      {/* Vitals Table */}
      <VitalsTable
        users={filteredUsers}
        sortConfig={sortConfig}
        onSort={handleSort}
      />
    </div>
  );
}
