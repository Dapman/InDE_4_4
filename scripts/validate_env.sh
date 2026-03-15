#!/bin/bash
# InDE Environment Validation Script
# Run before first deployment to catch common configuration issues.
# Usage: bash scripts/validate_env.sh

set -e
ERRORS=0

echo "=== InDE Environment Validation ==="
echo ""

# Check .env exists
if [ ! -f ".env" ]; then
  echo "❌ MISSING: .env file not found. Copy .env.template to .env and configure it."
  ERRORS=$((ERRORS + 1))
else
  echo "✓ .env file found"

  # Check for Windows CRLF line endings (the #1 deployment killer)
  if file .env | grep -q "CRLF"; then
    echo "❌ CRLF: .env has Windows line endings. Run: sed -i 's/\r$//' .env"
    ERRORS=$((ERRORS + 1))
  else
    echo "✓ .env line endings are Unix (LF)"
  fi

  # Check required variables are set and non-empty
  source .env 2>/dev/null || true
  for VAR in ANTHROPIC_API_KEY JWT_SECRET INDE_ADMIN_EMAIL; do
    if [ -z "${!VAR}" ]; then
      echo "❌ MISSING: $VAR is not set in .env"
      ERRORS=$((ERRORS + 1))
    else
      echo "✓ $VAR is set"
    fi
  done

  # Check ANTHROPIC_API_KEY format
  if [[ "${ANTHROPIC_API_KEY}" != sk-ant-* ]]; then
    echo "⚠️  WARNING: ANTHROPIC_API_KEY does not start with 'sk-ant-' — verify it is correct"
  fi
fi

echo ""
if [ $ERRORS -eq 0 ]; then
  echo "✓ All checks passed. Safe to deploy."
  exit 0
else
  echo "❌ $ERRORS error(s) found. Resolve before deploying."
  exit 1
fi
