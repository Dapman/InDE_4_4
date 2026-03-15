/**
 * CancelDeletionPage
 * Allows users to cancel a pending account deletion using the cancellation token.
 *
 * v3.12: Account Trust & Completeness
 */

import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function CancelDeletionPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [displayName, setDisplayName] = useState('');

  useEffect(() => {
    const cancelDeletion = async () => {
      if (!token) {
        setError('No cancellation token provided');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`/api/account/cancel-deletion?token=${encodeURIComponent(token)}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to cancel deletion');
        }

        setSuccess(true);
        setDisplayName(data.display_name || 'Innovator');
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    cancelDeletion();
  }, [token]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
        <div className="text-center">
          <RefreshCw className="animate-spin h-8 w-8 text-inde-500 mx-auto mb-4" />
          <p className="text-zinc-400">Cancelling account deletion...</p>
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
          </div>

          <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mb-4">
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
              <h2 className="text-body-md font-medium text-zinc-200 mb-2">
                Welcome Back, {displayName}!
              </h2>
              <p className="text-caption text-zinc-400 mb-6">
                Your account deletion has been cancelled. Your account is now
                fully active again.
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

  // Error state
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-0 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-display-lg inde-gradient-text mb-2">InDE</h1>
        </div>

        <div className="bg-surface-2 rounded-panel p-8 shadow-panel border border-surface-border">
          <div className="text-center">
            <div className="mx-auto w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-8 w-8 text-red-400" />
            </div>
            <h2 className="text-body-md font-medium text-zinc-200 mb-2">
              Unable to Cancel Deletion
            </h2>
            <p className="text-caption text-zinc-400 mb-6">
              {error || 'This cancellation link is invalid or has already been used.'}
            </p>
            <p className="text-caption text-zinc-500 mb-6">
              If your account was already deleted, you can create a new account.
              For assistance, please contact your administrator.
            </p>

            <Link to="/login">
              <Button className="w-full bg-inde-600 hover:bg-inde-700 text-white">
                Go to Login
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
