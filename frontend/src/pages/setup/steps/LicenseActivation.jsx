/**
 * Step 1: License Activation
 * Enter and validate the InDE license key
 */

import { useState, useEffect } from 'react';
import { Key, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

export default function LicenseActivation({ data, updateData, onValidating }) {
  const [licenseKey, setLicenseKey] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState(null);
  const [licenseInfo, setLicenseInfo] = useState(null);

  // Check for pre-configured license key
  useEffect(() => {
    checkExistingLicense();
  }, []);

  const checkExistingLicense = async () => {
    try {
      const response = await fetch('/api/system/license', {
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const info = await response.json();
        if (info.valid) {
          setLicenseInfo(info);
          updateData('license', { valid: true, ...info });
        }
      }
    } catch (err) {
      // License not yet configured, which is expected
    }
  };

  const validateLicense = async () => {
    if (!licenseKey.trim()) {
      setError('Please enter a license key');
      return;
    }

    setIsValidating(true);
    setError(null);
    onValidating(true);

    try {
      const response = await fetch('http://localhost:8100/api/v1/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_key: licenseKey.trim().toUpperCase() }),
      });

      const result = await response.json();

      if (result.success) {
        setLicenseInfo({
          tier: result.manifest?.tier,
          customer_name: result.manifest?.customer_name,
          seat_limit: result.manifest?.seat_limit,
          expires_at: result.manifest?.expires_at,
        });
        updateData('license', {
          valid: true,
          key: licenseKey.trim().toUpperCase(),
          ...result.manifest,
        });
      } else {
        setError(result.error || 'Invalid license key');
      }
    } catch (err) {
      setError('Unable to validate license. Please check your connection.');
    } finally {
      setIsValidating(false);
      onValidating(false);
    }
  };

  const formatTier = (tier) => {
    const tiers = {
      professional: 'Professional',
      enterprise: 'Enterprise',
      federated: 'Federated',
    };
    return tiers[tier] || tier;
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 bg-inde-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <Key className="w-8 h-8 text-inde-300" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          License Activation
        </h2>
        <p className="text-inde-400">
          Enter your InDE license key to activate this deployment.
        </p>
      </div>

      {licenseInfo?.valid || data.license?.valid ? (
        // License already validated
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <span className="text-green-400 font-medium">License Activated</span>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-inde-400">Tier:</span>
              <span className="text-white ml-2">
                {formatTier(licenseInfo?.tier || data.license?.tier)}
              </span>
            </div>
            <div>
              <span className="text-inde-400">Seats:</span>
              <span className="text-white ml-2">
                {licenseInfo?.seat_limit || data.license?.seat_limit}
              </span>
            </div>
            <div className="col-span-2">
              <span className="text-inde-400">Customer:</span>
              <span className="text-white ml-2">
                {licenseInfo?.customer_name || data.license?.customer_name}
              </span>
            </div>
          </div>
        </div>
      ) : (
        // License input form
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-inde-400 mb-2">
              License Key
            </label>
            <input
              type="text"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value.toUpperCase())}
              placeholder="INDE-PRO-XXXXXXXXXXXX-XXXX"
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white placeholder-inde-500 focus:outline-none focus:border-inde-500 font-mono"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <button
            onClick={validateLicense}
            disabled={isValidating || !licenseKey.trim()}
            className={`
              w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2
              ${isValidating || !licenseKey.trim()
                ? 'bg-inde-700 text-inde-400 cursor-not-allowed'
                : 'bg-inde-500 text-white hover:bg-inde-400'
              }
            `}
          >
            {isValidating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Validating...
              </>
            ) : (
              'Validate License'
            )}
          </button>

          <p className="text-xs text-inde-500 text-center">
            Your license key was provided by InDEVerse. Contact support@indeverse.com if you need assistance.
          </p>
        </div>
      )}
    </div>
  );
}
