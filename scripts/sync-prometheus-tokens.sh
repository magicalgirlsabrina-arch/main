#!/usr/bin/env bash
# ✦ Sync prometheus/tokens/*.token from .env (single source of truth) ✦
#
# Reads SALEM_GATEWAY_TOKEN / HILDA_GATEWAY_TOKEN / ZELDA_GATEWAY_TOKEN /
# HARVEY_GATEWAY_TOKEN from .env and writes each to prometheus/tokens/<name>.token
# (no trailing newline, since Prometheus reads them with credentials_file:).
#
# Called automatically by `spellbook.sh up`. Safe to re-run anytime.

set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "✗ .env not found — copy .env.example to .env and fill it in." >&2
  exit 1
fi

mkdir -p prometheus/tokens
written=0; skipped=0

for name in salem hilda zelda harvey; do
  var=$(echo "${name}_GATEWAY_TOKEN" | tr '[:lower:]' '[:upper:]')
  # Read the value from .env, stripping surrounding quotes if present.
  val=$(grep -E "^${var}=" .env 2>/dev/null | head -1 | cut -d= -f2- | sed -E 's/^["'\'']?(.*)["'\'']?$/\1/' || true)

  if [ -z "${val:-}" ] || [ "$val" = "replace-with-${name}-operator-token" ]; then
    echo "  ⚠️  $var not set in .env — skipping prometheus/tokens/${name}.token"
    skipped=$((skipped + 1))
    continue
  fi

  printf '%s' "$val" > "prometheus/tokens/${name}.token"
  written=$((written + 1))
done

echo "  ✓ wrote $written prometheus token files (skipped $skipped)"
