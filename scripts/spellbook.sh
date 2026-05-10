#!/usr/bin/env bash
# ✦ The Spellbook — manage Spellman Manor (the Mac mini hub) ✦

set -euo pipefail
cd "$(dirname "$0")/.."

# Auto-prepend Docker Desktop's CLI path on macOS. Docker Desktop installs
# `docker`, `docker compose`, and `docker-credential-desktop` here but
# doesn't add it to user PATH automatically.
if [ -d /Applications/Docker.app/Contents/Resources/bin ]; then
  case ":$PATH:" in
    *":/Applications/Docker.app/Contents/Resources/bin:"*) ;;
    *) export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ;;
  esac
fi

cmd=${1:-status}

case "$cmd" in
  up)
    echo "🔮 Opening the linen closet..."
    if [ -f .env ]; then
      ./scripts/sync-prometheus-tokens.sh
    fi
    docker compose up -d
    echo ""
    echo "✨ The Discovery of Magic → http://localhost:3000"
    echo "🪟 The Veil (PWA install) → http://localhost:3030  ← open in Safari to install"
    echo "📜 The Spellbook         → http://localhost:18793/"
    echo "🪞 The Magic Mirror      → http://localhost:8080"
    echo "💗 Vital Signs           → http://localhost:8090"
    echo "🌙 The Scrying Glass     → http://localhost:3001"
    echo "🔔 Howling Hat           → http://localhost:9093"
    ;;
  down)    docker compose down ;;
  restart) docker compose down && docker compose up -d ;;
  update)  echo "📚 Updating spellbooks..."; docker compose pull && docker compose up -d ;;
  logs)    docker compose logs -f --tail=50 ${2:-} ;;
  status)  docker compose ps ;;

  peer|ping)
    ./scripts/coven-status.sh
    ;;

  broadcast)
    shift
    ./scripts/coven-broadcast.sh "$@"
    ;;

  selftest)
    echo "🩺 Dispatching self-test to the coven..."
    curl -s -X POST http://localhost:18793/api/selftest | python3 -m json.tool
    ;;

  reload-prometheus)
    echo "♻️  Reloading Prometheus config..."
    curl -X POST http://localhost:9090/-/reload
    ;;

  sync-tokens)
    ./scripts/sync-prometheus-tokens.sh
    ;;

  tailnet)
    # Print the tailnet's MagicDNS suffix (e.g. tail4cb40.ts.net).
    if ! command -v tailscale >/dev/null 2>&1; then
      echo "✗ tailscale CLI not found in PATH" >&2
      exit 1
    fi
    if command -v jq >/dev/null 2>&1; then
      tailscale status --json | jq -r '.MagicDNSSuffix // "?"'
    else
      tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("MagicDNSSuffix","?"))'
    fi
    ;;

  distribute-handbook)
    ./scripts/distribute-handbook.sh
    ;;

  *)
    cat <<EOF
✨ Usage: $0 <command>

Stack control:
  up                       Start the stack (auto-syncs prometheus tokens from .env)
  down                     Stop the stack
  restart                  Stop + start
  update                   docker compose pull + restart
  status                   Show running containers
  logs [service]           Tail logs (optionally for one service)

Coven ops:
  peer | ping              Health-check all 4 familiars
  broadcast "message"      Send a message to the entire coven
  selftest                 Ask every familiar to respond with 'alive'
  distribute-handbook      Mail every familiar the URL for the handbook

Setup helpers:
  tailnet                  Print your tailnet's MagicDNS suffix
  sync-tokens              Re-sync prometheus/tokens/*.token from .env

Misc:
  reload-prometheus        Hot-reload Prometheus rules without restart
EOF
    exit 1
    ;;
esac
