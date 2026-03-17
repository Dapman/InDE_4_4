import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../api/auth';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { cn } from '../lib/utils';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, register, isLoading } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [showDemoInactivePopup, setShowDemoInactivePopup] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (mode === 'register') {
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters');
        return;
      }
      const result = await register(name, email, password);
      if (result.success) {
        navigate('/');
      } else {
        setError(result.error);
      }
    } else {
      const result = await login(email, password);
      if (result.success) {
        navigate('/');
      } else {
        setError(result.error);
      }
    }
  };

  // Demo login for development
  const handleDemoLogin = async () => {
    setError('');
    try {
      const response = await authApi.demoLogin();
      const { access_token } = response.data;

      // Store token first
      useAuthStore.getState().login({ email: 'demo@inde.dev' }, access_token);

      // Fetch full user profile
      try {
        const profileResponse = await authApi.getProfile();
        const userData = {
          id: profileResponse.data.user_id,
          email: profileResponse.data.email,
          name: profileResponse.data.name,
          experienceLevel: profileResponse.data.experience_level,
          maturityLevel: profileResponse.data.maturity_level,
        };
        useAuthStore.getState().login(userData, access_token);
      } catch (profileError) {
        console.warn('Could not fetch demo user profile:', profileError);
      }

      navigate('/');
    } catch (error) {
      // v4.4.1: Robust check for demo mode inactive
      // Check multiple ways the 403/DEMO_MODE_INACTIVE error could appear
      const status = error.response?.status;
      const errorDetail = error.response?.data?.detail;
      const errorCode = typeof errorDetail === 'object' ? errorDetail?.code : null;

      // Show demo inactive popup for any 403 on demo-login endpoint
      if (status === 403 || errorCode === 'DEMO_MODE_INACTIVE') {
        setShowDemoInactivePopup(true);
        return;  // Explicit return to prevent any further state changes
      }

      // Fallback error handling
      const errorMessage = typeof errorDetail === 'string'
        ? errorDetail
        : (errorDetail?.message || 'Demo login is currently unavailable. Please register or sign in.');
      setError(errorMessage);
    }
  };

  const switchMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setError('');
    setName('');
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-display-lg inde-gradient-text mb-2">InDE</h1>
          <p className="text-body-md text-zinc-500">
            Innovation Development Environment
          </p>
        </div>

        {/* Login/Register Card */}
        <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
          {/* Mode Toggle */}
          <div className="flex mb-6 bg-surface-3 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={cn(
                'flex-1 py-2 text-body-sm font-medium rounded-md transition-colors',
                mode === 'login'
                  ? 'bg-surface-4 text-zinc-200'
                  : 'text-zinc-500 hover:text-zinc-300'
              )}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={cn(
                'flex-1 py-2 text-body-sm font-medium rounded-md transition-colors',
                mode === 'register'
                  ? 'bg-surface-4 text-zinc-200'
                  : 'text-zinc-500 hover:text-zinc-300'
              )}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label htmlFor="name" className="block text-body-sm text-zinc-400 mb-1.5">
                  Name
                </label>
                <Input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  required
                  className="bg-surface-3 border-surface-border-light"
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-body-sm text-zinc-400 mb-1.5">
                Email
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="bg-surface-3 border-surface-border-light"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-body-sm text-zinc-400 mb-1.5">
                Password
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === 'register' ? 'Create a password' : 'Enter your password'}
                required
                className="bg-surface-3 border-surface-border-light"
              />
              {mode === 'register' && (
                <p className="text-caption text-zinc-400 mt-1.5">
                  Must be at least 8 characters
                </p>
              )}
              {mode === 'login' && (
                <div className="text-right mt-1.5">
                  <Link
                    to="/forgot-password"
                    className="text-caption text-inde-400 hover:text-inde-300"
                  >
                    Forgot password?
                  </Link>
                </div>
              )}
            </div>

            {mode === 'register' && (
              <div>
                <label htmlFor="confirmPassword" className="block text-body-sm text-zinc-400 mb-1.5">
                  Confirm Password
                </label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                  required
                  className="bg-surface-3 border-surface-border-light"
                />
              </div>
            )}

            {error && (
              <div className="text-body-sm text-red-400 bg-red-500/10 px-3 py-2 rounded-md">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full bg-inde-600 hover:bg-inde-700 text-white"
            >
              {isLoading
                ? (mode === 'register' ? 'Creating account...' : 'Signing in...')
                : (mode === 'register' ? 'Create Account' : 'Sign In')}
            </Button>
          </form>

          {/* Switch mode link */}
          <p className="text-center text-body-sm text-zinc-500 mt-4">
            {mode === 'login' ? (
              <>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={switchMode}
                  className="text-inde-400 hover:text-inde-300 font-medium"
                >
                  Register
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={switchMode}
                  className="text-inde-400 hover:text-inde-300 font-medium"
                >
                  Sign In
                </button>
              </>
            )}
          </p>

          <div className="mt-6 pt-6 border-t border-surface-border">
            <Button
              type="button"
              variant="outline"
              onClick={handleDemoLogin}
              className="w-full border-surface-border-light hover:bg-surface-4"
            >
              Try Demo Account
            </Button>
          </div>
        </div>

        {/* Version */}
        <p className="text-caption text-zinc-600 text-center mt-6">
          InDE v4.4.1
        </p>
      </div>

      {/* v4.2: Demo Mode Inactive Popup */}
      {showDemoInactivePopup && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-surface-2 rounded-panel p-6 max-w-md w-full shadow-2xl border border-surface-border">
            <div className="text-center mb-4">
              <div className="w-12 h-12 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-heading-md text-zinc-100 mb-2">Demo Account Unavailable</h3>
              <p className="text-body-sm text-zinc-400">
                The Demo User account is currently not active. To explore InDE and start developing your innovation ideas, please <strong className="text-zinc-300">register for a new account</strong> or use the <strong className="text-zinc-300">Sign In</strong> form to log in with your existing credentials.
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowDemoInactivePopup(false);
                  setMode('login');
                }}
                className="flex-1 border-surface-border-light"
              >
                Sign In
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setShowDemoInactivePopup(false);
                  setMode('register');
                }}
                className="flex-1 bg-inde-600 hover:bg-inde-700 text-white"
              >
                Register
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
