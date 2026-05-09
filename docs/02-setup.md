# 🔮 Setup walkthrough

For someone who hasn't used Docker before. ~30 minutes.

## What you need

- Mac mini (Spellman Manor) with admin access
- Tailscale already installed and connecting all the Macs
- ~3GB free disk space on the mini
- The bearer tokens for each familiar's gateway (operator scope) and hooks

## Step 1 — Install Docker Desktop on the Mac mini

1. Go to https://www.docker.com/products/docker-desktop/
2. Click **Download for Mac**, choose Apple silicon or Intel as appropriate.
3. Open the `.dmg`, drag the whale to Applications, then open Docker.
4. Click through the prompts. When you see the whale in your menu bar,
   it's ready.

> Docker is just a way to run apps in self-contained "containers" — you
> never edit anything inside them, you just start/stop them.

## Step 2 — Get this folder onto the Mac mini

```sh
git clone <this-repo> ~/spellman-manor
cd ~/spellman-manor
```

(Or however you got it here.)

## Step 3 — Fill in `.env`

```sh
cp .env.example .env
```

Open `.env` in any text editor and fill in real values:

- **The 3 host IPs** — get them from `tailscale status` on the Mac mini.
  Look for the lines for the mini, the Mac Pro, and the MacBook.
- **Gateway tokens** for `SALEM_GATEWAY_TOKEN`, `HILDA_GATEWAY_TOKEN`, etc.
  — these are the **operator-scope** tokens for each familiar's OpenClaw
  diagnostics endpoint. Find them in each familiar's OpenClaw config under
  `gateway.auth.tokens`.
- **Hook tokens** — these are in the registry you already have:
  ```
  Salem  hook: 5d6068713b33683021526d5b47ad44edc232663b8d6f8f40
  Hilda  hook: 5c7d91d8c1a8875bcee11f5cddcaca52c38cd30040b1314a
  Zelda  hook: 458130691ac45112f53d491e47350c92e88d7b07dd24399d
  Harvey hook: 4cd80c8bac6fec2f906830938c393c813f66af0bb8d77743
  ```
- **Mailbox token**: `4b78943f6520f5ec990e10281cad6ff81ace9b4f90435565`
- **`COVEN_MAILBOX_DIR`**: only change this if your home folder isn't
  `/Users/sabrinaryan`. Verify with `ls ~/.openclaw/workspace/coven-mailbox/`.

## Step 4 — Drop per-familiar Prometheus tokens

These are written as plain files (no quotes, no newline) so Prometheus can
read them with `credentials_file:`.

```sh
echo -n "your-salem-operator-token"  > prometheus/tokens/salem.token
echo -n "your-hilda-operator-token"  > prometheus/tokens/hilda.token
echo -n "your-zelda-operator-token"  > prometheus/tokens/zelda.token
echo -n "your-harvey-operator-token" > prometheus/tokens/harvey.token
```

## Step 5 — Start the stack

```sh
./scripts/spellbook.sh up
```

After ~30 seconds the script prints all the URLs. The most important:

- 🔮 http://localhost:3000  — **The Discovery of Magic** (Homepage)
- 📜 http://localhost:18793 — **The Spellbook** (mail + console)
- 🪞 http://localhost:8080  — **The Magic Mirror** (kiosk for TV)

## Step 6 — Set up the other Macs (Mac Pro & MacBook)

On each one, copy `scripts/setup-familiar-host.sh` over and run it:

```sh
./setup-familiar-host.sh spellman-manor.tailXXXX.ts.net
```

(Replace `tailXXXX` with your real tailnet name — find it in `tailscale status`.)

It installs the Beszel agent and a tiny "Claude bridge" that lets familiars
ask each other's Claude Code.

## Step 7 — Add hosts to Beszel

Open http://localhost:8090, click **Add System** for each Mac. Paste the
public key the agent printed during install. Name them `spellman-manor`,
`harveys-workshop`, `zeldas-study`.

## Step 8 — On the Android TV

Install a browser app (Brave / Firefox from the Play Store). Bookmark:

```
http://spellman-manor.tailXXXX.ts.net:8080
```

That's the Magic Mirror page. Pin to the home screen for one-tap access.

## Step 9 — Optional: clean HTTPS URL

```sh
./scripts/tailscale-serve.sh
```

Maps `https://spellman-manor.tailXXXX.ts.net` → Homepage on port 3000.

---

Done. To stop everything: `./scripts/spellbook.sh down`. To update:
`./scripts/spellbook.sh update`.
