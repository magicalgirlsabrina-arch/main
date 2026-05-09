# 🔮 Setup walkthrough
*docker desktop + docker compose · ~30 minutes*

For someone who hasn't used Docker before.

> **Coven topology check** — before anything else, confirm what you're
> setting up: **3 physical Macs running 4 OpenClaw familiar processes.**
> Salem (`:18789`) AND Hilda (`:18790`) both run on the Mac mini
> (Spellman Manor) on different ports — they share the host. The Mac
> Pro runs Harvey, the MacBook Pro runs Zelda. The Android TV doesn't
> host any familiar; it's just a viewer for the Magic Mirror page.

## What you need

- Mac mini (Spellman Manor) with admin access. **All 3 Macs are Apple Silicon** — fine for Docker, see [§ Apple Silicon notes](#apple-silicon-notes) below.
- Tailscale already installed and connecting all the Macs
- ~3GB free disk space on the mini
- The bearer tokens for each familiar's gateway + hooks (you already have these — see [`docs/00-glossary.md`](00-glossary.md))

## Step 1 — Install Docker Desktop on the Mac mini

> **Skip `brew install --cask docker`.** It needs `sudo mkdir
> /usr/local/cli-plugins` which fails silently on managed Macs and
> non-TTY shells. Use the .dmg directly.

1. Download from https://docs.docker.com/desktop/install/mac-install/ — pick **Apple Silicon** (all 3 Macs are M-series).
2. Open the `.dmg`, drag **Docker.app** to **Applications**, then open Docker.app from Applications.
3. Click through the prompts. When the whale appears in your menu bar, Docker is running.

### Step 1.5 — Get the Docker CLI on your PATH

Docker Desktop installs the CLI at `/Applications/Docker.app/Contents/Resources/bin`, but that directory isn't on your shell's PATH by default. Without it you'll see `error getting credentials - exec: "docker-credential-desktop"`.

Append to your shell rc and reload:

```sh
echo 'export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

(`spellbook.sh` already auto-detects this path so the day-to-day commands work even if you skip this step. But you'll want it for direct `docker` usage from your shell.)

## Step 2 — Get the code onto the mini

```sh
cd ~
git clone -b claude/openclaw-dashboard-research-GFWWK <your-repo-url> spellman-manor
cd spellman-manor
```

(Or `git pull` if already cloned.)

## Step 3 — Find your tailnet name

You'll need it for the other Macs. From any host already on the tailnet:

```sh
./scripts/spellbook.sh tailnet
# → tail4cb40.ts.net
```

That's the suffix. Your hosts will be `spellman-manor.tail4cb40.ts.net`, etc.

## Step 4 — Fill in `.env`

```sh
cp .env.example .env
nano .env   # or `code .env` if you have VS Code's CLI installed
            # avoid TextEdit — it formats as rich text by default
```

Fill in:

- **The 3 host IPs** — already templated; confirm with `tailscale status`.
- **Mailbox token + 4 hook tokens** — these are in your existing OpenClaw registry config; the values are constants per familiar.
- **The 4 gateway tokens** — `SALEM_GATEWAY_TOKEN`, `HILDA_GATEWAY_TOKEN`, `ZELDA_GATEWAY_TOKEN`, `HARVEY_GATEWAY_TOKEN`. These are *not* the same as hook tokens. See [Step 4a](#step-4a--grab-the-gateway-tokens).
- **`COVEN_MAILBOX_DIR`** — only change if your home isn't `/Users/sabrinaryan`. Verify with `ls ~/.openclaw/workspace/coven-mailbox/`.

### Step 4a — Grab the gateway tokens

Each familiar's gateway token lives at `gateway.auth.token` (singular!) in its OpenClaw config. There are two ways to retrieve them:

**Option A — run on each host directly (preferred):**

For Salem + Hilda (already on Spellman Manor):
```sh
./scripts/grab-gateway-token.sh salem
./scripts/grab-gateway-token.sh hilda
```

For Zelda + Harvey (on the other two Macs), enable Remote Login first:
- macOS Settings → General → **Sharing** → enable **Remote Login**
- Or in Terminal: `sudo systemsetup -setremotelogin on`

Then SSH in and run:
```sh
ssh zeldas-study.<your-tailnet>  "$(cat scripts/grab-gateway-token.sh) zelda"
ssh harveys-workshop.<your-tailnet> "$(cat scripts/grab-gateway-token.sh) harvey"
```

**Option B — print them at the bottom of the host setup script:**

When you run `./scripts/setup-familiar-host.sh` on each Mac (Step 7), it prints that host's gateway token at the end. Copy it back to `.env` on the mini.

## Step 5 — Start the stack

```sh
./scripts/spellbook.sh up
```

This now also auto-syncs the gateway tokens from `.env` into `prometheus/tokens/*.token`, so you don't have to maintain two copies. Update `.env`, run `up`, done.

You should see the seven services start, then a list of URLs. Open **http://localhost:3000** to confirm the dashboard is live.

## Step 6 — Sanity check

```sh
./scripts/spellbook.sh status     # all 7 containers should say "Up"
./scripts/spellbook.sh peer       # pings the 4 familiars over Tailscale
```

## Step 7 — Set up the other Macs

On each of the other two Macs (Mac Pro and MacBook Pro):

```sh
# Copy the script over from the mini (replace <tailnet> with what Step 3 printed)
scp ~/spellman-manor/scripts/setup-familiar-host.sh harveys-workshop.<tailnet>:~/
ssh harveys-workshop.<tailnet>
./setup-familiar-host.sh spellman-manor.<tailnet>
```

The script installs the Beszel agent (sends system metrics back to the mini) and prints that host's gateway token at the end. Copy it into `.env` on the mini, then `./scripts/spellbook.sh up` to re-sync.

Repeat for `zeldas-study`.

## Step 8 — Distribute the Familiar's Handbook

Once everything's running, send the new handbook to all four familiars:

```sh
./scripts/distribute-handbook.sh
```

This drops a coven-mail in each familiar's inbox pointing at `http://100.106.134.96:18793/api/handbook` so they can self-serve the manual. See [`docs/13-familiar-handbook.md`](13-familiar-handbook.md).

## Step 9 — Android TV bookmark (optional)

Install Brave or Firefox from the Play Store. Bookmark:
```
http://spellman-manor.<tailnet>:8080
```

That's the Magic Mirror. Pin to home screen for one-tap access.

## Step 10 — Optional: clean HTTPS URL

```sh
./scripts/tailscale-serve.sh
```

Maps `https://spellman-manor.<tailnet>` → Homepage on port 3000.

---

## Apple Silicon notes

All three Macs are Apple Silicon (M1/M2/M3 family). Docker Desktop on Apple Silicon Just Works for nearly every image — the ones in this stack (Homepage, Beszel, Prometheus, Alertmanager, Grafana, nginx) all publish `linux/arm64` builds so they run natively without emulation.

If you ever pull an x86-only image and see `exec format error`:

1. Make sure Docker Desktop has Rosetta enabled: Settings → General → "Use Rosetta for x86_64/amd64 emulation."
2. Pin the platform in `docker-compose.yml`: `platform: linux/amd64`.

But everything in this repo is multi-arch — you should never hit it.

---

To stop everything: `./scripts/spellbook.sh down`. To update:
`./scripts/spellbook.sh update`. Full troubleshooting:
[`docs/04-troubleshooting.md`](04-troubleshooting.md).
