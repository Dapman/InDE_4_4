/**
 * PasswordChange Component
 * Allows authenticated users to change their password.
 *
 * v3.12: Account Trust & Completeness
 */

import { useState } from 'react';
import { Eye, EyeOff, CheckCircle, AlertCircle, Lock } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { cn } from '../../lib/utils';
import { useAuthStore } from '../../stores/authStore';

export default function PasswordChange() {
  const token = useAuthStore((state) => state.token);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const passwordRequirements = [
    { met: newPassword.length >= 8, text: 'At least 8 characters' },
    { met: /[A-Z]/.test(newPassword), text: 'One uppercase letter' },
    { met: /[a-z]/.test(newPassword), text: 'One lowercase letter' },
    { met: /[0-9]/.test(newPassword), text: 'One number' },
  ];

  const isValid =
    currentPassword.length > 0 &&
    newPassword.length >= 8 &&
    newPassword === confirmPassword;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/account/change-password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to change password');
      }

      setSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Current Password */}
      <div>
        <label className="block text-body-sm text-zinc-400 mb-1.5">
          Current Password
        </label>
        <div className="relative">
          <Input
            type={showCurrent ? 'text' : 'password'}
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Enter current password"
            className="bg-surface-3 border-surface-border-light pr-10"
          />
          <button
            type="button"
            onClick={() => setShowCurrent(!showCurrent)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
          >
            {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* New Password */}
      <div>
        <label className="block text-body-sm text-zinc-400 mb-1.5">
          New Password
        </label>
        <div className="relative">
          <Input
            type={showNew ? 'text' : 'password'}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Enter new password"
            className="bg-surface-3 border-surface-border-light pr-10"
          />
          <button
            type="button"
            onClick={() => setShowNew(!showNew)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
          >
            {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>

        {/* Password requirements */}
        {newPassword.length > 0 && (
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
        <label className="block text-body-sm text-zinc-400 mb-1.5">
          Confirm New Password
        </label>
        <div className="relative">
          <Input
            type={showConfirm ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
            className={cn(
              'bg-surface-3 border-surface-border-light pr-10',
              confirmPassword.length > 0 && newPassword !== confirmPassword && 'border-red-500'
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
        {confirmPassword.length > 0 && newPassword !== confirmPassword && (
          <p className="text-caption text-red-400 mt-1">Passwords do not match</p>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <AlertCircle className="h-4 w-4 text-red-400" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {/* Success message */}
      {success && (
        <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
          <CheckCircle className="h-4 w-4 text-green-400" />
          <span className="text-sm text-green-400">Password updated successfully!</span>
        </div>
      )}

      {/* Submit button */}
      <Button
        type="submit"
        disabled={!isValid || loading}
        className="w-full bg-inde-600 hover:bg-inde-700 text-white"
      >
        <Lock className="h-4 w-4 mr-2" />
        {loading ? 'Updating...' : 'Update Password'}
      </Button>
    </form>
  );
}
