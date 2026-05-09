# 🐺 Watchdog + cron heartbeats
*coven-mail-bridge endpoints · `POST /api/watchdog/heartbeat` · `POST /api/cron/heartbeat`*

The Surveillance tab in the Spellbook shows live status for cron jobs and
watchdogs across the household. Each one is "self-reporting" — it tells
the bridge "I just ran" and the bridge tracks `last_seen` per name.

If a job stops reporting (fails, gets disabled, host went to sleep), it
appears as **stale** in the UI and `coven_cron_age_seconds` /
`coven_watchdog_age_seconds` show the age in Prometheus.

## Why heartbeats instead of scraping crontab

Cleaner. The bridge doesn't need to read each Mac's crontab over SSH or
mount each home directory. Each job is in charge of saying it ran. If
the job script is broken, it can't lie about being healthy — silence
reads as "stale" within 24 hours.

## Wiring up a cron job

Add the curl line to the bottom of any cron job:

```sh
# crontab -e on Spellman Manor
0 3 * * * /Users/sabrinaryan/scripts/backup-mailbox.sh && \
          curl -s -X POST http://localhost:18793/api/cron/heartbeat \
          -H 'Content-Type: application/json' \
          -d '{"name":"backup-mailbox","status":"ok","host":"spellman-manor","schedule":"0 3 * * *"}'
```

If the script fails, the `&&` short-circuits and no heartbeat is sent —
the job appears stale within 24h.

For a more nuanced version that always reports (even on failure):

```sh
0 3 * * * /Users/sabrinaryan/scripts/backup-mailbox.sh; \
          curl -s -X POST http://localhost:18793/api/cron/heartbeat \
          -H 'Content-Type: application/json' \
          -d "{\"name\":\"backup-mailbox\",\"status\":\"$([[ $? -eq 0 ]] && echo ok || echo fail)\",\"host\":\"spellman-manor\",\"schedule\":\"0 3 * * *\"}"
```

## Heartbeat payload reference

```jsonc
POST /api/cron/heartbeat
{
  "name":        "backup-mailbox",   // required, unique per job
  "status":      "ok",               // ok | fail | warn
  "host":        "spellman-manor",   // optional but recommended
  "schedule":    "0 3 * * *",        // optional human-readable cron expr
  "duration_ms": 8420,               // optional
  "output":      "12.4MB synced"     // optional last 500 chars
}
```

Watchdog is the same shape, posted to `/api/watchdog/heartbeat`.

## Wiring up a watchdog

A watchdog is a process that runs on a loop (not via cron) and
periodically reports it's alive. Pattern in bash:

```sh
#!/usr/bin/env bash
# salem-watchdog.sh — runs in a launchd KeepAlive=true plist
while true; do
  if curl -fs -m 5 http://localhost:18789/health >/dev/null; then
    status=ok; out="alive"
  else
    status=fail; out="salem health failed"
  fi
  curl -s -X POST http://100.106.134.96:18793/api/watchdog/heartbeat \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"salem-watchdog\",\"status\":\"$status\",\"host\":\"$(hostname)\",\"output\":\"$out\"}"
  sleep 60
done
```

Save as `~/.openclaw/workspace/scripts/salem-watchdog.sh`, mark
executable, and add a launchd plist that runs it with `KeepAlive=true`.

## What "stale" means

| Type | Considered stale after |
|---|---|
| Cron heartbeat | 24 hours since last seen |
| Watchdog heartbeat | 10 minutes since last seen |

You can change those thresholds in `coven-mail-bridge/server.py`:

```python
"stale": (now - v.get("last_seen", 0)) > 24 * 3600   # cron
"stale": (now - v.get("last_seen", 0)) > 600         # watchdog
```

## Where it shows up

- **Spellbook UI → Surveillance tab** — live list per job/watchdog with status, host, last seen.
- **Homepage → Surveillance tile** — shows the most recent activity event (rotates through whatever just happened).
- **Prometheus** — emits `coven_cron_age_seconds{job="..."}` and `coven_watchdog_age_seconds{watchdog="..."}` so you can graph staleness in Grafana or alert on it.

## Suggested first jobs to instrument

Even before you have a backup script, these are easy wins:

| Name | What it does |
|---|---|
| `mailbox-prune` | Truncate `inbox.jsonl` weekly to keep it under, say, 10MB |
| `tailscale-up-check` | Hourly: `tailscale status \| grep online` and report |
| `openclaw-rolling-restart` | Weekly restart of each familiar to clear memory |
| `coven-mailbox-backup` | Nightly rsync to `Katrina` |
| `health-summary-mail` | Every morning: peer-ping the coven, mail Salem the report |

Each one is a 5-line bash script + one curl line for the heartbeat.

## Persistence

**Heads up:** heartbeats are in-memory only — they reset when the bridge
container restarts. That's fine for "is it alive right now?" but if you
need historical staleness, scrape the Prometheus metrics into long-term
storage. (Prometheus already does this for 30 days.)

## Adding a new alert

In `prometheus/alerts.yml`:

```yaml
- alert: CronGoneSilent
  expr: coven_cron_age_seconds > 3600 * 25     # missed by an hour
  for: 5m
  labels:
    severity: hex
    theme: cron-stale
  annotations:
    summary: "🌙 cron job '{{ $labels.job }}' has gone silent"
```

Then `./scripts/spellbook.sh reload-prometheus`.
