/**
 * ForgotPasswordPage
 * Allows users to request a password reset email.
 *
 * v3.12: Account Trust & Completeness
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle, AlertCircle, AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [emailConfigured, setEmailConfigured] = useState(true);
  const [checkingStatus, setCheckingStatus] = useState(true);

  // Check if email is configured on this installation
  useEffect(() => {
    const checkEmailStatus = async () => {
      try {
        const response = await fetch('/api/account/password-reset-status');
        if (response.ok) {
          const data = await response.json();
          setEmailConfigured(data.email_configured);
        }
      } catch (err) {
        console.error('Failed to check email status:', err);
      } finally {
        setCheckingStatus(false);
      }
    };

    checkEmailStatus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/account/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to send reset email');
      }

      setSubmitted(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Email not configured state
  if (!checkingStatus && !emailConfigured) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-display-lg inde-gradient-text mb-2">InDE</h1>
            <p className="text-body-md text-zinc-500">Password Reset</p>
          </div>

          <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
            <div className="flex items-center gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg mb-6">
              <AlertTriangle className="h-6 w-6 text-amber-400 flex-shrink-0" />
              <div>
                <h2 className="text-body-sm font-medium text-amber-400">
                  Email Not Configured
                </h2>
                <p className="text-caption text-zinc-400 mt-1">
                  Password reset via email is not available on this InDE installation.
                  Please contact your administrator for a recovery link.
                </p>
              </div>
            </div>

            <Link to="/login">
              <Button variant="outline" className="w-full">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Login
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Success state
  if (submitted) {
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
                Check Your Email
              </h2>
              <p className="text-caption text-zinc-400 mb-6">
                If an account exists for <strong className="text-zinc-300">{email}</strong>,
                you'll receive a password reset link shortly.
              </p>
              <p className="text-caption text-zinc-500 mb-6">
                The link will expire in 1 hour. Check your spam folder if you don't see it.
              </p>

              <Link to="/login">
                <Button variant="outline" className="w-full">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Login
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
          <p className="text-body-md text-zinc-500">Password Reset</p>
        </div>

        <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
          <h2 className="text-body-md font-medium text-zinc-200 mb-2">
            Forgot your password?
          </h2>
          <p className="text-caption text-zinc-400 mb-6">
            Enter your email address and we'll send you a link to reset your password.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-body-sm text-zinc-400 mb-1.5">
                Email Address
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

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <AlertCircle className="h-4 w-4 text-red-400" />
                <span className="text-sm text-red-400">{error}</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading || !email}
              className="w-full bg-inde-600 hover:bg-inde-700 text-white"
            >
              <Mail className="h-4 w-4 mr-2" />
              {loading ? 'Sending...' : 'Send Reset Link'}
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
          InDE v4.4.0
        </p>
      </div>
    </div>
  );
}
