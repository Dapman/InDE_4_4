import { useNavigate } from 'react-router-dom';
import { useUIStore } from '../../stores/uiStore';
import { useAuthStore } from '../../stores/authStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { Avatar, AvatarFallback } from '../ui/avatar';
import {
  Search,
  Bell,
  Sun,
  Moon,
  ChevronDown,
  Plus,
  Settings,
  LogOut,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function TopBar() {
  const navigate = useNavigate();
  const { theme, toggleTheme, setCommandPaletteOpen, unreadCount } = useUIStore();
  const { user, getUserInitials } = useAuthStore();
  const { pursuitList, activePursuitId, setActivePursuit } = usePursuitStore();
  const { logout } = useAuth();

  const activePursuit = pursuitList.find((p) => p.id === activePursuitId);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="h-topbar flex items-center px-4 border-b border-surface-border bg-surface-2/80 backdrop-blur-sm">
      {/* Logo */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 mr-4 hover:opacity-80 transition-opacity"
      >
        <div className="w-7 h-7 rounded-lg inde-gradient flex items-center justify-center">
          <span className="text-white font-bold text-sm">I</span>
        </div>
        <span className="font-display font-semibold text-lg inde-gradient-text hidden sm:block">
          InDE
        </span>
      </button>

      {/* Pursuit Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="h-8 px-3 text-body-sm text-zinc-300 hover:text-white hover:bg-surface-4"
          >
            <span className="max-w-[200px] truncate">
              {activePursuit?.name || 'Select Pursuit'}
            </span>
            <ChevronDown className="ml-2 h-4 w-4 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64 bg-surface-3 border-surface-border text-zinc-200">
          {pursuitList.filter((p) => p.state === 'ACTIVE').map((pursuit) => (
            <DropdownMenuItem
              key={pursuit.id}
              onClick={() => {
                setActivePursuit(pursuit.id);
                navigate(`/pursuit/${pursuit.id}`);
              }}
              className={cn(
                'cursor-pointer',
                pursuit.id === activePursuitId && 'bg-surface-4'
              )}
            >
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    'w-2 h-2 rounded-full',
                    pursuit.phase === 'VISION' && 'bg-phase-vision',
                    pursuit.phase === 'PITCH' && 'bg-phase-pitch',
                    pursuit.phase === 'DE_RISK' && 'bg-phase-derisk',
                    pursuit.phase === 'BUILD' && 'bg-phase-build',
                    pursuit.phase === 'DEPLOY' && 'bg-phase-deploy'
                  )}
                />
                <span className="truncate">{pursuit.name}</span>
              </div>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => {
              // TODO: Open new pursuit modal
            }}
            className="cursor-pointer text-inde-400"
          >
            <Plus className="mr-2 h-4 w-4" />
            New Pursuit
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Command Trigger */}
      <Button
        variant="ghost"
        onClick={() => setCommandPaletteOpen(true)}
        className="h-8 px-3 text-zinc-500 hover:text-zinc-300 hover:bg-surface-4 hidden sm:flex"
      >
        <Search className="h-4 w-4 mr-2" />
        <span className="text-body-sm">Search</span>
        <kbd className="ml-2 px-1.5 py-0.5 text-[10px] font-mono bg-surface-4 rounded border border-surface-border">
          ⌘K
        </kbd>
      </Button>

      {/* Mobile search */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setCommandPaletteOpen(true)}
        className="h-8 w-8 sm:hidden text-zinc-500 hover:text-zinc-300"
      >
        <Search className="h-4 w-4" />
      </Button>

      {/* Notifications */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 ml-1 text-zinc-500 hover:text-zinc-300 relative"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-inde-500 rounded-full text-[10px] font-bold flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </Button>

      {/* Theme Toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleTheme}
        className="h-8 w-8 ml-1 text-zinc-500 hover:text-zinc-300"
      >
        {theme === 'dark' ? (
          <Sun className="h-4 w-4" />
        ) : (
          <Moon className="h-4 w-4" />
        )}
      </Button>

      {/* User Menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="h-8 px-2 ml-2"
          >
            <Avatar className="h-6 w-6">
              <AvatarFallback className="bg-inde-600 text-white text-xs">
                {getUserInitials()}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48 bg-surface-3 border-surface-border text-zinc-200">
          <div className="px-2 py-1.5">
            <p className="text-body-sm font-medium">{user?.name || user?.email}</p>
            <p className="text-caption text-zinc-500">{user?.email}</p>
          </div>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate('/settings')} className="cursor-pointer">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-red-400">
            <LogOut className="mr-2 h-4 w-4" />
            Sign Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}

export default TopBar;
