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
| 🪟 **The Veil** | `nginx` PWA proxy | `:3030` | PWA-installable wrapper for Homepage |
| 📜 **The Spellbook** | `coven-mail-bridge` | `:18793` | Mail UI + console + Surveillance |
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
| "Heartbeat" | A cron/watchdog `POST /api/{cron,watchdog}/heartbeat` |
| "Stale" | A heartbeat that's older than the threshold (24h cron / 10m watchdog) |
| "Verdict" | The bridge's cheap review of a release: safe / recommended / review / wait |

## The palette: Westbridge Twilight + Dawn

90s celestial Sabrina × Gen Z Y2K. Hot pink `#FF3FA4` is the show's
actual logo color. Twilight (dark) is the default; Dawn (light) is
the toggle.

| Token | Westbridge Twilight (dark) | Westbridge Dawn (light) | Used for |
|---|---|---|---|
| `--ink` | `#1A1B4B` (midnight navy) | `#F4EAFB` (veil) | page background |
| `--hot-pink` | `#FF3FA4` (Sabrina logo) | `#C12B7E` | primary accent / hover glow |
| `--rose` | `#FF6EC7` | `#DD4A95` | secondary pink |
| `--bubblegum` | `#FFB6D5` | `#F296B8` | highlights |
| `--lavender` | `#C8A2DB` (bedroom drapes) | `#7E66B0` | section headings |
| `--gold` | `#E8C547` (spell gold) | `#B8842D` | values + ornaments |
| `--mint` | `#A8F0D0` (Salem's eyes) | `#3D8E76` | success / online indicators |
| `--holo-sky` | `#A8E0FF` | `#5A8FBC` | iridescent gradient stop |
| `--ember` | `#FF8E8E` | `#C8485E` | danger / open circuits |
| `--text` | `#F4EAFB` (veil) | `#2A1535` | primary copy |

Fonts:
- **Cinzel Decorative** (400 / 700 / 900) — chapter-heading section
  titles + card titles. Roman inscriptional, properly witchy.
- **Sacramento** (cursive) — the personal greeting "Welcome home,
  Sabrina" only, with iridescent gradient text fill that drifts.
- **Quicksand** (400 / 500 / 600 / 700) — body copy. Rounded, friendly,
  90s-coded.
- **JetBrains Mono** (300 / 400 / 500) — technical subtitles in
  lowercase letter-spaced.

## Decorative SVG assets

Sprinkled through the UI in `homepage/images/` and via inline data
URIs in the Spellbook UI. All shape via `currentColor` so CSS controls
the fill.

| File | Use |
|---|---|
| `sparkle.svg` | 4-point pinched-diamond (the iconic Sabrina/MSN twinkle) — section heading prefix, framing the greeting |
| `twinkle.svg` | Smaller variant — sprinkled across page edges, appears on bookmark hover |
| `crescent.svg` | Waxing crescent moon — Magic Mirror footer ornament |
| `star.svg` | Chunky 5-point sticker star |
| `butterfly.svg` | Y2K morpho silhouette |
| `jewel.svg` | Diamond / rhombus accent |
| `app-icon-spellbook.svg` | 512×512 — gold sparkle on pink/violet/midnight gradient |
| `app-icon-mirror.svg` | 512×512 — gold crescent on midnight + nebula |
| `app-icon-spellman.svg` | 512×512 — crescent + sparkle composition for Homepage PWA |

## PWA-installable apps (iOS / Android home-screen)

Three apps install with their own themed icons. See
[`14-remote-access.md`](14-remote-access.md).

| App | URL | Icon |
|---|---|---|
| **Spellman Manor** | `:3030` (via The Veil) | crescent + sparkle on pink/violet/midnight |
| **The Spellbook** | `:18793/` | gold sparkle on pink/violet |
| **The Magic Mirror** | `:8080` | gold crescent on midnight |
