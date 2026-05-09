# 🌙 Spellman Manor — The Discovery of Magic
*self-hosted dashboard · 3 macs · 4 openclaw familiars · over tailscale*

A 90s celestial witchy dashboard for Sabrina Ryan's Spellman Manor setup —
3 Macs running 4 OpenClaw familiars (*Salem*, *Hilda*, *Zelda*, *Harvey*)
across Tailscale, with Coven Mail integration, themed alerts, peer
debugging, and a TV kiosk view.

Throughout the dashboard and these docs, themed names appear with a
technical subtitle in monospace underneath — like:

> ### 🔮 The Discovery of Magic
> *homepage · :3000*

The fancy name is for vibes; the subtitle is for actually finding things.

> *"The book contains everything you need to know about being a witch."*

---

## The household

| Themed name | Real device | Tailnet IP | Familiars hosted |
|---|---|---|---|
| **Spellman Manor** *(mac mini · hub · always on)* | Mac mini | `100.106.134.96` | Salem :18789 · Hilda :18790 |
| **Harvey's Workshop** *(mac pro)* | Mac Pro | `100.79.115.101` | Harvey :18789 |
| **Zelda's Study** *(macbook pro)* | MacBook Pro | `100.112.73.96` | Zelda :18789 |
| **The Magic Mirror** *(android tv · viewer only)* | Android TV | — | — |
| **Other Realm** *(primary ssd)* | SSD | — | — |
| **Katrina** *(backup drive)* | Backup drive | — | — |

3 hosts, 4 familiars (Salem and Hilda share the mini because the Android TV
can't run OpenClaw — see [`docs/03-architecture.md`](docs/03-architecture.md)).

---

## The stack

| Themed name | Tech | Port | Job |
|---|---|---|---|
| 🔮 **The Discovery of Magic** | Homepage | `:3000` | front door |
| 📜 **The Spellbook** | Coven Mail Bridge | `:18793` | mail UI + console |
| 🪞 **The Magic Mirror** | nginx (static) | `:8080` | TV kiosk |
| 💗 **Vital Signs of the Coven** | Beszel | `:8090` | per-host monitoring |
| 👁 **The Watcher** | Prometheus | `:9090` | metrics scraper |
| 🔔 **Howling Hat** | Alertmanager | `:9093` | alert routing |
| 🌙 **The Scrying Glass** | Grafana | `:3001` | deep dashboards |

Everything reaches over the tailnet — nothing exposed to the mortal realm.

---

## Quick start

```sh
# 1. On Spellman Manor (the Mac mini):
cp .env.example .env                              # then fill in real values
echo -n "your-token" > prometheus/tokens/salem.token   # and the other 3
./scripts/spellbook.sh up                         # starts everything
```

After ~30 seconds the script prints all the URLs.

```sh
# 2. On each other Mac (Mac Pro, MacBook Pro):
./scripts/setup-familiar-host.sh spellman-manor.tailXXXX.ts.net
```

Full walkthrough: [`docs/02-setup.md`](docs/02-setup.md)

---

## What it does

- **Live status per familiar** — model, tok/s, active sessions on each tile,
  served by the bridge so the dashboard never breaks if an OpenClaw
  endpoint changes.
- **Coven Mail UI** at `:18793/` — read history, send mail to one familiar,
  broadcast to all, mark-as-read.
- **Peer-debug primitives** — peer-ping, broadcast self-test, circuit
  breakers (so a flaky familiar doesn't get hammered).
- **Claude Code bridge** on each Mac — exposes `claude -p` over HTTP so any
  familiar can borrow another Mac's Claude.
- **Surveillance** — live activity feed (mail · circuits · cron · watchdog),
  per-job heartbeat tracking, available-upgrade scanner with auto-fetched
  GitHub release notes + cheap "verdict" review (safe / recommended /
  review / wait).
- **Themed alerts** — *Salem's Napping*, *Backfired Spell*, *Time Ball
  Slowdown*, *Howling Hat Delivery*, *Witch's License Revoked*, *Cron Gone
  Silent*, *Watchdog Stopped*. Every alert mapped to a real Prometheus
  condition. See [`docs/07-alerts.md`](docs/07-alerts.md).
- **Magic Mirror** at `:8080` — TV-optimized view with big text and
  pulsing indicators.
- **Spellbook** at `:18793/` — coven-mail archive with four tabs:
  History · Send · Debug · Surveillance.

---

## Daily incantations

```sh
./scripts/spellbook.sh up         # start everything
./scripts/spellbook.sh down       # stop everything
./scripts/spellbook.sh status     # what's running
./scripts/spellbook.sh logs       # tail logs
./scripts/spellbook.sh update     # pull new images, restart
./scripts/spellbook.sh peer       # health-check all familiars
./scripts/spellbook.sh broadcast "message"   # mail every familiar
./scripts/spellbook.sh selftest   # ask each to respond with 'alive'
```

Or directly:
```sh
./scripts/coven-status.sh
./scripts/coven-broadcast.sh --from sabrina "STATUS — please respond"
```

---

## Documentation

Twelve focused docs in [`docs/`](docs/):

- [`00-glossary.md`](docs/00-glossary.md) — terminology key
- [`01-overview.md`](docs/01-overview.md) — what this whole thing is
- [`02-setup.md`](docs/02-setup.md) — step-by-step install
- [`03-architecture.md`](docs/03-architecture.md) — who lives where
- [`04-troubleshooting.md`](docs/04-troubleshooting.md) — when things break
- [`05-coven-mail.md`](docs/05-coven-mail.md) — mail + bridge API
- [`06-claude-on-macs.md`](docs/06-claude-on-macs.md) — Claude integration
- [`07-alerts.md`](docs/07-alerts.md) — what each themed alert means
- [`08-customizing.md`](docs/08-customizing.md) — adding familiars, colors
- [`09-debugging.md`](docs/09-debugging.md) — peer-debug primitives
- [`10-magic-mirror.md`](docs/10-magic-mirror.md) — TV kiosk
- [`11-upgrading.md`](docs/11-upgrading.md) — safe upgrades + rollback
- [`12-watchdog-cron.md`](docs/12-watchdog-cron.md) — heartbeat patterns for cron + watchdog

---

## Repo layout

```
.env.example                          credentials template (copy to .env)
docker-compose.yml                    the stack (one file runs everything)
homepage/                             Homepage YAML config + custom.css theme
coven-mail-bridge/                    custom Python service (no deps)
magic-mirror/                         static HTML/CSS/JS for the TV
prometheus/                           scrape config + themed alert rules
alertmanager/                         alert routing
grafana/                              auto-imported dashboards
scripts/                              spellbook, broadcast, status, setup-host
docs/                                 13 markdown files
```

---

## Honest caveats

- **OpenClaw metric names** in `prometheus/alerts.yml` and the Grafana
  dashboards are educated guesses (`openclaw_gateway_requests_total`,
  `openclaw_tokens_generated_total`, etc.). If your version exposes
  different names, the panels show "no data" and alerts won't fire.
  Find the real names with:
  ```sh
  curl -sH "Authorization: Bearer $TOKEN" http://salem-host:18789/api/diagnostics/prometheus | grep -v ^#
  ```
- **OpenClaw `/api/diagnostics/summary`** — assumed shape:
  `{model, tokens_per_sec, active_sessions}`. Adjust mappings in
  `homepage/services.yaml` if your version differs.
- **First `docker compose up -d`** may surface tweaks. Most likely
  fixes: token mismatch, wrong tailnet IP in `.env`, or
  `COVEN_MAILBOX_DIR` not pointing at the right home folder.

If a familiar shows offline on the dashboard but you can ping it directly,
[`docs/04-troubleshooting.md`](docs/04-troubleshooting.md) has the runbook.
