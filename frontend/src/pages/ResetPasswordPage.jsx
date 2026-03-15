/**
 * ResetPasswordPage
 * Allows users to set a new password using a reset token.
 *
 * v3.12: Account Trust & Completeness
 */

import { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Lock, Eye, EyeOff, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { cn } from '../lib/utils';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Password requirements
  const passwordRequirements = [
    { met: password.length >= 8, text: 'At least 8 characters' },
    { met: /[A-Z]/.test(password), text: 'One uppercase letter' },
    { met: /[a-z]/.test(password), text: 'One lowercase letter' },
    { met: /[0-9]/.test(password), text: 'One number' },
  ];

  const isValid =
    password.length >= 8 &&
    password === confirmPassword;

  // Validate token on mount
  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setTokenValid(false);
        setValidating(false);
        return;
      }

      try {
        const response = await fetch('/api/account/validate-reset-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token })
        });

        if (response.ok) {
          const data = await response.json();
          setTokenValid(data.valid);
        } else {
          setTokenValid(false);
        }
      } catch (err) {
        console.error('Failed to validate token:', err);
        setTokenValid(false);
      } finally {
        setValidating(false);
      }
    };

    validateToken();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/account/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to reset password');
      }

      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (validating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-2 border-inde-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-zinc-400">Validating reset link...</p>
        </div>
      </div>
    );
  }

  // Invalid token state
  if (!tokenValid) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-display-lg inde-gradient-text mb-2">InDE</h1>
            <p className="text-body-md text-zinc-500">Password Reset</p>
          </div>

          <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
                <AlertCircle className="h-8 w-8 text-red-400" />
              </div>
              <h2 className="text-body-md font-medium text-zinc-200 mb-2">
                Invalid or Expired Link
              </h2>
              <p className="text-caption text-zinc-400 mb-6">
                This password reset link is invalid or has expired.
                Please request a new one.
              </p>

              <Link to="/forgot-password">
                <Button className="w-full bg-inde-600 hover:bg-inde-700 text-white">
                  Request New Link
                </Button>
              </Link>

              <div className="mt-4">
                <Link
                  to="/login"
                  className="text-body-sm text-inde-400 hover:text-inde-300"
                >
                  <ArrowLeft className="h-4 w-4 inline mr-1" />
                  Back to Login
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-display-lg inde-gradient-text mb-2">InDE</h1>
            <p className="text-body-md text-zinc-500">Password Reset</p>
          </div>

          <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mb-4">
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
              <h2 className="text-body-md font-medium text-zinc-200 mb-2">
                Password Reset Complete
              </h2>
              <p className="text-caption text-zinc-400 mb-6">
                Your password has been successfully reset. You can now log in
                with your new password.
              </p>

              <Link to="/login">
                <Button className="w-full bg-inde-600 hover:bg-inde-700 text-white">
                  Continue to Login
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Form state
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-display-lg inde-gradient-text mb-2">InDE</h1>
          <p className="text-body-md text-zinc-500">Set New Password</p>
        </div>

        <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
          <h2 className="text-body-md font-medium text-zinc-200 mb-2">
            Create a new password
          </h2>
          <p className="text-caption text-zinc-400 mb-6">
            Enter a new password for your account.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* New Password */}
            <div>
              <label htmlFor="password" className="block text-body-sm text-zinc-400 mb-1.5">
                New Password
              </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter new password"
                  required
                  className="bg-surface-3 border-surface-border-light pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Password requirements */}
              {password.length > 0 && (
                <div className="mt-2 space-y-1">
                  {passwordRequirements.map((req, i) => (
                    <div key={i} className="flex items-center gap-2">
                      {req.met ? (
                        <CheckCircle className="h-3 w-3 text-green-400" />
                      ) : (
                        <div className="h-3 w-3 rounded-full border border-zinc-600" />
                      )}
                      <span className={cn(
                        'text-caption',
                        req.met ? 'text-green-400' : 'text-zinc-500'
                      )}>
                        {req.text}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label htmlFor="confirmPassword" className="block text-body-sm text-zinc-400 mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirm ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  required
                  className={cn(
                    'bg-surface-3 border-surface-border-light pr-10',
                    confirmPassword.length > 0 && password !== confirmPassword && 'border-red-500'
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                >
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {confirmPassword.length > 0 && password !== confirmPassword && (
                <p className="text-caption text-red-400 mt-1">Passwords do not match</p>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <AlertCircle className="h-4 w-4 text-red-400" />
                <span className="text-sm text-red-400">{error}</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={!isValid || loading}
              className="w-full bg-inde-600 hover:bg-inde-700 text-white"
            >
              <Lock className="h-4 w-4 mr-2" />
              {loading ? 'Resetting...' : 'Reset Password'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <Link
              to="/login"
              className="text-body-sm text-inde-400 hover:text-inde-300"
            >
              <ArrowLeft className="h-4 w-4 inline mr-1" />
              Back to Login
            </Link>
          </div>
        </div>

        <p className="text-caption text-zinc-600 text-center mt-6">
          InDE v4.3.0
        </p>
      </div>
    </div>
  );
}
