/**
 * ErrorBoundary - React class component that catches component errors.
 *
 * v3.15: Wraps workspace zones to provide graceful degradation.
 * Logs errors to the backend diagnostics error buffer.
 */

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Fire-and-forget: log to backend
    const token = localStorage.getItem('inde_token') ?? '';

    fetch('/api/v1/errors/client', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        zone: this.props.zoneName ?? 'unknown',
        error_message: error?.message ?? 'Unknown error',
        component_stack: errorInfo?.componentStack?.slice(0, 500),
      }),
    }).catch(() => {
      // Never throw - this is fire-and-forget
    });

    // Log to console in development
    if (process.env.NODE_ENV !== 'production') {
      console.error(`ErrorBoundary caught error in ${this.props.zoneName}:`, error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center p-8 bg-surface-2 border border-surface-border rounded-lg m-4">
          <div className="w-12 h-12 flex items-center justify-center bg-amber-500/10 rounded-full mb-4">
            <AlertTriangle className="w-6 h-6 text-amber-400" />
          </div>

          <h4 className="text-body-lg font-medium text-zinc-200 mb-2">
            Something went wrong in {this.props.zoneName ?? 'this area'}
          </h4>

          <p className="text-body-sm text-zinc-500 text-center mb-4 max-w-md">
            This area encountered an unexpected problem.
            You can try refreshing this section, or reload the page if the problem persists.
          </p>

          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-surface-4 hover:bg-surface-5 text-zinc-300 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh this section
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
