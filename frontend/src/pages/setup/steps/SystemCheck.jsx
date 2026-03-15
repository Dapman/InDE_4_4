/**
 * Step 5: System Verification
 * Verify all systems are operational
 */

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Loader2, RefreshCw, Activity } from 'lucide-react';

const CHECKS = [
  { id: 'license', name: 'License Service', endpoint: '/api/system/license' },
  { id: 'database', name: 'Database', endpoint: '/api/system/stats' },
  { id: 'llm', name: 'LLM Gateway', endpoint: '/api/coaching/health' },
  { id: 'events', name: 'Event Bus', endpoint: '/health' },
  { id: 'ikf', name: 'IKF Service', endpoint: '/api/ikf/health' },
];

export default function SystemCheck({ data, updateData, onValidating }) {
  const [checks, setChecks] = useState(
    CHECKS.map((c) => ({ ...c, status: 'pending', message: '' }))
  );
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    runChecks();
  }, []);

  const runChecks = async () => {
    setIsRunning(true);
    onValidating(true);

    const results = await Promise.all(
      CHECKS.map(async (check) => {
        try {
          const response = await fetch(check.endpoint, { timeout: 5000 });
          if (response.ok) {
            return { ...check, status: 'success', message: 'Operational' };
          } else {
            return { ...check, status: 'warning', message: `Status ${response.status}` };
          }
        } catch (err) {
          // For non-critical services, mark as warning instead of failure
          if (['ikf', 'events'].includes(check.id)) {
            return { ...check, status: 'warning', message: 'Not responding (optional)' };
          }
          return { ...check, status: 'error', message: 'Not responding' };
        }
      })
    );

    setChecks(results);
    setIsRunning(false);
    onValidating(false);

    // Check if all critical checks passed
    const criticalPassed = results
      .filter((r) => !['ikf', 'events'].includes(r.id))
      .every((r) => r.status === 'success' || r.status === 'warning');

    updateData('verification', {
      allPassed: criticalPassed,
      results,
    });
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'warning':
        return <CheckCircle className="w-5 h-5 text-yellow-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Loader2 className="w-5 h-5 text-inde-400 animate-spin" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
        return 'border-green-500/30 bg-green-500/10';
      case 'warning':
        return 'border-yellow-500/30 bg-yellow-500/10';
      case 'error':
        return 'border-red-500/30 bg-red-500/10';
      default:
        return 'border-inde-600 bg-inde-800/50';
    }
  };

  const allPassed = checks.every((c) => c.status === 'success' || c.status === 'warning');
  const hasErrors = checks.some((c) => c.status === 'error');

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 bg-inde-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <Activity className="w-8 h-8 text-inde-300" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          System Verification
        </h2>
        <p className="text-inde-400">
          Checking all InDE services are operational.
        </p>
      </div>

      <div className="space-y-3">
        {checks.map((check) => (
          <div
            key={check.id}
            className={`flex items-center justify-between p-4 rounded-lg border ${getStatusColor(check.status)}`}
          >
            <div className="flex items-center gap-3">
              {getStatusIcon(check.status)}
              <span className="text-white font-medium">{check.name}</span>
            </div>
            <span className="text-sm text-inde-400">{check.message}</span>
          </div>
        ))}
      </div>

      {allPassed && !isRunning && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 text-center">
          <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
          <p className="text-green-400 font-medium">All systems operational!</p>
          <p className="text-inde-400 text-sm mt-1">
            InDE is ready for use.
          </p>
        </div>
      )}

      {hasErrors && !isRunning && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <p className="text-red-400 text-sm mb-3">
            Some services are not responding. Check your Docker containers are running.
          </p>
          <button
            onClick={runChecks}
            className="w-full py-2 bg-inde-700 text-white rounded-lg hover:bg-inde-600 flex items-center justify-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Retry Checks
          </button>
        </div>
      )}

      {isRunning && (
        <div className="text-center text-inde-400">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
          Running system checks...
        </div>
      )}
    </div>
  );
}
