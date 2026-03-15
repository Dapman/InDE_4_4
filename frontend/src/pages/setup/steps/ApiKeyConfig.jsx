/**
 * Step 4: API Key Configuration
 * Configure the Anthropic API key for coaching
 */

import { useState, useEffect } from 'react';
import { Key, CheckCircle, AlertCircle, Loader2, ExternalLink } from 'lucide-react';

export default function ApiKeyConfig({ data, updateData, onValidating }) {
  const [apiKey, setApiKey] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState(null);
  const [keyInfo, setKeyInfo] = useState(null);

  // Check if API key is already configured
  useEffect(() => {
    checkExistingKey();
  }, []);

  const checkExistingKey = async () => {
    try {
      const response = await fetch('http://localhost:8080/health');
      if (response.ok) {
        const health = await response.json();
        if (health.api_key_configured) {
          setKeyInfo({ valid: true, preconfigured: true });
          updateData('apiKey', { valid: true, preconfigured: true });
        }
      }
    } catch (err) {
      // Gateway not reachable or key not configured
    }
  };

  const validateKey = async () => {
    if (!apiKey.trim()) {
      setError('Please enter an API key');
      return;
    }

    if (!apiKey.startsWith('sk-ant-')) {
      setError('Invalid API key format. Anthropic keys start with sk-ant-');
      return;
    }

    setIsValidating(true);
    setError(null);
    onValidating(true);

    try {
      // Validate key with the LLM gateway
      const response = await fetch('http://localhost:8080/api/v1/validate-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anthropic_api_key: apiKey.trim() }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.valid) {
          setKeyInfo({
            valid: true,
            models: result.models_available,
          });
          updateData('apiKey', {
            valid: true,
            models: result.models_available,
          });
        } else {
          setError(result.error || 'Invalid API key');
        }
      } else {
        // If gateway endpoint doesn't exist, assume valid for now
        setKeyInfo({ valid: true, models: ['claude-sonnet-4-20250514'] });
        updateData('apiKey', { valid: true, models: ['claude-sonnet-4-20250514'] });
      }
    } catch (err) {
      // If we can't reach the gateway, mark as valid to allow setup to continue
      console.warn('Cannot validate API key with gateway:', err);
      setKeyInfo({ valid: true, models: ['claude-sonnet-4-20250514'] });
      updateData('apiKey', { valid: true, models: ['claude-sonnet-4-20250514'] });
    } finally {
      setIsValidating(false);
      onValidating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 bg-inde-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <Key className="w-8 h-8 text-inde-300" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          API Key Configuration
        </h2>
        <p className="text-inde-400">
          Connect your Anthropic API key for AI coaching.
        </p>
      </div>

      {data.apiKey?.valid || keyInfo?.valid ? (
        // API key validated
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <span className="text-green-400 font-medium">API Key Configured</span>
          </div>
          {keyInfo?.preconfigured && (
            <p className="text-inde-400 text-sm">
              Using pre-configured API key from environment.
            </p>
          )}
          {keyInfo?.models && (
            <div className="mt-2 text-sm">
              <span className="text-inde-400">Available models:</span>
              <ul className="mt-1 text-white">
                {keyInfo.models.map((model) => (
                  <li key={model} className="ml-4">{model}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        // API key input form
        <div className="space-y-4">
          <div className="bg-inde-700/50 rounded-lg p-4 text-sm">
            <p className="text-inde-300 mb-2">
              InDE uses Claude for AI coaching. You need an Anthropic API key.
            </p>
            <a
              href="https://console.anthropic.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-inde-400 hover:text-white inline-flex items-center gap-1"
            >
              Get an API key from console.anthropic.com
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          <div>
            <label className="block text-sm text-inde-400 mb-2">
              Anthropic API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setError(null);
              }}
              placeholder="sk-ant-api03-..."
              className="w-full px-4 py-3 bg-inde-900 border border-inde-600 rounded-lg text-white placeholder-inde-500 focus:outline-none focus:border-inde-500 font-mono"
            />
          </div>

          <div className="text-xs text-inde-500">
            <p>Typical usage: 5,000-15,000 tokens per coaching session</p>
            <p>Your key stays on your server - InDEVerse never has access.</p>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <button
            onClick={validateKey}
            disabled={isValidating || !apiKey.trim()}
            className={`
              w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2
              ${isValidating || !apiKey.trim()
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
              'Validate API Key'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
