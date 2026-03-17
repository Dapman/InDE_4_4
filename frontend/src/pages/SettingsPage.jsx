import { useState, useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';
import { useUIStore } from '../stores/uiStore';
import { useAuth } from '../hooks/useAuth';
import { systemApi } from '../api/system';
import {
  User,
  Bell,
  Palette,
  Shield,
  Globe,
  Keyboard,
  Moon,
  Sun,
  Monitor,
  ChevronRight,
  Save,
  LogOut,
  Key,
  AlertTriangle,
  CheckCircle,
  Clock,
  Users,
  RefreshCw,
  Server,
  Cpu,
  Cloud,
  Wifi,
  WifiOff,
  Activity,
  Zap,
  DollarSign,
} from 'lucide-react';
import { cn } from '../lib/utils';

// v3.12: Account Trust components
import SessionManagement from '../components/settings/SessionManagement';
import PasswordChange from '../components/settings/PasswordChange';
import AccountDeletion from '../components/settings/AccountDeletion';

// =============================================================================
// SETTINGS SECTION
// =============================================================================

function SettingsSection({ title, description, children }) {
  return (
    <div className="bg-surface-2 border border-surface-border rounded-lg p-6 mb-6">
      <h2 className="text-body-md font-medium text-zinc-200 mb-1">{title}</h2>
      {description && (
        <p className="text-caption text-zinc-500 mb-4">{description}</p>
      )}
      <div className="space-y-4">{children}</div>
    </div>
  );
}

// =============================================================================
// SETTINGS ROW
// =============================================================================

function SettingsRow({ label, description, children }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex-1">
        <span className="text-body-sm text-zinc-300">{label}</span>
        {description && (
          <p className="text-caption text-zinc-600">{description}</p>
        )}
      </div>
      <div className="flex-shrink-0 ml-4">{children}</div>
    </div>
  );
}

// =============================================================================
// TOGGLE SWITCH
// =============================================================================

function Toggle({ checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={cn(
        'relative w-11 h-6 rounded-full transition-colors',
        checked ? 'bg-inde-500' : 'bg-surface-4'
      )}
    >
      <span
        className={cn(
          'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1'
        )}
      />
    </button>
  );
}

// =============================================================================
// SELECT DROPDOWN
// =============================================================================

function Select({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="px-3 py-1.5 text-body-sm bg-surface-3 border border-surface-border rounded-lg text-zinc-300 focus:outline-none focus:ring-2 focus:ring-inde-500/50"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

// =============================================================================
// MAIN SETTINGS PAGE
// =============================================================================

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const { logout } = useAuth();
  const theme = useUIStore((s) => s.theme);
  const setTheme = useUIStore((s) => s.setTheme);
  const complexityTier = useUIStore((s) => s.complexityTier);
  const setComplexityTier = useUIStore((s) => s.setComplexityTier);
  const complexityAutoDetect = useUIStore((s) => s.complexityAutoDetect);
  const setComplexityAutoDetect = useUIStore((s) => s.setComplexityAutoDetect);

  // Local state for settings
  const [notifications, setNotifications] = useState({
    coaching: true,
    health: true,
    ikf: false,
    digest: true,
  });

  const [ikfSettings, setIkfSettings] = useState({
    sharingLevel: 'moderate',
    autoPrepare: true,
  });

  // License status state
  const [licenseStatus, setLicenseStatus] = useState(null);
  const [licenseLoading, setLicenseLoading] = useState(true);

  // v3.9: Provider status state (admin only)
  const [providerStatus, setProviderStatus] = useState(null);
  const [providerLoading, setProviderLoading] = useState(true);

  // v3.9: AI Provider preference state (all users)
  const [llmPreference, setLlmPreference] = useState('auto');
  const [userProviders, setUserProviders] = useState(null);
  const [userProvidersLoading, setUserProvidersLoading] = useState(true);
  const [llmSaving, setLlmSaving] = useState(false);

  useEffect(() => {
    fetchLicenseStatus();
    fetchUserProviders();
    if (user?.role === 'admin') {
      fetchProviderStatus();
    }
  }, [user?.role]);

  const fetchLicenseStatus = async () => {
    setLicenseLoading(true);
    try {
      const response = await fetch('/api/system/license');
      if (response.ok) {
        const data = await response.json();
        setLicenseStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch license status:', err);
    } finally {
      setLicenseLoading(false);
    }
  };

  // v3.9: Fetch LLM provider status (admin)
  const fetchProviderStatus = async () => {
    setProviderLoading(true);
    try {
      const response = await fetch('/api/llm/providers');
      if (response.ok) {
        const data = await response.json();
        setProviderStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch provider status:', err);
    } finally {
      setProviderLoading(false);
    }
  };

  // v3.9: Fetch user's LLM provider options and preference
  const fetchUserProviders = async () => {
    setUserProvidersLoading(true);
    try {
      const data = await systemApi.getUserProviders();
      setUserProviders(data);
      setLlmPreference(data.user_preference || 'auto');
    } catch (err) {
      console.error('Failed to fetch user providers:', err);
    } finally {
      setUserProvidersLoading(false);
    }
  };

  // v3.9: Handle LLM preference change
  const handleLlmPreferenceChange = async (preference) => {
    setLlmSaving(true);
    const previousPref = llmPreference;
    setLlmPreference(preference);

    try {
      await systemApi.updateLlmPreference(preference);
      // Refresh to get updated active provider
      await fetchUserProviders();
    } catch (err) {
      console.error('Failed to save LLM preference:', err);
      setLlmPreference(previousPref); // Revert on error
    } finally {
      setLlmSaving(false);
    }
  };

  // v3.9: Get provider tier badge color
  const getTierColor = (tier) => {
    switch (tier?.toLowerCase()) {
      case 'premium':
        return 'text-inde-400 bg-inde-500/10 border-inde-500/20';
      case 'standard':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
      case 'basic':
        return 'text-orange-400 bg-orange-500/10 border-orange-500/20';
      default:
        return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/20';
    }
  };

  // v3.9: Get provider icon
  const getProviderIcon = (name) => {
    switch (name?.toLowerCase()) {
      case 'anthropic':
        return <Cloud className="h-4 w-4" />;
      case 'ollama':
        return <Cpu className="h-4 w-4" />;
      default:
        return <Server className="h-4 w-4" />;
    }
  };

  const getLicenseStatusColor = (state) => {
    switch (state) {
      case 'ACTIVE':
        return 'text-green-400';
      case 'GRACE_QUIET':
      case 'GRACE_VISIBLE':
        return 'text-yellow-400';
      case 'GRACE_URGENT':
        return 'text-orange-400';
      case 'EXPIRED':
        return 'text-red-400';
      default:
        return 'text-zinc-400';
    }
  };

  const getLicenseIcon = (state) => {
    switch (state) {
      case 'ACTIVE':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'GRACE_QUIET':
      case 'GRACE_VISIBLE':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'GRACE_URGENT':
      case 'EXPIRED':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      default:
        return <Key className="h-5 w-5 text-zinc-400" />;
    }
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  return (
    <div className="h-full overflow-y-auto bg-surface-1">
      <div className="max-w-3xl mx-auto px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-zinc-100 mb-1">Settings</h1>
          <p className="text-body-sm text-zinc-500">
            Manage your profile, preferences, and InDE configuration
          </p>
        </div>

        {/* License Status Section (Admin Only) */}
        {user?.role === 'admin' && (
          <SettingsSection
            title="License Status"
            description="Your InDE license information and entitlements"
          >
            {licenseLoading ? (
              <div className="flex items-center gap-2 text-zinc-400">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>Loading license info...</span>
              </div>
            ) : licenseStatus ? (
              <div className="space-y-4">
                {/* License State Banner */}
                <div className={cn(
                  'flex items-center gap-3 p-4 rounded-lg',
                  licenseStatus.grace_period?.state === 'ACTIVE' ? 'bg-green-500/10 border border-green-500/20' :
                  licenseStatus.grace_period?.state?.includes('GRACE') ? 'bg-yellow-500/10 border border-yellow-500/20' :
                  'bg-red-500/10 border border-red-500/20'
                )}>
                  {getLicenseIcon(licenseStatus.grace_period?.state)}
                  <div className="flex-1">
                    <span className={cn('font-medium', getLicenseStatusColor(licenseStatus.grace_period?.state))}>
                      {licenseStatus.grace_period?.state === 'ACTIVE' ? 'License Active' :
                       licenseStatus.grace_period?.state?.includes('GRACE') ? 'Grace Period Active' :
                       'License Expired'}
                    </span>
                    {licenseStatus.grace_period?.days_remaining !== undefined && licenseStatus.grace_period?.days_remaining < 30 && (
                      <p className="text-caption text-zinc-500 mt-0.5">
                        {licenseStatus.grace_period.days_remaining} days remaining
                      </p>
                    )}
                  </div>
                  <button
                    onClick={fetchLicenseStatus}
                    className="p-2 hover:bg-surface-3 rounded-lg transition-colors"
                    title="Refresh license status"
                  >
                    <RefreshCw className="h-4 w-4 text-zinc-400" />
                  </button>
                </div>

                {/* License Details */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-surface-3 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Key className="h-4 w-4 text-zinc-500" />
                      <span className="text-caption text-zinc-500">License Tier</span>
                    </div>
                    <span className="text-body-sm text-zinc-200 font-medium capitalize">
                      {licenseStatus.entitlements?.tier || 'Professional'}
                    </span>
                  </div>

                  <div className="p-3 bg-surface-3 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <Users className="h-4 w-4 text-zinc-500" />
                      <span className="text-caption text-zinc-500">Seats</span>
                    </div>
                    <span className="text-body-sm text-zinc-200 font-medium">
                      {licenseStatus.seats?.active || 0} / {licenseStatus.entitlements?.seat_limit || '∞'}
                    </span>
                  </div>
                </div>

                {/* Features */}
                {licenseStatus.entitlements?.features && (
                  <div>
                    <span className="text-caption text-zinc-500 block mb-2">Enabled Features</span>
                    <div className="flex flex-wrap gap-2">
                      {licenseStatus.entitlements.features.map((feature) => (
                        <span
                          key={feature}
                          className="px-2 py-1 bg-inde-500/10 border border-inde-500/20 rounded text-caption text-inde-400"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Grace Period Warning */}
                {licenseStatus.grace_period?.state?.includes('GRACE') && (
                  <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5" />
                      <div>
                        <p className="text-body-sm text-yellow-300">
                          Your license requires attention
                        </p>
                        <p className="text-caption text-zinc-400 mt-1">
                          Contact your administrator or visit license.indeverse.com to renew.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 p-4 bg-surface-3 rounded-lg">
                <Key className="h-5 w-5 text-zinc-400" />
                <span className="text-body-sm text-zinc-400">
                  License information unavailable
                </span>
              </div>
            )}
          </SettingsSection>
        )}

        {/* v3.9: LLM Provider Status (Admin Only) */}
        {user?.role === 'admin' && (
          <SettingsSection
            title="LLM Provider Status"
            description="AI provider chain and failover configuration"
          >
            {providerLoading ? (
              <div className="flex items-center gap-2 text-zinc-400">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>Loading provider status...</span>
              </div>
            ) : providerStatus ? (
              <div className="space-y-4">
                {/* Provider Chain Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-inde-400" />
                    <span className="text-body-sm text-zinc-300">Provider Chain</span>
                  </div>
                  <button
                    onClick={fetchProviderStatus}
                    className="p-2 hover:bg-surface-3 rounded-lg transition-colors"
                    title="Refresh provider status"
                  >
                    <RefreshCw className="h-4 w-4 text-zinc-400" />
                  </button>
                </div>

                {/* Provider List */}
                <div className="space-y-2">
                  {providerStatus.providers?.map((provider, index) => (
                    <div
                      key={provider.name}
                      className={cn(
                        'flex items-center justify-between p-3 rounded-lg border',
                        provider.available
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-surface-3 border-surface-border'
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'p-2 rounded-lg',
                          provider.available ? 'bg-green-500/10' : 'bg-surface-4'
                        )}>
                          {getProviderIcon(provider.name)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-body-sm font-medium text-zinc-200 capitalize">
                              {provider.name}
                            </span>
                            {index === 0 && (
                              <span className="text-caption text-inde-400">(Primary)</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            {provider.available ? (
                              <div className="flex items-center gap-1 text-green-400">
                                <Wifi className="h-3 w-3" />
                                <span className="text-caption">Connected</span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1 text-zinc-500">
                                <WifiOff className="h-3 w-3" />
                                <span className="text-caption">Unavailable</span>
                              </div>
                            )}
                            {provider.current_model && (
                              <span className="text-caption text-zinc-500">
                                • {provider.current_model}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          'px-2 py-0.5 rounded text-caption border font-medium capitalize',
                          getTierColor(provider.quality_tier)
                        )}>
                          {provider.quality_tier || 'unknown'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Failover History (if any recent events) */}
                {providerStatus.failover_history?.length > 0 && (
                  <div className="pt-4 border-t border-surface-border">
                    <span className="text-caption text-zinc-500 block mb-2">Recent Failovers</span>
                    <div className="space-y-1">
                      {providerStatus.failover_history.slice(0, 3).map((event, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-caption">
                          <AlertTriangle className="h-3 w-3 text-yellow-500" />
                          <span className="text-zinc-400">
                            {event.from_provider} → {event.to_provider}
                          </span>
                          <span className="text-zinc-600">
                            {new Date(event.timestamp).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Air-Gapped Mode Indicator */}
                {providerStatus.chain?.length === 1 && providerStatus.chain[0] === 'ollama' && (
                  <div className="p-3 bg-inde-500/10 border border-inde-500/20 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-inde-400" />
                      <span className="text-body-sm text-inde-300">Air-Gapped Mode</span>
                    </div>
                    <p className="text-caption text-zinc-400 mt-1">
                      Running with local Ollama model. No internet connection required.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 p-4 bg-surface-3 rounded-lg">
                <Server className="h-5 w-5 text-zinc-400" />
                <span className="text-body-sm text-zinc-400">
                  Provider information unavailable
                </span>
              </div>
            )}
          </SettingsSection>
        )}

        {/* Profile Section */}
        <SettingsSection title="Profile" description="Your account information">
          <div className="flex items-center gap-4 p-4 bg-surface-3 rounded-lg">
            <div className="w-16 h-16 rounded-full bg-inde-500/20 flex items-center justify-center">
              <User className="h-8 w-8 text-inde-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-body-md font-medium text-zinc-200">
                {user?.name || user?.email || 'Innovator'}
              </h3>
              <p className="text-caption text-zinc-500">{user?.email || 'demo@inde.ai'}</p>
              <p className="text-caption text-zinc-600 mt-1">
                {user?.maturity_level || 'COMPETENT'} Innovator
              </p>
            </div>
          </div>
        </SettingsSection>

        {/* Appearance Section */}
        <SettingsSection
          title="Appearance"
          description="Customize how InDE looks and feels"
        >
          <SettingsRow label="Theme" description="Choose your preferred color scheme">
            <div className="flex items-center gap-1 bg-surface-3 rounded-lg p-1">
              <button
                onClick={() => setTheme('light')}
                className={cn(
                  'p-2 rounded-md transition-colors',
                  theme === 'light' ? 'bg-surface-4 text-zinc-200' : 'text-zinc-500'
                )}
              >
                <Sun className="h-4 w-4" />
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={cn(
                  'p-2 rounded-md transition-colors',
                  theme === 'dark' ? 'bg-surface-4 text-zinc-200' : 'text-zinc-500'
                )}
              >
                <Moon className="h-4 w-4" />
              </button>
            </div>
          </SettingsRow>

          <SettingsRow
            label="UI Complexity"
            description="Control how much guidance the interface shows"
          >
            <Select
              value={complexityAutoDetect ? 'auto' : complexityTier}
              onChange={(v) => {
                if (v === 'auto') {
                  setComplexityAutoDetect(true);
                } else {
                  setComplexityAutoDetect(false);
                  setComplexityTier(v);
                }
              }}
              options={[
                { value: 'auto', label: 'Auto-detect' },
                { value: 'guided', label: 'Guided (More Help)' },
                { value: 'standard', label: 'Standard' },
                { value: 'streamlined', label: 'Streamlined' },
                { value: 'minimal', label: 'Minimal (Expert)' },
              ]}
            />
          </SettingsRow>
        </SettingsSection>

        {/* v3.9: AI Provider Preference Section */}
        <SettingsSection
          title="AI Provider"
          description="Choose how InDE's coaching intelligence is powered"
        >
          {userProvidersLoading ? (
            <div className="flex items-center gap-2 text-zinc-400">
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span>Loading provider options...</span>
            </div>
          ) : userProviders ? (
            <div className="space-y-3">
              {/* Provider Options */}
              {[
                {
                  id: 'auto',
                  icon: <RefreshCw className="h-5 w-5" />,
                  badge: null,
                },
                {
                  id: 'cloud',
                  icon: <Cloud className="h-5 w-5" />,
                  badge: { text: 'Best Quality', color: 'inde' },
                },
                {
                  id: 'local',
                  icon: <Cpu className="h-5 w-5" />,
                  badge: { text: 'Free', color: 'green' },
                },
              ].map((opt) => {
                const provider = userProviders.providers?.[opt.id];
                const isSelected = llmPreference === opt.id;
                const isAvailable = provider?.available !== false;
                // Users can select any option - system will fallback gracefully
                const isDisabled = llmSaving;

                return (
                  <button
                    key={opt.id}
                    onClick={() => !llmSaving && handleLlmPreferenceChange(opt.id)}
                    disabled={isDisabled}
                    className={cn(
                      'w-full p-4 rounded-lg border transition-all text-left',
                      isSelected
                        ? 'border-inde-500 bg-inde-500/10'
                        : 'border-surface-border hover:border-surface-border-hover',
                      isDisabled && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={cn(
                          'p-2 rounded-lg',
                          isSelected
                            ? 'bg-inde-500/20 text-inde-400'
                            : 'bg-surface-3 text-zinc-400'
                        )}
                      >
                        {opt.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-body-sm font-medium text-zinc-200">
                            {provider?.name || opt.id}
                          </span>
                          {opt.badge && (
                            <span
                              className={cn(
                                'px-1.5 py-0.5 text-caption rounded',
                                opt.badge.color === 'inde'
                                  ? 'bg-inde-500/20 text-inde-400'
                                  : 'bg-green-500/20 text-green-400'
                              )}
                            >
                              {opt.badge.text}
                            </span>
                          )}
                          {!isAvailable && opt.id !== 'auto' && (
                            <span className="px-1.5 py-0.5 text-caption rounded bg-yellow-500/20 text-yellow-400">
                              Currently Offline
                            </span>
                          )}
                        </div>
                        <p className="text-caption text-zinc-500 mt-0.5">
                          {provider?.description}
                        </p>
                        <div className="flex gap-4 mt-2">
                          <span className="text-caption text-zinc-600">
                            Quality:{' '}
                            <span className="text-zinc-400 capitalize">
                              {provider?.quality_tier || 'unknown'}
                            </span>
                          </span>
                          <span className="text-caption text-zinc-600">
                            Cost:{' '}
                            <span className="text-zinc-400">{provider?.cost}</span>
                          </span>
                        </div>
                      </div>
                      {isSelected && (
                        <CheckCircle className="h-5 w-5 text-inde-500 flex-shrink-0" />
                      )}
                      {llmSaving && isSelected && (
                        <RefreshCw className="h-4 w-4 text-inde-400 animate-spin flex-shrink-0" />
                      )}
                    </div>
                  </button>
                );
              })}

              {/* Active Provider Info */}
              {userProviders.active_provider && (
                <div className="flex items-center gap-2 pt-2 text-caption text-zinc-500">
                  <Zap className="h-3 w-3 text-inde-400" />
                  <span>
                    Currently using:{' '}
                    <span className="text-zinc-300 capitalize">
                      {userProviders.active_provider === 'cloud'
                        ? 'Cloud (Claude)'
                        : userProviders.active_provider === 'local'
                        ? 'Local (Ollama)'
                        : userProviders.active_provider}
                    </span>
                  </span>
                </div>
              )}

              {/* Fallback Warning */}
              {userProviders.fallback_warning && (
                <div className="flex items-start gap-2 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg mt-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-body-sm text-yellow-300">
                      Preferred provider unavailable
                    </p>
                    <p className="text-caption text-zinc-400 mt-0.5">
                      Using fallback provider. Your preference will be used when available.
                    </p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 p-4 bg-surface-3 rounded-lg">
              <Server className="h-5 w-5 text-zinc-400" />
              <span className="text-body-sm text-zinc-400">
                Provider information unavailable
              </span>
            </div>
          )}
        </SettingsSection>

        {/* Notifications Section */}
        <SettingsSection
          title="Notifications"
          description="Control when InDE notifies you"
        >
          <SettingsRow
            label="Coaching Insights"
            description="Get notified about coaching suggestions"
          >
            <Toggle
              checked={notifications.coaching}
              onChange={(v) => setNotifications({ ...notifications, coaching: v })}
            />
          </SettingsRow>

          <SettingsRow
            label="Health Alerts"
            description="Alerts when pursuit health needs attention"
          >
            <Toggle
              checked={notifications.health}
              onChange={(v) => setNotifications({ ...notifications, health: v })}
            />
          </SettingsRow>

          <SettingsRow
            label="IKF Updates"
            description="Notifications about federation patterns"
          >
            <Toggle
              checked={notifications.ikf}
              onChange={(v) => setNotifications({ ...notifications, ikf: v })}
            />
          </SettingsRow>

          <SettingsRow
            label="Weekly Digest"
            description="Summary of your innovation progress"
          >
            <Toggle
              checked={notifications.digest}
              onChange={(v) => setNotifications({ ...notifications, digest: v })}
            />
          </SettingsRow>
        </SettingsSection>

        {/* IKF Settings */}
        <SettingsSection
          title="Knowledge Federation"
          description="Control how you participate in the innovation network"
        >
          <SettingsRow
            label="Sharing Level"
            description="How much you share with the federation"
          >
            <Select
              value={ikfSettings.sharingLevel}
              onChange={(v) => setIkfSettings({ ...ikfSettings, sharingLevel: v })}
              options={[
                { value: 'aggressive', label: 'Aggressive (Share All)' },
                { value: 'moderate', label: 'Moderate (Recommended)' },
                { value: 'minimal', label: 'Minimal' },
                { value: 'none', label: 'None (Opt Out)' },
              ]}
            />
          </SettingsRow>

          <SettingsRow
            label="Auto-Prepare Contributions"
            description="Automatically prepare patterns for review"
          >
            <Toggle
              checked={ikfSettings.autoPrepare}
              onChange={(v) => setIkfSettings({ ...ikfSettings, autoPrepare: v })}
            />
          </SettingsRow>
        </SettingsSection>

        {/* Keyboard Shortcuts */}
        <SettingsSection
          title="Keyboard Shortcuts"
          description="Quick reference for keyboard navigation"
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center justify-between p-2 bg-surface-3 rounded">
              <span className="text-caption text-zinc-400">Command Palette</span>
              <kbd className="px-2 py-0.5 bg-surface-4 rounded text-caption text-zinc-300 font-mono">
                Cmd+K
              </kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-surface-3 rounded">
              <span className="text-caption text-zinc-400">New Pursuit</span>
              <kbd className="px-2 py-0.5 bg-surface-4 rounded text-caption text-zinc-300 font-mono">
                Cmd+N
              </kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-surface-3 rounded">
              <span className="text-caption text-zinc-400">Toggle Sidebar</span>
              <kbd className="px-2 py-0.5 bg-surface-4 rounded text-caption text-zinc-300 font-mono">
                Cmd+B
              </kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-surface-3 rounded">
              <span className="text-caption text-zinc-400">Focus Chat</span>
              <kbd className="px-2 py-0.5 bg-surface-4 rounded text-caption text-zinc-300 font-mono">
                Cmd+/
              </kbd>
            </div>
          </div>
        </SettingsSection>

        {/* v3.12: Security & Sessions */}
        <SettingsSection
          title="Security"
          description="Manage your password and active sessions"
        >
          {/* Password Change */}
          <div className="mb-6">
            <h3 className="text-body-sm font-medium text-zinc-300 mb-3">Change Password</h3>
            <PasswordChange />
          </div>

          {/* Session Management */}
          <div className="pt-4 border-t border-surface-border/50">
            <h3 className="text-body-sm font-medium text-zinc-300 mb-3">Active Sessions</h3>
            <SessionManagement />
          </div>
        </SettingsSection>

        {/* v3.12: Account Deletion */}
        <SettingsSection
          title="Account"
          description="Manage your account settings"
        >
          <AccountDeletion />
        </SettingsSection>

        {/* Account Actions */}
        <div className="mt-8 pt-6 border-t border-surface-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 text-body-sm text-health-atrisk hover:bg-health-atrisk/10 rounded-lg transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>

        {/* About Section */}
        <SettingsSection
          title="About"
          description="Product information and version details"
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-surface-border/50">
              <span className="text-body-sm text-zinc-400">Product</span>
              <span className="text-body-sm text-zinc-200">InDE - Innovation Development Environment</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-surface-border/50">
              <span className="text-body-sm text-zinc-400">Version</span>
              <span className="text-body-sm text-zinc-200 font-mono">4.4.1</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-surface-border/50">
              <span className="text-body-sm text-zinc-400">Codename</span>
              <span className="text-body-sm text-zinc-200 font-mono">Innovation Vitals</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-surface-border/50">
              <span className="text-body-sm text-zinc-400">Build</span>
              <span className="text-body-sm text-zinc-200 font-mono">v4.4.1</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-body-sm text-zinc-400">Company</span>
              <span className="text-body-sm text-zinc-200">InDEVerse, Inc.</span>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-surface-border/50 text-center">
            <p className="text-caption text-zinc-600">
              © {new Date().getFullYear()} InDEVerse, Inc. All rights reserved.
            </p>
          </div>
        </SettingsSection>
      </div>
    </div>
  );
}
