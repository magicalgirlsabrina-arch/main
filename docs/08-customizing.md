# 🎨 Customizing — make it yours
*`.env` · `homepage/*.yaml` · `prometheus/prometheus.yml` · CSS variables*

## Adding a new familiar

Say you spin up a 5th familiar named **Drell** on a new Mac.

1. **Add credentials to `.env`:**
   ```
   DRELL_HOST=100.x.y.z
   DRELL_GATEWAY_PORT=18789
   DRELL_GATEWAY_TOKEN=...
   DRELL_HOOK_TOKEN=...
   ```

2. **Add a Prometheus scrape job** (`prometheus/prometheus.yml`):
   ```yaml
   - job_name: drell
     metrics_path: /api/diagnostics/prometheus
     authorization:
       type: Bearer
       credentials_file: /etc/prometheus/tokens/drell.token
     static_configs:
       - targets: ['100.x.y.z:18789']
         labels: { familiar: drell, host: drells-tower, role: council }
   ```
   And drop the token: `echo -n "..." > prometheus/tokens/drell.token`

3. **Add a tile** (`homepage/services.yaml`) — copy any existing familiar's
   block and rename. Pick an icon from https://pictogrammers.com/library/mdi/.

4. **Add to the bridge** — edit `coven-mail-bridge/server.py`:
   ```python
   FAMILIARS = {
       ...,
       "drell":  {"host": os.environ.get("DRELL_HOST", ""),
                  "port": os.environ.get("DRELL_GATEWAY_PORT", "18789"),
                  "token": os.environ.get("DRELL_HOOK_TOKEN", "")},
   }
   ```
   And in the bridge's HTML, add a `<select>` option.

5. **Add to docker-compose.yml** in the `coven-mail` env block.

6. Rebuild + restart: `docker compose up -d --build coven-mail`.

## Changing the color palette

All colors live in CSS variables at the top of two files:

- `homepage/custom.css` — Homepage theme
- `magic-mirror/style.css` — Android TV kiosk

Both define:
```css
:root {
  --pink:  #FF1493;   /* Sabrina pink */
  --hot:   #FF6EC7;   /* Hot pink */
  --lav:   #B19CD9;   /* Lavender */
  --gold:  #FFD700;
  --cream: #F5E6FF;
  ...
}
```

Change those, and the rest of the dashboard follows. Try a different palette:
- **Salem-noir:** swap pink for `#0A0A0A` and gold for `#1F1F1F` for a black-cat vibe
- **Other Realm green:** swap pink for `#39FF14` and lavender for `#76FF7A`
- **Sunset Witch:** swap to coral/peach gradients

## Adding a new dashboard tile that isn't a familiar

`homepage/services.yaml` — pick any section and add an entry:

```yaml
- The Other Realm:
    - My New Tool:
        href: http://localhost:1234
        description: 🌟 Whatever this is
        icon: mdi-book-music-#ff6ec7   # mdi icon + color suffix
        widget:
          type: customapi
          url: http://my-service:1234/status
          mappings:
            - field: someField
              label: My Label
```

## Renaming things

The themed names are decorative — the underlying technology doesn't care.
Search-and-replace any of these:
- "Spellman Manor", "Harvey's Workshop", "Zelda's Study"
- "The Discovery of Magic", "The Spellbook", "The Magic Mirror", etc.

You don't have to match the show — make it yours. The architecture
(3 hosts, 4 familiars, 1 mailbox) is what matters.

## Changing how often things update

| What | Where | Default |
|---|---|---|
| Prometheus scrape | `prometheus/prometheus.yml` `scrape_interval:` | 30s |
| Prometheus retention | `docker-compose.yml` `--storage.tsdb.retention.time=` | 30d |
| Homepage widget refresh | client-side, ~10s | — |
| Magic Mirror refresh | `magic-mirror/app.js` `setInterval(refreshAll, 10000)` | 10s |
| Spellbook history refresh | `coven-mail-bridge/server.py` HTML `setInterval(loadHistory, 5000)` | 5s |
| Alert evaluation | `prometheus/prometheus.yml` `evaluation_interval:` | 30s |

## Adding your own background image

Edit `homepage/custom.css`:

```css
body::before {
  background: url('https://your-image-url.jpg') center/cover no-repeat,
              linear-gradient(180deg, var(--midnight), var(--velvet));
}
```

For local images, drop them in `homepage/images/` and reference as
`/api/images/yours.jpg` (Homepage serves the `images/` folder automatically).
