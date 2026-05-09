#!/usr/bin/env bash
# ✦ Print one familiar's gateway token from its OpenClaw config ✦
#
# Run on the host that runs that familiar. Prints just the token, no
# trailing newline — pipe straight into `pbcopy` or paste into .env.
#
#   ./grab-gateway-token.sh salem
#   ./grab-gateway-token.sh hilda
#   ./grab-gateway-token.sh zelda
#   ./grab-gateway-token.sh harvey

set -euo pipefail

NAME=${1:-}
if [ -z "$NAME" ]; then
  echo "Usage: $0 <familiar-name>" >&2
  exit 1
fi

# OpenClaw conventionally stores per-familiar config at:
#   ~/.openclaw/${NAME}.json   (per-familiar)
#   ~/.openclaw/openclaw.json  (single-familiar host)
CONFIG=""
for candidate in \
    "$HOME/.openclaw/${NAME}.json" \
    "$HOME/.openclaw/openclaw.json" \
    "$HOME/.openclaw/config.json"; do
  if [ -f "$candidate" ]; then
    CONFIG="$candidate"
    break
  fi
done

if [ -z "$CONFIG" ]; then
  echo "✗ no OpenClaw config found in ~/.openclaw/" >&2
  echo "  tried: ~/.openclaw/${NAME}.json, ~/.openclaw/openclaw.json, ~/.openclaw/config.json" >&2
  exit 1
fi

# Read the gateway token. Try common shapes:
#   {"gateway":{"auth":{"token":"..."}}}                       ← per Salem's note
#   {"gateway":{"auth":{"tokens":["..."]}}}                    ← older shape
#   {"gateway":{"auth":{"tokens":{"operator":"..."}}}}         ← scoped shape
python3 - "$CONFIG" "$NAME" <<'PY'
import json, sys
cfg_path, name = sys.argv[1], sys.argv[2]
cfg = json.load(open(cfg_path))
auth = cfg.get("gateway", {}).get("auth", {})
tok = auth.get("token")
if not tok:
    toks = auth.get("tokens")
    if isinstance(toks, list) and toks:
        tok = toks[0]
    elif isinstance(toks, dict):
        tok = toks.get("operator") or toks.get("admin") or next(iter(toks.values()), None)
if not tok:
    sys.stderr.write(f"✗ couldn't find gateway.auth.token in {cfg_path}\n")
    sys.stderr.write(f"  found auth keys: {list(auth.keys())}\n")
    sys.exit(2)
sys.stdout.write(tok)
PY
