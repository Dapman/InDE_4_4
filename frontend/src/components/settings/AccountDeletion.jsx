/**
 * AccountDeletion Component
 * Danger zone for account deletion with confirmation flow.
 *
 * v3.12: Account Trust & Completeness
 */

import { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Trash2,
  X,
  CheckCircle,
  AlertCircle,
  Clock,
  Shield,
  Database
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { cn } from '../../lib/utils';
import { useAuthStore } from '../../stores/authStore';

export default function AccountDeletion() {
  const [expanded, setExpanded] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [confirmEmail, setConfirmEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [deletionStatus, setDeletionStatus] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(true);

  const user = useAuthStore((state) => state.user);
  const token = useAuthStore((state) => state.token);
  const userEmail = user?.email || '';

  // Check current deletion status
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch('/api/account/deletion-status', {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (response.ok) {
          const data = await response.json();
          setDeletionStatus(data);
        }
      } catch (err) {
        console.error('Failed to check deletion status:', err);
      } finally {
        setCheckingStatus(false);
      }
    };

    checkStatus();
  }, [token]);

  const handleRequestDeletion = async () => {
    if (confirmEmail.toLowerCase() !== userEmail.toLowerCase()) {
      setError('Email does not match your account email');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/account/request-deletion', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ confirm_email: confirmEmail })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to request deletion');
      }

      setDeletionStatus({
        status: 'deactivated',
        deletion_scheduled_for: data.scheduled_for
      });
      setShowModal(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  // Show pending deletion status
  if (deletionStatus?.status === 'deactivated') {
    return (
      <div className="border-2 border-amber-500/30 rounded-lg overflow-hidden">
        <div className="bg-amber-500/10 px-4 py-3 flex items-center gap-3">
          <Clock className="h-5 w-5 text-amber-400" />
          <div>
            <h3 className="text-body-sm font-medium text-amber-400">
              Account Deletion Scheduled
            </h3>
            <p className="text-caption text-amber-300/70">
              Your account will be permanently deleted on{' '}
              <strong>{formatDate(deletionStatus.deletion_scheduled_for)}</strong>
            </p>
          </div>
        </div>
        <div className="p-4 bg-surface-2">
          <p className="text-caption text-zinc-400 mb-3">
            To cancel this deletion and keep your account, click the cancellation link
            in the confirmation email we sent you.
          </p>
          <p className="text-caption text-zinc-500">
            If you didn't receive the email, check your spam folder or contact support.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Danger Zone Collapsible Section */}
      <div className="border-2 border-red-500/30 rounded-lg overflow-hidden">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full bg-red-500/10 px-4 py-3 flex items-center justify-between hover:bg-red-500/15 transition-colors"
        >
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <span className="text-body-sm font-medium text-red-400">Danger Zone</span>
          </div>
          {expanded ? (
            <ChevronDown className="h-5 w-5 text-red-400" />
          ) : (
            <ChevronRight className="h-5 w-5 text-red-400" />
          )}
        </button>

        {expanded && (
          <div className="p-4 bg-surface-2 border-t border-red-500/20">
            <h3 className="text-body-sm font-medium text-zinc-200 mb-2">
              Delete Your Account
            </h3>
            <p className="text-caption text-zinc-400 mb-4">
              Permanently delete your InDE account and all associated data. This action
              cannot be undone after the 14-day grace period.
            </p>

            {/* What gets deleted vs preserved */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Trash2 className="h-4 w-4 text-red-400" />
                  <span className="text-caption font-medium text-red-400">
                    Will be deleted
                  </span>
                </div>
                <ul className="text-caption text-zinc-400 space-y-1">
                  <li>• Your account and profile</li>
                  <li>• All pursuit data and artifacts</li>
                  <li>• Coaching session history</li>
                  <li>• Personal memory records</li>
                </ul>
              </div>

              <div className="p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="h-4 w-4 text-green-400" />
                  <span className="text-caption font-medium text-green-400">
                    Will be preserved
                  </span>
                </div>
                <ul className="text-caption text-zinc-400 space-y-1">
                  <li>• Anonymized innovation patterns</li>
                  <li>• IKF contributions (cannot be traced to you)</li>
                  <li className="text-zinc-500 italic">
                    These are not personal data under GDPR
                  </li>
                </ul>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={() => setShowModal(true)}
              className="text-red-400 border-red-500/30 hover:bg-red-500/10"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete My Account
            </Button>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="bg-surface-2 border-surface-border max-w-md">
          <DialogHeader>
            <DialogTitle className="text-zinc-200 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              Delete Your Account
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              This action cannot be undone. Your account will be permanently deleted
              after a 14-day grace period.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Warning box */}
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-caption text-red-400 font-medium mb-2">
                What happens when you delete your account:
              </p>
              <ul className="text-caption text-zinc-400 space-y-1">
                <li>• Immediate: Your account is deactivated (you cannot log in)</li>
                <li>• 14 days: All personal data is permanently deleted</li>
                <li>• Check your email for a cancellation link</li>
              </ul>
            </div>

            {/* Email confirmation */}
            <div>
              <label className="block text-body-sm text-zinc-300 mb-2">
                Type <strong className="text-zinc-200">{userEmail}</strong> to confirm:
              </label>
              <Input
                type="email"
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                placeholder="Enter your email"
                className="bg-surface-3 border-surface-border-light"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <AlertCircle className="h-4 w-4 text-red-400" />
                <span className="text-sm text-red-400">{error}</span>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setShowModal(false)}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleRequestDeletion}
                disabled={
                  loading ||
                  confirmEmail.toLowerCase() !== userEmail.toLowerCase()
                }
                className="flex-1 bg-red-600 hover:bg-red-700 text-white"
              >
                {loading ? 'Processing...' : 'Schedule Deletion'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
