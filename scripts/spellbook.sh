#!/usr/bin/env bash
# ✦ The Spellbook — manage Spellman Manor (the Mac mini hub) ✦

set -euo pipefail
cd "$(dirname "$0")/.."

cmd=${1:-status}

case "$cmd" in
  up)
    echo "🔮 Opening the linen closet..."
    docker compose up -d
    echo ""
    echo "✨ The Discovery of Magic → http://localhost:3000"
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

  *)
    cat <<EOF
✨ Usage: $0 <command>

Stack control:
  up                       Start the whole dashboard stack
  down                     Stop the stack
  restart                  Stop + start
  update                   docker compose pull + restart
  status                   Show running containers
  logs [service]           Tail logs (optionally for one service)

Coven ops (via the Coven Mail Bridge):
  peer | ping              Health-check all 4 familiars
  broadcast "message"      Send a message to the entire coven
  selftest                 Ask every familiar to respond with 'alive'

Misc:
  reload-prometheus        Hot-reload Prometheus rules without restart
EOF
    exit 1
    ;;
esac
