// 🪞 The Magic Mirror — polls the Coven Mail Bridge + Alertmanager.
//
// The Bridge runs on the Mac mini at port 18793. From an Android TV
// browser on the tailnet, hit the mini directly. Update BRIDGE_URL below
// to your tailnet name (or leave it as same-origin if you proxy via nginx).

const BRIDGE_URL       = ''; // empty = same origin (when reverse-proxied), else 'http://spellman-manor.tailXXXX.ts.net:18793'
const ALERTMANAGER_URL = ''; // same idea, or 'http://spellman-manor.tailXXXX.ts.net:9093'

const FAMILIARS = ['salem', 'hilda', 'zelda', 'harvey'];

// ── Clock ──────────────────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  document.getElementById('datestamp').textContent =
    now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
}
tickClock();
setInterval(tickClock, 1000);

// ── Coven peer-ping ────────────────────────────────────────────────────
async function refreshCoven() {
  try {
    const r = await fetch(`${BRIDGE_URL}/api/peer-ping`);
    const d = await r.json();
    let allOnline = true;
    for (const name of FAMILIARS) {
      const card = document.querySelector(`.familiar[data-name="${name}"]`);
      const ping = d[name] || {};
      if (ping.ok) {
        card.classList.remove('offline');
        card.classList.add('online');
        card.querySelector('.status').textContent = `✨ alive · ${ping.latency_ms}ms`;
      } else {
        card.classList.remove('online');
        card.classList.add('offline');
        card.querySelector('.status').textContent = `🌑 vanished`;
        allOnline = false;
      }
    }
  } catch (e) {
    FAMILIARS.forEach(n => {
      const card = document.querySelector(`.familiar[data-name="${n}"]`);
      card.querySelector('.status').textContent = '🌫 portal unclear';
    });
  }
}

// ── Mail summary + recent ──────────────────────────────────────────────
async function refreshMail() {
  try {
    const [unread, msgs] = await Promise.all([
      fetch(`${BRIDGE_URL}/api/unread-count`).then(r => r.json()),
      fetch(`${BRIDGE_URL}/api/messages?limit=4`).then(r => r.json()),
    ]);
    document.getElementById('mail-summary').textContent = unread.unread || 0;
    const recent = msgs.messages || [];
    document.getElementById('mail-recent').innerHTML = recent.slice(0, 3).map(m => `
      <div class="item">
        <span class="from">${escapeHtml(m.from || '?')}</span> ·
        ${escapeHtml((m.subject || m.body || '').slice(0, 50))}
      </div>
    `).join('') || '<div class="item">no messages yet</div>';
  } catch (e) {
    document.getElementById('mail-summary').textContent = '?';
  }
}

// ── Active spells (sum sessions across familiars via OpenClaw metrics) ─
//   We don't query OpenClaw directly here — too many bearer-token roundtrips.
//   Instead we approximate from the bridge's circuit state for now.
//   Future: add a /api/coven-summary endpoint to the bridge.
async function refreshActiveSpells() {
  // Placeholder: use the count of online familiars × 1 as a proxy.
  const count = document.querySelectorAll('.familiar.online').length;
  document.getElementById('active-sessions').textContent = count;
}

// ── Alerts (pull from Alertmanager) ────────────────────────────────────
async function refreshAlerts() {
  if (!ALERTMANAGER_URL) return;
  try {
    const r = await fetch(`${ALERTMANAGER_URL}/api/v2/alerts?active=true&silenced=false&inhibited=false`);
    const alerts = await r.json();
    const el = document.getElementById('alert-list');
    if (!alerts.length) {
      el.innerHTML = '<div class="all-clear">🌙 Westbridge calm</div>';
      return;
    }
    el.innerHTML = alerts.slice(0, 4).map(a => `
      <div class="alert">
        ${escapeHtml(a.annotations.summary || a.labels.alertname)}
      </div>
    `).join('');
  } catch (e) {
    // silent
  }
}

function escapeHtml(s) {
  return (s || '').replace(/[<>&]/g, c => ({ '<':'&lt;', '>':'&gt;', '&':'&amp;' })[c]);
}

// ── Schedule ───────────────────────────────────────────────────────────
async function refreshAll() {
  await refreshCoven();
  await refreshMail();
  await refreshActiveSpells();
  await refreshAlerts();
}
refreshAll();
setInterval(refreshAll, 10000);
