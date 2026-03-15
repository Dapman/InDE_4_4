/**
 * Step 2: Organization Setup
 * Create the initial organization
 */

import { useState } from 'react';
import { Building2, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

const INDUSTRIES = [
  { value: 'technology', label: 'Technology' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'finance', label: 'Finance' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'retail', label: 'Retail' },
  { value: 'education', label: 'Education' },
  { value: 'government', label: 'Government' },
  { value: 'nonprofit', label: 'Nonprofit' },
  { value: 'consulting', label: 'Consulting' },
  { value: 'other', label: 'Other' },
];

const ORG_SIZES = [
  { value: '1-50', label: '1-50 employees' },
  { value: '51-200', label: '51-200 employees' },
  { value: '201-500', label: '201-500 employees' },
  { value: '500+', label: '500+ employees' },
];

export default function OrganizationSetup({ data, updateData, onValidating }) {
  const [formData, setFormData] = useState({
    name: '',
    industry: '',
    size: '',
  });
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const createOrganization = async () => {
    if (!formData.name.trim()) {
      setError('Organization name is required');
      return;
    }

    setIsCreating(true);
    setError(null);
    onValidating(true);

    try {
      const response = await fetch('/api/organizations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name.trim(),
          industry: formData.industry || null,
          size: formData.size || null,
        }),
      });

      if (response.ok) {
        const org = await response.json();
        updateData('organization', {
          id: org.organization_id || org.id,
          name: formData.name.trim(),
          industry: formData.industry,
          size: formData.size,
        });
      } else {
        const err = await response.json();
        setError(err.detail || 'Failed to create organization');
      }
    } catch (err) {
      setError('Unable to create organization. Please try again.');
    } finally {
      setIsCreating(false);
      onValidating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 bg-inde-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <Building2 className="w-8 h-8 text-inde-300" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          Create Your Organization
        </h2>
        <p className="text-inde-400">
          Set up your organization to manage innovators and pursuits.
        </p>
      </div>

      {data.organization?.id ? (
        // Organization already created
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <span className="text-green-400 font-medium">Organization Created</span>
          </div>
          <p className="text-white">{data.organization.name}</p>
        </div>
      ) : (
        // Organization form
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Organization Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="Acme Innovation Labs"
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white placeholder-inde-500 focus:outline-none focus:border-inde-500"
            />
          </div>

          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Industry (optional)
            </label>
            <select
              value={formData.industry}
              onChange={(e) => handleChange('industry', e.target.value)}
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white focus:outline-none focus:border-inde-500"
            >
              <option value="">Select industry...</option>
              {INDUSTRIES.map((ind) => (
                <option key={ind.value} value={ind.value}>
                  {ind.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Organization Size (optional)
            </label>
            <select
              value={formData.size}
              onChange={(e) => handleChange('size', e.target.value)}
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white focus:outline-none focus:border-inde-500"
            >
              <option value="">Select size...</option>
              {ORG_SIZES.map((size) => (
                <option key={size.value} value={size.value}>
                  {size.label}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <button
            onClick={createOrganization}
            disabled={isCreating || !formData.name.trim()}
            className={`
              w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2
              ${isCreating || !formData.name.trim()
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
              'Create Organization'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
