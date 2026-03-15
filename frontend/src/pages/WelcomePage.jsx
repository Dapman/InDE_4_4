import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useQuery } from '@tanstack/react-query';
import { pursuitsApi } from '../api/pursuits';
import {
  Sparkles,
  MessageSquare,
  Brain,
  Users,
  Lightbulb,
  Archive,
  ChevronRight,
} from 'lucide-react';

/**
 * WelcomePage - For users with zero active pursuits
 * Provides a warm welcome and clear path to start innovating
 */
export default function WelcomePage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const userName = useAuthStore((s) => s.getUserName());

  // Check for archived pursuits
  const { data: pursuits } = useQuery({
    queryKey: ['pursuits'],
    queryFn: async () => {
      const response = await pursuitsApi.list();
      return response.data?.pursuits || response.data || [];
    },
  });

  const archivedPursuits = pursuits?.filter(
    (p) => p.state === 'ARCHIVED' || p.state === 'COMPLETED' || p.status === 'archived'
  ) || [];

  const handleStartPursuit = () => {
    navigate('/pursuit/new');
  };

  const handleViewArchived = () => {
    navigate('/portfolio?filter=archived');
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-4xl mx-auto">
      {/* Welcome Header */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-inde-500/10 rounded-full mb-6">
          <Sparkles className="w-8 h-8 text-inde-400" />
        </div>
        <h1 className="text-display-lg font-semibold text-zinc-100 mb-3">
          Welcome{userName ? `, ${userName}` : ''}!
        </h1>
        <p className="text-body-lg text-zinc-400 max-w-lg mx-auto">
          You're ready to transform ideas into impact. InDE will guide you through
          every step of your innovation journey with AI-powered coaching.
        </p>
      </div>

      {/* Primary CTA */}
      <button
        onClick={handleStartPursuit}
        className="group flex items-center gap-3 px-8 py-4 bg-inde-500 hover:bg-inde-600 text-white rounded-xl font-medium text-body-lg transition-all hover:shadow-lg hover:shadow-inde-500/25 mb-12"
      >
        <Lightbulb className="w-6 h-6" />
        <span>Start Your First Innovation Pursuit</span>
        <ChevronRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
      </button>

      {/* Capability Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full mb-8">
        <CapabilityCard
          icon={MessageSquare}
          title="Coaching"
          description="Real-time AI coaching adapts to your innovation style"
          color="text-phase-vision"
          bgColor="bg-phase-vision/10"
        />
        <CapabilityCard
          icon={Sparkles}
          title="Methodology"
          description="Choose from proven frameworks or discover your own"
          color="text-inde-400"
          bgColor="bg-inde-500/10"
        />
        <CapabilityCard
          icon={Brain}
          title="Intelligence"
          description="Learn from patterns across the innovation network"
          color="text-phase-derisk"
          bgColor="bg-phase-derisk/10"
        />
        <CapabilityCard
          icon={Users}
          title="Collaboration"
          description="Work with your team and share knowledge globally"
          color="text-phase-pitch"
          bgColor="bg-phase-pitch/10"
        />
      </div>

      {/* Archived pursuits link */}
      {archivedPursuits.length > 0 && (
        <button
          onClick={handleViewArchived}
          className="flex items-center gap-2 text-body-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <Archive className="w-4 h-4" />
          <span>View {archivedPursuits.length} Archived Pursuit{archivedPursuits.length !== 1 ? 's' : ''}</span>
        </button>
      )}
    </div>
  );
}

function CapabilityCard({ icon: Icon, title, description, color, bgColor }) {
  return (
    <div className="bg-surface-4 border border-surface-border rounded-xl p-5">
      <div className={`inline-flex items-center justify-center w-10 h-10 ${bgColor} rounded-lg mb-3`}>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <h3 className="text-body-md font-medium text-zinc-200 mb-1">{title}</h3>
      <p className="text-caption text-zinc-500">{description}</p>
    </div>
  );
}
