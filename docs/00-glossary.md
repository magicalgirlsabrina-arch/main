# 📖 Glossary — Spellman Manor terminology
*key for mapping themed names → real technology*

Throughout the dashboard, every themed name has a technical subtitle in a
small monospace font underneath. This page is the master key.

## Hosts (physical machines)

| Themed name | Tech | Tailscale IP |
|---|---|---|
| **Spellman Manor** | mac mini | `100.106.134.96` |
| **Harvey's Workshop** | mac pro | `100.79.115.101` |
| **Zelda's Study** | macbook pro | `100.112.73.96` |
| **The Magic Mirror** | android tv (viewer only) | — |

## Familiars (AI agent processes)

| Themed name | Tech | Lives on | Personality |
|---|---|---|---|
| 🐈‍⬛ **Salem** | `openclaw familiar · spellman-manor:18789` | Mac mini | The cat. Schemes. |
| ☕ **Hilda** | `openclaw familiar · spellman-manor:18790` | Mac mini | Chaos energy aunt. |
| 📖 **Zelda** | `openclaw familiar · zeldas-study:18789` | MacBook Pro | Precise, scholarly aunt. |
| 🛠 **Harvey** | `openclaw familiar · harveys-workshop:18789` | Mac Pro | Steady mortal. |

## Services in the dashboard stack

| Themed name | Tech | Port | What it does |
|---|---|---|---|
| 🔮 **The Discovery of Magic** | `homepage` | `:3000` | Front-door dashboard |
| 📜 **The Spellbook** | `coven-mail-bridge` | `:18793` | Mail UI + console |
| 🪞 **The Magic Mirror** | `nginx` (static) | `:8080` | TV kiosk page |
| 💗 **Vital Signs of the Coven** | `beszel` | `:8090` | System monitoring |
| 👁 **The Watcher** | `prometheus` | `:9090` | Metrics scraper |
| 🔔 **Howling Hat** | `alertmanager` | `:9093` | Alert routing |
| 🌙 **The Scrying Glass** | `grafana` | `:3001` | Deep dashboards |

## Other moving parts

| Themed name | Tech |
|---|---|
| **Coven Mailbox** | `mailbox-server.py` · `:18792` · existing launchd service |
| **Claude Bridge** | tiny `claude -p` HTTP wrapper · `:18794` per Mac |
| **Other Realm** | primary SSD (storage) |
| **Katrina** | backup drive |
| **The Linen Closet** | metaphor for the Tailscale tunnel + docker network |
| **Westbridge** | metaphor for the healthy/quiet state |

## Grafana dashboards

| Themed name | Tech | Shows |
|---|---|---|
| **The Coven Atlas** | `grafana://coven-atlas` (home dashboard) | Coven overview — who's alive, mail flow, circuits |
| **The Cast Log** | `grafana://cast-log` | OpenClaw spells/sec, tokens, sessions, latency |

## Alert severities

| Severity tag | Meaning | Repeat |
|---|---|---|
| `spellbook` | Informational (mail, all-clear) | 24h |
| `hex` | Warning — sustained but not broken | 6h |
| `backfire` | Critical — something is actually broken | 1h |

## Show vocabulary used as glue

| Phrase | Used in code/config to mean |
|---|---|
| "Spell" | An OpenClaw request (one prompt → response) |
| "Cast" | Invoking a spell |
| "Séance" | An active OpenClaw session (open conversation) |
| "Backfire" | A 5xx error from a familiar |
| "Coven Mail" | Inter-familiar messaging (existing `mailbox-server.py`) |
| "The Linen Closet" | Tailscale tunnel / docker network |
| "The Other Realm" | The metrics/observability layer |
| "Westbridge calm" | All-systems-healthy state |
