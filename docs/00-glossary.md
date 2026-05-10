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

90s celestial Sabrina × Gen Z Y2K. Hot pink `#FF1493` is the OG show
saturation, electric cyan `#5BE0FF` is the Y2K stop. Twilight (dark)
is the default; Dawn (light) is a peachy-pink-cream second mode that
flips dramatically on the toggle.

| Token | Westbridge Twilight (dark) | Westbridge Dawn (light) | Used for |
|---|---|---|---|
| `--ink` | `#0F0524` (deep midnight) | `#FFE4F1` (peachy cream) | page background |
| `--hot-pink` | `#FF1493` (OG Sabrina) | `#C2185B` | primary accent / hover glow |
| `--rose` | `#FF80C8` | `#E91E63` | secondary pink |
| `--bubblegum` | `#FFB3D9` | `#F48FB1` | highlights |
| `--lavender` | `#B19CD9` | `#7B2FBE` (deep electric purple) | section headings, icons |
| `--gold` | `#FFD700` (brightest) | `#B8860B` (dark goldenrod) | values + ornaments |
| `--mint` | `#5FFFE6` (Salem's eyes) | `#2E7D5C` | success / online |
| `--cyan` | `#5BE0FF` (Y2K electric) | `#0288D1` | iridescent gradient stop |
| `--ember` | `#FF6B6B` | `#C62828` | danger / open circuits |
| `--text` | `#FFF0F8` | `#2A0D35` (near-black aubergine) | primary copy |

Fonts:
- **Pacifico** (cursive, 400) — the personal greeting "Welcome home,
  Sabrina" only. Closest commercial match to the actual Sabrina the
  Teenage Witch logo: chunky, bouncy, connected letterforms with
  exaggerated swashes. Filled with the iridescent gradient that drifts
  through pink → lavender → cyan → gold every 8 seconds.
- **Cinzel Decorative** (400 / 700 / 900) — chapter-heading section
  titles + card titles. Roman inscriptional with flourishes.
- **Quicksand** (400 / 500 / 600 / 700) — body copy. Rounded,
  friendly, 90s-coded.
- **JetBrains Mono** (300 / 400 / 500) — technical subtitles in
  lowercase letter-spaced.

### Where each mode looks dramatically different

| Element | Twilight (dark) | Dawn (light) |
|---|---|---|
| Background | midnight purple with pink/lavender/cyan nebula washes + 18-star drifting starfield + 6 floating SVG sparkles | peachy pink cream with subtle pink/purple/gold radial accents, no starfield (it's invisible on light), softer sparkles |
| Glass cards | translucent dark glass, hot-pink border-glow, iridescent shimmer on hover | translucent white glass, deep-pink border-glow on hover |
| Section titles | bubblegum pink with hot-pink glow text-shadow | hot-pink (deeper #C2185B) — no glow, sits cleanly on the cream bg |
| Greeting | iridescent rainbow gradient text fill, drop-shadowed in pink + gold | same gradient (works on both modes via background-clip text) |
| Crescent moon corner | gold, drifting at 14s loop | gold, drifting at 14s loop |

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
