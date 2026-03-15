/**
 * Step 6: Setup Complete
 * Summary and launch
 */

import { CheckCircle, Rocket, Mail, Building2, Key, Shield } from 'lucide-react';

export default function SetupComplete({ data }) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-10 h-10 text-green-500" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Setup Complete!
        </h2>
        <p className="text-inde-400">
          Your InDE deployment is ready for innovation.
        </p>
      </div>

      {/* Configuration Summary */}
      <div className="bg-inde-700/50 rounded-lg p-4 space-y-4">
        <h3 className="text-sm font-medium text-inde-300 uppercase tracking-wide">
          Configuration Summary
        </h3>

        <div className="grid gap-4">
          {/* License */}
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded bg-inde-600 flex items-center justify-center flex-shrink-0">
              <Key className="w-4 h-4 text-inde-300" />
            </div>
            <div>
              <p className="text-white text-sm font-medium">License</p>
              <p className="text-inde-400 text-sm">
                {data.license?.tier ? (
                  <>
                    {data.license.tier.charAt(0).toUpperCase() + data.license.tier.slice(1)} tier
                    {data.license.seat_limit && ` (${data.license.seat_limit} seats)`}
                  </>
                ) : (
                  'Active'
                )}
              </p>
            </div>
          </div>

          {/* Organization */}
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded bg-inde-600 flex items-center justify-center flex-shrink-0">
              <Building2 className="w-4 h-4 text-inde-300" />
            </div>
            <div>
              <p className="text-white text-sm font-medium">Organization</p>
              <p className="text-inde-400 text-sm">
                {data.organization?.name || 'Created'}
              </p>
            </div>
          </div>

          {/* Admin */}
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded bg-inde-600 flex items-center justify-center flex-shrink-0">
              <Mail className="w-4 h-4 text-inde-300" />
            </div>
            <div>
              <p className="text-white text-sm font-medium">Administrator</p>
              <p className="text-inde-400 text-sm">
                {data.admin?.email || 'Created'}
              </p>
            </div>
          </div>

          {/* API Key */}
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded bg-inde-600 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-inde-300" />
            </div>
            <div>
              <p className="text-white text-sm font-medium">API Connection</p>
              <p className="text-inde-400 text-sm">
                {data.apiKey?.valid ? 'Configured and validated' : 'Configured'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Next Steps */}
      <div className="bg-inde-800/50 border border-inde-700 rounded-lg p-4">
        <h3 className="text-sm font-medium text-inde-300 mb-3">
          Next Steps
        </h3>
        <ul className="space-y-2 text-sm text-inde-400">
          <li className="flex items-center gap-2">
            <Rocket className="w-4 h-4 text-inde-500" />
            Create your first innovation pursuit
          </li>
          <li className="flex items-center gap-2">
            <Rocket className="w-4 h-4 text-inde-500" />
            Invite team members to collaborate
          </li>
          <li className="flex items-center gap-2">
            <Rocket className="w-4 h-4 text-inde-500" />
            Explore the coaching experience
          </li>
        </ul>
      </div>

      <div className="text-center text-inde-500 text-sm">
        Click "Launch InDE" to begin your innovation journey.
      </div>
    </div>
  );
}
