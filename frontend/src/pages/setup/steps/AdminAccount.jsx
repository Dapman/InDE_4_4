/**
 * Step 3: Admin Account Creation
 * Create the initial administrator account
 */

import { useState } from 'react';
import { User, CheckCircle, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';

export default function AdminAccount({ data, updateData, onValidating }) {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const validateForm = () => {
    if (!formData.fullName.trim()) {
      setError('Full name is required');
      return false;
    }
    if (!formData.email.trim()) {
      setError('Email is required');
      return false;
    }
    if (!formData.email.includes('@')) {
      setError('Please enter a valid email address');
      return false;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    return true;
  };

  const createAdmin = async () => {
    if (!validateForm()) return;

    setIsCreating(true);
    setError(null);
    onValidating(true);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.fullName.trim(),
          email: formData.email.trim().toLowerCase(),
          password: formData.password,
          role: 'admin',
          organization_id: data.organization?.id,
        }),
      });

      if (response.ok) {
        const user = await response.json();
        updateData('admin', {
          created: true,
          userId: user.user_id,
          email: formData.email.trim().toLowerCase(),
          name: formData.fullName.trim(),
        });
      } else {
        const err = await response.json();
        setError(err.detail || 'Failed to create admin account');
      }
    } catch (err) {
      setError('Unable to create account. Please try again.');
    } finally {
      setIsCreating(false);
      onValidating(false);
    }
  };

  const getPasswordStrength = (password) => {
    if (!password) return { level: 0, label: '', color: '' };
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    if (score <= 2) return { level: 1, label: 'Weak', color: 'bg-red-500' };
    if (score <= 3) return { level: 2, label: 'Fair', color: 'bg-yellow-500' };
    if (score <= 4) return { level: 3, label: 'Good', color: 'bg-blue-500' };
    return { level: 4, label: 'Strong', color: 'bg-green-500' };
  };

  const strength = getPasswordStrength(formData.password);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 bg-inde-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <User className="w-8 h-8 text-inde-300" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Create Admin Account
        </h2>
        <p className="text-inde-400">
          Set up the administrator account for your InDE deployment.
        </p>
      </div>

      {data.admin?.created ? (
        // Admin already created
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <span className="text-green-400 font-medium">Admin Account Created</span>
          </div>
          <div className="text-sm">
            <p className="text-white">{data.admin.name}</p>
            <p className="text-inde-400">{data.admin.email}</p>
          </div>
        </div>
      ) : (
        // Admin form
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Full Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={formData.fullName}
              onChange={(e) => handleChange('fullName', e.target.value)}
              placeholder="Jane Smith"
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white placeholder-inde-500 focus:outline-none focus:border-inde-500"
            />
          </div>

          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Email <span className="text-red-400">*</span>
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              placeholder="admin@yourcompany.com"
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white placeholder-inde-500 focus:outline-none focus:border-inde-500"
            />
          </div>

          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Password <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => handleChange('password', e.target.value)}
                placeholder="Min 8 characters"
                className="w-full px-4 py-3 pr-10 bg-inde-900 border border-inde-600 rounded-lg text-white placeholder-inde-500 focus:outline-none focus:border-inde-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-inde-400 hover:text-white"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {formData.password && (
              <div className="mt-2">
                <div className="flex gap-1 mb-1">
                  {[1, 2, 3, 4].map((level) => (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded ${
                        level <= strength.level ? strength.color : 'bg-inde-700'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-xs text-inde-400">{strength.label}</span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Confirm Password <span className="text-red-400">*</span>
            </label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={formData.confirmPassword}
              onChange={(e) => handleChange('confirmPassword', e.target.value)}
              placeholder="Confirm your password"
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white placeholder-inde-500 focus:outline-none focus:border-inde-500"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <button
            onClick={createAdmin}
            disabled={isCreating}
            className={`
              w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2
              ${isCreating
                ? 'bg-inde-700 text-inde-400 cursor-not-allowed'
                : 'bg-inde-500 text-white hover:bg-inde-400'
              }
            `}
          >
            {isCreating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Admin Account'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
