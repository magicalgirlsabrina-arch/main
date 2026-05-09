#!/usr/bin/env bash
# ✦ Send a cron / watchdog heartbeat to the Coven Mail Bridge ✦
#
# Drop-in usage at the end of any cron line:
#   /path/to/job.sh && /path/to/coven-heartbeat.sh cron my-job-name
#
# Or in a watchdog loop:
#   while true; do check_thing && coven-heartbeat.sh watchdog my-watchdog; sleep 60; done

set -euo pipefail

KIND=${1:-cron}              # cron | watchdog
NAME=${2:-}
STATUS=${3:-ok}
OUTPUT=${4:-}
BRIDGE=${BRIDGE_URL:-http://localhost:18793}

if [ -z "$NAME" ]; then
  echo "Usage: $0 <cron|watchdog> <name> [status] [output]" >&2
  exit 1
fi

ENDPOINT="$BRIDGE/api/$KIND/heartbeat"

curl -fs -X POST "$ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c '
import json, sys
print(json.dumps({
    "name":   sys.argv[1],
    "status": sys.argv[2],
    "host":   sys.argv[3],
    "output": sys.argv[4],
}))' "$NAME" "$STATUS" "$(hostname -s)" "$OUTPUT")"
