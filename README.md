# 🌙 The Discovery of Magic

A 90s celestial witchy dashboard for the Spellman household: 4 ClawBots
(*hilda*, *zelda*, *salem*, *harvey*), three Macs, and an Android TV magic
mirror — all reachable over Tailscale.

> *"The book contains everything you need to know about being a witch."*

---

## The household

| Host | Role | Hardware |
|---|---|---|
| **Spellman Manor** | The hub — runs the whole dashboard | Mac mini |
| **Hilda** | ClawBot — chaos energy | Jetson Orin Nano |
| **Zelda** | ClawBot — precise, cold | Jetson Orin Nano |
| **Salem** | ClawBot — mischievous | Jetson Orin Nano |
| **Harvey** | ClawBot — steady | Jetson Orin Nano |
| **Drell** | Council muscle | Mac Pro |
| **Sabrina** | The mortal-realm laptop | MacBook Pro |
| **The Magic Mirror** | Scrying surface | Android TV |
| **Other Realm** | Primary storage | SSD |
| **Katrina** | Backups (keep your enemies close) | Backup drive |

---

## The stack

- **Homepage** — themed front door, one tile per ClawBot with live OpenClaw stats
- **Beszel** — *Vital Signs of the Coven*: lightweight CPU/RAM/disk per host
- **Prometheus + Grafana** — *Other Realm Surveillance* (Jetson GPU/temps) and
  *The Cast Log* (OpenClaw spells per second, latency, sessions)

Everything reached over the tailnet — nothing exposed to the mortal realm.

---

## Setup walkthrough

### 1. On Spellman Manor (the Mac mini)

**Install Docker Desktop.** Download from https://www.docker.com/products/docker-desktop/,
double-click the `.dmg`, drag the whale to Applications, open it. The whale
appears in your menu bar when it's awake.

**Install Tailscale** if you haven't: https://tailscale.com/download

**Get this folder onto Spellman Manor.** Either `git clone` it or copy.

**Set your gateway tokens and tailnet hostnames:**

```sh
cp .env.example .env
# edit .env — fill in real tokens and the tailnet names you see in `tailscale status`
```

For each ClawBot, drop its bearer token in `prometheus/tokens/` as a single
line (no trailing newline):

```sh
echo -n "your-hilda-token"  > prometheus/tokens/hilda.token
echo -n "your-zelda-token"  > prometheus/tokens/zelda.token
echo -n "your-salem-token"  > prometheus/tokens/salem.token
echo -n "your-harvey-token" > prometheus/tokens/harvey.token
```

**Open the linen closet** (start the stack):

```sh
docker compose up -d
```

Wait ~30 seconds, then visit:

- 🔮 **The Discovery of Magic** (Homepage) — http://localhost:3000
- 💗 **Vital Signs** (Beszel) — http://localhost:8090
- 👁 **Other Realm Surveillance + Cast Log** (Grafana) — http://localhost:3001 *(login: admin / admin, change it)*
- 🛠 **Prometheus** — http://localhost:9090 *(only for debugging)*

### 2. On each ClawBot (hilda, zelda, salem, harvey)

Confirm OpenClaw's Prometheus diagnostics plugin is enabled in the gateway
config (`"diagnostics-prometheus": { "enabled": true }`), and grab the
operator-scope bearer token.

Then SSH in and install the Beszel agent + Jetson exporter:

```sh
# 1. Beszel agent (system stats)
curl -fsSL https://raw.githubusercontent.com/henrygd/beszel/main/supplemental/scripts/install-agent.sh | bash
# When prompted, enter:  http://spellman-manor.tailXXXX.ts.net:8090

# 2. Jetson stats (GPU, temps, power) for the Other Realm Surveillance dashboard
sudo pip3 install -U jetson-stats
sudo systemctl enable --now jtop.service
docker run -d --restart unless-stopped --name jetson-exporter \
  --device /dev/i2c-0 --device /dev/i2c-1 -p 9100:9100 \
  rbonghi/jetson_stats:prometheus-exporter
```

(If a ClawBot doesn't have Docker: `curl -fsSL https://get.docker.com | sh`.)

### 3. Add each ClawBot in Beszel

Open Vital Signs (http://spellman-manor.tailXXXX.ts.net:8090), click
**Add System**, paste the public key the agent printed, and name them
`hilda`, `zelda`, `salem`, `harvey`. Repeat for `drell` and `sabrina` if you
want them in the coven view.

### 4. On the Magic Mirror (Android TV)

Install a browser (Brave / Firefox) from the Play Store. Bookmark
`http://spellman-manor.tailXXXX.ts.net:3000`. Open it whenever you want to
gaze into the Other Realm.

### 5. Optional: clean URL via Tailscale Serve

Skip the port numbers — get `https://spellman-manor.tailXXXX.ts.net`:

```sh
./scripts/tailscale-serve.sh
```

---

## Daily incantations

A small helper script wraps the common Docker commands:

```sh
./scripts/spellbook.sh up        # start everything
./scripts/spellbook.sh down      # stop everything
./scripts/spellbook.sh restart   # restart
./scripts/spellbook.sh update    # pull new versions, restart
./scripts/spellbook.sh logs      # tail logs
./scripts/spellbook.sh status    # what's running
./scripts/spellbook.sh peer      # health-check all 4 ClawBots
```

---

## Customizing the magic

- **Theme/colors** → `homepage/custom.css` (the witchy CSS lives here)
- **Tile layout** → `homepage/services.yaml`
- **Widgets** (moon, weather, etc.) → `homepage/widgets.yaml`
- **Add/remove a ClawBot from scraping** → `prometheus/prometheus.yml`
- **Grafana dashboards** — `grafana/dashboards/*.json` are auto-imported

## Troubleshooting

- *"Can't reach a ClawBot"* — `tailscale status` on Spellman Manor; make sure
  the tailnet name in `.env` matches.
- *"Prometheus shows a target as DOWN"* — token wrong, or diagnostics plugin
  not enabled. Test:
  `curl -H "Authorization: Bearer $TOKEN" http://hilda.tailXXXX.ts.net:18789/api/diagnostics/prometheus`
- *"Beszel says agent offline"* — on the ClawBot: `systemctl status beszel-agent`.
- *Tile widgets blank* — the OpenClaw `/api/diagnostics/summary` field names may
  differ in your version; tweak `mappings:` in `homepage/services.yaml`.
