# 🪞 The Magic Mirror — TV kiosk view
*nginx static page · `:8080` · android tv viewer*

A stripped-down, big-text version of the dashboard tuned for ~10ft viewing
on the Android TV in the living room. Refreshes every 10 seconds.

## What it shows

- **Big clock + date** at the top
- **4 familiar cards** — green border = online, pink + pulsing = offline
- **Coven Mail summary** — unread count, top 3 recent senders
- **Active Spells** — proxy of how many sessions are open across the coven
- **Howling Hat** — currently firing alerts (or "🌙 Westbridge calm")

It's pure HTML/CSS/JS — no framework, ~7KB total. Lives at:

```
http://spellman-manor.tailXXXX.ts.net:8080
```

## Why a separate page (not just Homepage on the TV)

Homepage looks great on a desktop but its tile UI is dense for a TV.
The Magic Mirror trades clickability for legibility:
- ~96px clock (Cinzel Decorative)
- 56px familiar emojis with status pulses
- 96px alert/mail counters in gold
- Bigger gaps, fewer panels

You can still open Homepage in the TV's browser if you want to click
through — they coexist on different ports.

## Setting it up on the Android TV

1. Install a browser app from the Play Store. **Brave** and **Firefox** both
   work; some smart TVs ship with a "TV browser" that's also fine.
2. Open `http://spellman-manor.tailXXXX.ts.net:8080`.
3. **Pin to home screen / make it a shortcut** so you can launch it
   in one click without typing the URL each time.
4. Optional: turn off the TV's screen saver / sleep so it stays on.

## When the TV is doing other things

You said you want to use the TV for other things too — that's fine.
The dashboard URL just sits as a bookmark; open it when you want to
glance, close it when you want Netflix. No background process.

If you ever DO want it as a permanent display:
- Most Android TV browsers have a fullscreen / kiosk mode (F11 or menu).
- Set the TV to "always on" or set screen-off timeout to never.
- Some Android TVs support "auto-launch app on boot" — set it to your
  browser pointing at the Magic Mirror URL.

## Customizing the Magic Mirror

Edit `magic-mirror/index.html` for layout, `style.css` for colors, `app.js`
for behavior. The whole thing is ~250 lines; reading it top-to-bottom is
the fastest way to understand what's happening.

To add a new card:

```html
<!-- in index.html, inside <section class="cards"> -->
<div class="card">
  <h2>📚 BOOK OF SHADOWS</h2>
  <div id="my-data" class="big-number">…</div>
  <div class="card-sub">whatever this is</div>
</div>
```

```js
// in app.js, in refreshAll() or a new function:
async function refreshBookOfShadows() {
  const r = await fetch(`${BRIDGE_URL}/api/your-endpoint`);
  const d = await r.json();
  document.getElementById('my-data').textContent = d.value;
}
```

```css
/* You don't need to add CSS — `.card` styling already applies. */
```

Then `docker compose restart magic-mirror` (nginx reads files on each request,
so usually a hard-refresh of the browser is enough).

## Auto-rotating multiple views

If you want the Magic Mirror to cycle between 2-3 different views (e.g.
"Coven status" → "Daily mail summary" → "Now playing on Salem"), the
simplest approach is in `app.js`:

```js
const VIEWS = ['coven', 'mail', 'now-playing'];
let viewIdx = 0;

function showView(v) {
  document.querySelectorAll('.view').forEach(el => el.style.display = 'none');
  document.getElementById('view-' + v).style.display = 'block';
}
setInterval(() => {
  showView(VIEWS[viewIdx]);
  viewIdx = (viewIdx + 1) % VIEWS.length;
}, 30000);  // rotate every 30s
```

And wrap each section in `<div class="view" id="view-coven">…</div>`.

## CORS

The Magic Mirror is served from `:8080` (nginx) but talks to the bridge at
`:18793` and Alertmanager at `:9093`. The bridge already sends
`Access-Control-Allow-Origin: *` on every response, so cross-origin works
out of the box. If you fork the bridge and remove that header, the Magic
Mirror will silently fail to fetch.
