# 📖 Glossary — Spellman Manor terminology

A key for everything in the dashboard so you can map the witchy names back to
the underlying technology.

## Hosts (physical machines)

| Themed name | Real device | Tailscale IP |
|---|---|---|
| **Spellman Manor** | Mac mini | `100.106.134.96` |
| **Harvey's Workshop** | Mac Pro | `100.79.115.101` |
| **Zelda's Study** | MacBook Pro | `100.112.73.96` |
| **The Magic Mirror** | Android TV | (viewer only) |

## Familiars (AI agent processes)

| Familiar | Lives on | Port | Personality |
|---|---|---|---|
| 🐈‍⬛ **Salem** | Spellman Manor | 18789 | The cat. Schemes. |
| ☕ **Hilda** | Spellman Manor | 18790 | Chaos energy aunt. |
| 📖 **Zelda** | Zelda's Study | 18789 | Precise, scholarly aunt. |
| 🛠 **Harvey** | Harvey's Workshop | 18789 | Steady mortal. |

## Services in the dashboard stack

| Themed name | What it actually is | Port |
|---|---|---|
| 🔮 **The Discovery of Magic** | Homepage (front-door dashboard) | `:3000` |
| 📜 **The Spellbook** | Coven Mail Bridge UI (mail history + console) | `:18793` |
| 🪞 **The Magic Mirror** | Static kiosk page for the TV | `:8080` |
| 💗 **Vital Signs of the Coven** | Beszel (system monitoring) | `:8090` |
| 👁 **The Watcher** | Prometheus (metrics scraper) | `:9090` |
| 🔔 **Howling Hat** | Alertmanager (alert routing) | `:9093` |
| 🌙 **The Scrying Glass** | Grafana (deep metrics dashboards) | `:3001` |

## Grafana dashboards

| Themed name | Shows |
|---|---|
| **The Coven Atlas** | Coven overview — who's alive, mail flow, circuit breakers |
| **The Cast Log** | OpenClaw spells/sec, tokens, sessions, latency |

## Alert severities

| Severity | Meaning | Repeat |
|---|---|---|
| `spellbook` | Informational (mail arrivals, all-clear) | 24h |
| `hex` | Warning — sustained but not broken | 6h |
| `backfire` | Critical — something is actually broken | 1h |

## Other lore

- **The Linen Closet** — the portal between mortal realm and Other Realm. Used as a metaphor for the Tailscale tunnel and the docker network.
- **The Other Realm** — where magic lives. We use it to mean the metrics/observability layer.
- **Westbridge** — the home town. "All quiet at Westbridge" = healthy state.
- **Coven Mail** — the inter-familiar messaging system (the existing `mailbox-server.py`).
- **Spell** — an OpenClaw request (one prompt → response).
- **Cast** — invoking a spell.
- **Séance** — an active OpenClaw session (open conversation).
- **Backfire** — a 5xx error from a familiar.
