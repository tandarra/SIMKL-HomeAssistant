/*!
 * SIMKL Hub card + sidebar panel (no dependencies).
 * Served by the simkl_hub integration; loaded automatically on all dashboards.
 *   type: custom:simkl-hub-card
 *   optional: default_tab: calendar|upnext|watching|plan|done|trending|search|stats
 *             players: [{ name: "Living room", entity: remote.living_room_tv }]
 */
(() => {
  const POSTER = 'https://simkl.in/posters/';
  const CSS = `
:host{display:block;--bg:#0b0d14;--card:rgba(255,255,255,.05);--line:rgba(255,255,255,.09);--text:#eceff8;--mute:#8d96b0;--dim:#5b6480;--accent:#ff4d6d;--ok:#34d399;--warn:#fbbf24;--blue:#60a5fa;--amber:#f59e0b;
color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
*{box-sizing:border-box}
.wrap{background:radial-gradient(1200px 500px at 0 -10%,rgba(255,77,109,.14),transparent 60%),var(--bg);border-radius:20px;padding:18px;min-height:420px}
.hd{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.hd h2{margin:0;font-size:22px;letter-spacing:-.01em}.sub{color:var(--mute);font-size:12px}.sp{flex:1}
button{font:inherit;color:var(--text);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:7px 13px;cursor:pointer}
button:hover{border-color:var(--accent)}button.pri{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
button.sm{padding:5px 11px;font-size:12px}
.tabs,.seg{display:flex;gap:6px;flex-wrap:wrap}.tabs{margin-bottom:14px}
.tabs button,.seg button{border-radius:999px;padding:6px 14px;font-size:13px;color:var(--mute)}
.tabs button.on,.seg button.on{color:#fff;background:rgba(255,77,109,.25);border-color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:14px}
.it{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;cursor:pointer;transition:transform .12s,border-color .12s}
.it:hover{transform:translateY(-2px);border-color:var(--accent)}
.it img{width:100%;aspect-ratio:2/3;object-fit:cover;background:#171a26;display:block}
.it .b{padding:9px 10px 11px;display:flex;flex-direction:column;gap:3px}
.t{font-size:13px;font-weight:600;line-height:1.25}.m{font-size:11px;color:var(--mute)}
.bar{height:4px;border-radius:4px;background:rgba(255,255,255,.1);overflow:hidden;margin-top:4px}.bar i{display:block;height:100%;background:var(--accent)}
.nx{font-size:11px;color:var(--ok)}
.empty{color:var(--mute);padding:30px 0;text-align:center}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}
.st{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}.st b{font-size:28px;display:block}.st span{color:var(--mute);font-size:12px}
.box{max-width:480px;margin:30px auto;text-align:center;display:flex;flex-direction:column;gap:14px;align-items:center;color:var(--mute)}
a{color:var(--accent)}.err{color:var(--warn);font-size:12px;margin-top:10px}
/* calendar */
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}.ctl h3{margin:0 6px;font-size:18px;min-width:150px}
.cal{display:grid;gap:14px;grid-template-columns:minmax(0,1fr)}
@media(min-width:1000px){.cal.side{grid-template-columns:minmax(0,1fr) 330px}}
.mg{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));border:1px solid var(--line);border-radius:14px;overflow:hidden}
.dow{padding:6px 8px;font-size:11px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em;background:rgba(255,255,255,.03);border-bottom:1px solid var(--line)}
.day{min-height:104px;padding:5px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);cursor:pointer;display:flex;flex-direction:column;gap:3px;overflow:hidden}
.day:nth-child(7n){border-right:0}.day:hover{background:rgba(255,255,255,.04)}
.day.out{opacity:.4}.day.sel{background:rgba(255,77,109,.12);box-shadow:inset 0 0 0 1px var(--accent)}
.day .n{font-size:12px;color:var(--mute);align-self:flex-end;width:22px;height:22px;display:grid;place-items:center;border-radius:50%}
.day.today .n{background:var(--accent);color:#fff;font-weight:700}
.chip{font-size:11px;line-height:1.2;padding:2px 5px;border-radius:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:rgba(96,165,250,.18);color:#bcd7ff;border-left:3px solid var(--blue)}
.chip.mine{background:rgba(255,77,109,.2);color:#ffd0d8;border-left-color:var(--accent)}
.chip.movie{background:rgba(245,158,11,.18);color:#ffe2b0;border-left-color:var(--amber)}
.more{font-size:11px;color:var(--mute);padding-left:4px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;max-height:640px;overflow:auto}
.panel h4{margin:0 0 10px;font-size:15px}
.row{display:flex;gap:10px;padding:8px;border-radius:10px;cursor:pointer;align-items:center}.row:hover{background:rgba(255,255,255,.05)}
.row img{width:42px;aspect-ratio:2/3;object-fit:cover;border-radius:6px;background:#171a26}
.row .x{flex:1;min-width:0}.row .t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tag{display:inline-block;font-size:10px;padding:1px 6px;border-radius:999px;margin-left:5px;background:rgba(255,255,255,.1);color:var(--mute);vertical-align:middle}
.tag.mine{background:rgba(255,77,109,.25);color:#ffd0d8}.tag.fin{background:rgba(52,211,153,.2);color:#b6f3d9}
.wk{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}
@media(max-width:700px){.wk{grid-template-columns:1fr}.day{min-height:64px}.chip{font-size:10px}.cal.side{grid-template-columns:1fr}}
.wk .col{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px;min-height:120px;display:flex;flex-direction:column;gap:6px}
.wk .col.today{border-color:var(--accent)}.wk .col h5{margin:0;font-size:12px;color:var(--mute)}
.ag h5{margin:14px 0 6px;font-size:13px;color:var(--mute)}.ag h5.today{color:var(--accent)}
/* detail */
.hero{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:16px}.hero img{width:130px;border-radius:12px;aspect-ratio:2/3;object-fit:cover;background:#171a26}
.hero .tx{flex:1;min-width:240px;display:flex;flex-direction:column;gap:8px}.hero h3{margin:0;font-size:24px}
.ov{font-size:13px;line-height:1.55;color:#c9d0e4;max-width:760px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 12px}.chips button{border-radius:999px;padding:5px 12px;font-size:12px;color:var(--mute)}
.chips button.on{color:#fff;background:rgba(255,77,109,.25);border-color:var(--accent)}
.eps{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:6px;max-height:300px;overflow:auto;margin-bottom:14px}
.ep{display:flex;gap:10px;align-items:baseline;text-align:left;border-radius:10px;padding:8px 12px;width:100%}
.ep.on{border-color:var(--accent);background:rgba(255,77,109,.14)}.ep.nx2{border-color:var(--ok)}
.ep b{min-width:34px;color:var(--mute)}.ep span{flex:1}.ep i{font-style:normal;font-size:11px;color:var(--dim)}
.epd{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:12px;font-size:13px;line-height:1.5}
.acts{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.acts a{text-decoration:none}
.toast{font-size:12px;color:var(--ok);margin-left:6px}.toast.bad{color:var(--warn)}
.rate{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.pill{display:inline-flex;gap:6px;align-items:baseline;font-size:12px;padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.07);border:1px solid var(--line);color:var(--text);text-decoration:none}
.pill b{font-weight:600;color:var(--mute);font-size:11px;letter-spacing:.03em}.pill small{color:var(--dim)}
.pill.rt{background:rgba(250,50,10,.16);border-color:rgba(250,90,50,.4)}.pill.rt b{color:#ffb4a0}
a.pill:hover{border-color:var(--accent)}
.lk{display:inline-flex;align-items:center;gap:6px;text-decoration:none;color:var(--text);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:7px 13px;font-size:13px}
.lk:hover{border-color:var(--accent)}
.trl{position:relative;width:100%;max-width:720px;aspect-ratio:16/9;margin:4px 0 14px;border-radius:14px;overflow:hidden;border:1px solid var(--line);background:#000}
.trl iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.sec{margin:16px 0 6px;font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--dim)}
button.on{color:#fff;background:rgba(255,77,109,.25);border-color:var(--accent)}
button.cf{background:var(--warn);border-color:var(--warn);color:#1b1500;font-weight:600}
.sf{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.sf input{flex:1;min-width:200px;font:inherit;color:var(--text);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:9px 14px}
.sf input:focus{outline:none;border-color:var(--accent)}
.bd{z-index:2;position:absolute;top:8px;right:8px;border-radius:8px;padding:2px 8px;font-size:11px;font-weight:700;backdrop-filter:blur(4px)}
.bd.done{background:rgba(16,185,129,.92);color:#04251a}.bd.now{background:rgba(96,165,250,.92);color:#06172e}.bd.plan{background:rgba(245,158,11,.92);color:#2b1a00}
.it.seen img{opacity:.55}.ep.seen b{color:var(--ok)}.ep.seen span{color:var(--mute)}
.qm{position:absolute;z-index:3;right:8px;top:44px;width:30px;height:30px;padding:0;border-radius:50%;display:grid;place-items:center;font-size:15px;background:rgba(0,0,0,.7);opacity:0;transition:opacity .12s}
.it:hover .qm,.it:focus-within .qm{opacity:1}@media(hover:none){.qm{opacity:.9}}.qm:hover{background:var(--ok);border-color:var(--ok);color:#04251a}
.rk{z-index:2;position:absolute;top:8px;left:8px;background:rgba(0,0,0,.72);backdrop-filter:blur(4px);border-radius:8px;padding:2px 8px;font-size:12px;font-weight:700}
.it{position:relative}
.sub2{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
`;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pad = (n) => String(n).padStart(2, '0');
  const dkey = (d) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  const MON = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const fmtDate = (s) => { if (!s) return ''; const d = new Date(s); return isNaN(d) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); };
  const fmtTime = (s) => { const d = new Date(s); return isNaN(d) ? '' : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }); };
  const ago = (t) => { const m = Math.round((Date.now() / 1000 - t) / 60); return m < 2 ? 'just now' : m < 90 ? m + ' min ago' : Math.round(m / 60) + ' h ago'; };
  const BLANK = 'data:image/svg+xml;utf8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 2 3%22%3E%3Crect width=%222%22 height=%223%22 fill=%22%23171a26%22/%3E%3C/svg%3E';
  const poster = (p) => (p ? POSTER + esc(p) + '_c.webp' : BLANK);
  const epLabel = (x) => (x.s != null && x.e != null ? 'S' + x.s + 'E' + x.e : '');
  const KIND = { show: 'show', anime: 'anime', movie: 'movie' };

  class SimklHubCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this._tab = null; this._st = null; this._sel = null; this._det = null; this._season = null; this._ep = null;
      this._view = 'month'; this._scope = 'major'; this._cursor = new Date(); this._cursor.setDate(1); this._day = dkey(new Date());
      this._cal = {}; this._loading = {}; this._players = null; this._toast = ''; this._toastBad = false; this._wk = null;
      this._pool = {}; this._tr = { kind: 'show', period: 'today', data: {} }; this._q = ''; this._sk = 'all'; this._sr = null; this._serr = ''; this._sbusy = false; this._trailer = false; this._cf = null;
    }
    setConfig(c) { this._cfg = c || {}; if (!this._tab) this._tab = this._cfg.default_tab || 'watching'; this._render(); }
    getCardSize() { return 12; }
    static getStubConfig() { return {}; }
    set hass(h) {
      const first = !this._hass; this._hass = h;
      if (first) { this._loadState(); this._timer = setInterval(() => { if (!this._sel) this._loadState(true); }, 60000); if (!this._narrowSet) { this._narrowSet = true; if (this.clientWidth && this.clientWidth < 640) this._view = 'agenda'; } }
    }
    set narrow(v) { this._narrow = v; }
    set panel(p) { /* HA panel API */ }
    disconnectedCallback() { clearInterval(this._timer); this._timer = null; this._hass = this._hass; }
    connectedCallback() { if (this._hass && !this._timer) this._timer = setInterval(() => { if (!this._sel) this._loadState(true); }, 60000); }

    async _loadState(quiet) {
      try { const s = await this._hass.callWS({ type: 'simkl_hub/state' }); const k = JSON.stringify([s.updated, s.connected, s.ok]); if (quiet && k === this._k) return; this._k = k; this._st = s; this._done = null; }
      catch (e) { this._st = { connected: false, error: String(e.message || e.code || e) }; }
      this._render();
    }
    async _loadMonth(y, m) {
      const key = y + '-' + m + '-' + this._scope;
      if (this._cal[key] || this._loading[key]) return;
      this._loading[key] = true;
      try { this._cal[key] = await this._hass.callWS({ type: 'simkl_hub/calendar', year: y, month: m, scope: this._scope }); } catch (e) { this._cal[key] = []; }
      delete this._loading[key]; this._render();
    }
    _ensureMonths() {
      const base = this._view === 'week' && this._wk ? this._wk : this._cursor;
      const ms = new Set(); const add = (d) => ms.add(d.getFullYear() + '|' + (d.getMonth() + 1));
      const a = new Date(base.getFullYear(), base.getMonth() - 1, 1), c = new Date(base.getFullYear(), base.getMonth(), 1), b = new Date(base.getFullYear(), base.getMonth() + 1, 1);
      add(a); add(c); add(b);
      if (this._view === 'agenda') { const n = new Date(); add(n); add(new Date(n.getFullYear(), n.getMonth() + 1, 1)); }
      ms.forEach((k) => { const [y, m] = k.split('|').map(Number); this._loadMonth(y, m); });
    }
    _byDay() {
      const map = {}; const seen = new Set();
      Object.keys(this._cal).filter((k) => k.endsWith('-' + this._scope)).forEach((k) => (this._cal[k] || []).forEach((it) => {
        const id = it.k + it.id + it.date + it.s + it.e; if (seen.has(id)) return; seen.add(id);
        const d = new Date(it.date); if (isNaN(d)) return; (map[dkey(d)] = map[dkey(d)] || []).push(it);
      }));
      Object.values(map).forEach((a) => a.sort((x, y) => (y.mine - x.mine) || (y.pop - x.pop) || String(x.date).localeCompare(y.date)));
      return map;
    }

    /* ---------- detail ---------- */
    async _open(it, season, episode) {
      this._sel = { kind: it.kind || it.k, id: it.id, title: it.title, poster: it.poster, year: it.year, next: it.next };
      this._det = null; this._trailer = false; this._cf = null; this._ep = episode != null ? episode : (it.next && it.next.episode != null ? it.next.episode : null);
      this._season = season != null ? season : (it.next && it.next.season ? it.next.season : null); this._toast = '';
      this._render();
      if (!this._players) { try { this._players = await this._hass.callWS({ type: 'simkl_hub/players' }); } catch (e) { this._players = []; } }
      try {
        const d = await this._hass.callWS({ type: 'simkl_hub/detail', kind: this._sel.kind, simkl_id: String(this._sel.id) });
        const ss = [...new Set(d.eps.map((e) => e.s))].sort((a, b) => a - b);
        if (this._season == null || !ss.includes(this._season)) { this._season = ss.find((x) => x > 0) || ss[0] || 1; if (episode == null) this._ep = null; }
        this._det = d;
      } catch (e) { this._det = { eps: [], title: this._sel.title, error: true }; }
      this._render();
    }
    _link() {
      const d = this._det || {}, s = this._sel; const t = d.imdb;
      if (!t) return 'stremio:///search?search=' + encodeURIComponent(s.title || '');
      if (s.kind === 'movie') return 'stremio:///detail/movie/' + t + '/' + t;
      return this._ep != null ? 'stremio:///detail/series/' + t + '/' + t + ':' + this._season + ':' + this._ep : 'stremio:///detail/series/' + t;
    }
    _playerList() {
      const cfg = this._cfg.players;
      if (Array.isArray(cfg) && cfg.length) return cfg.map((p) => ({ id: p.entity || p.service, name: p.name || p.entity }));
      return (this._players || []).map((p) => ({ id: p.id, name: p.name }));
    }
    async _send(p) {
      const d = this._det || {};
      try {
        await this._hass.callWS({ type: 'simkl_hub/open', target: p.id, kind: this._sel.kind, imdb: d.imdb || null, season: this._ep != null ? this._season : null, episode: this._ep, title: this._sel.title });
        this._toast = 'Sent to ' + p.name; this._toastBad = false;
      } catch (e) { this._toast = 'Could not send: ' + (e.message || e.code || e); this._toastBad = true; }
      this._render(); setTimeout(() => { this._toast = ''; this._render(); }, 5000);
    }
    _detailView() {
      const it = this._sel, d = this._det;
      if (!d) return '<div class="empty">Loading ' + esc(it.title) + '…</div>';
      const eps = d.eps || [], seasons = [...new Set(eps.map((e) => e.s))].sort((a, b) => a - b);
      const cur = eps.filter((e) => e.s === this._season), sel = this._ep != null ? cur.find((e) => e.e === this._ep) : null;
      const nx = it.next || (((this._st && this._st.watching) || []).find((x) => x.kind + '|' + x.id === it.kind + '|' + it.id) || {}).next || {};
      const sub = [d.year || it.year, (d.genres || []).slice(0, 3).join(', '), d.network, d.runtime ? d.runtime + ' min' : '', d.rating ? '★ ' + d.rating : ''].filter(Boolean).map(esc).join(' · ');
      let h = '<div class="hero"><img src="' + poster(d.poster || it.poster) + '" alt=""><div class="tx"><h3>' + esc(d.title || it.title) + '</h3><div class="m">' + sub + '</div><div class="ov">' + esc(d.overview || (d.error ? 'Could not load details from SIMKL.' : 'No description.')) + '</div></div></div>';
      const stt = this._status(it.kind, it.id), wl = ((this._st && this._st.watching) || []).find((x) => x.kind + '|' + x.id === it.kind + '|' + it.id);
      if (stt) h += '<div class="rate" style="margin-bottom:8px"><span class="pill" style="border-color:' + (stt === 'done' ? 'var(--ok)' : stt === 'now' ? 'var(--blue)' : 'var(--amber)') + '"><b>' + (stt === 'done' ? '✓ WATCHED' : stt === 'now' ? 'WATCHING' : 'PLAN TO WATCH') + '</b>' + (stt === 'now' && wl && wl.total ? ' ' + (wl.watched || 0) + '/' + wl.total + ' eps' : '') + '</span></div>';
      h += this._ratingsRow(d, it);
      if (seasons.length) {
        h += '<div class="chips">' + seasons.map((s) => '<button data-s="' + s + '" class="' + (s === this._season ? 'on' : '') + '">' + (s === 0 ? 'Specials' : 'Season ' + s) + '</button>').join('') + '</div>';
        h += '<div class="eps">' + cur.map((e) => { const isNx = nx.season === e.s && nx.episode === e.e; const seen = stt === 'done' || (stt === 'now' && nx.episode != null && e.s > 0 && (e.s < nx.season || (e.s === nx.season && e.e < nx.episode))); return '<button class="ep ' + (e.e === this._ep ? 'on' : '') + (isNx ? ' nx2' : '') + (seen ? ' seen' : '') + '" data-e="' + e.e + '"><b>' + (seen ? '✓' : e.e) + '</b><span>' + esc(e.t || 'Episode ' + e.e) + '</span><i>' + fmtDate(e.a) + (isNx ? ' · up next' : '') + '</i></button>'; }).join('') + '</div>';
        if (sel && sel.d) h += '<div class="epd"><b>S' + sel.s + 'E' + sel.e + ' · ' + esc(sel.t || '') + '</b><br>' + esc(sel.d) + '</div>';
      }
      const what = this._ep != null ? 'S' + this._season + 'E' + this._ep : (it.kind === 'movie' ? 'movie' : 'series');
      const pl = this._playerList();
      h += '<div class="acts"><a href="' + esc(this._link()) + '"><button class="pri">Open in Stremio here (' + what + ')</button></a>' + pl.map((p, i) => '<button data-p="' + i + '">' + esc(p.name) + '</button>').join('') + (this._toast ? '<span class="toast ' + (this._toastBad ? 'bad' : '') + '">' + esc(this._toast) + '</span>' : '') + '</div>';
      if (!pl.length) h += '<div class="m" style="margin-top:10px;line-height:1.5">No players added yet. Go to <b>Settings → Devices &amp; services → SIMKL Hub → Configure → Players</b>, tick your TVs or phones and name them (for example <i>Nvidia Shield Living Room</i>). Add a TV first with the <b>Android TV Remote</b> or <b>Android Debug Bridge</b> integration.</div>';
      return h + this._manageRow(d, it, what);
    }

    _ratingsRow(d, it) {
      const imdb = d.imdb ? 'https://www.imdb.com/title/' + d.imdb + '/' : '';
      const votes = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(n || ''));
      const p = [];
      if (d.rating) p.push('<span class="pill"><b>SIMKL</b> ★ ' + esc(d.rating) + '</span>');
      if (d.imdb_rating) p.push((imdb ? '<a class="pill" target="_blank" rel="noopener" href="' + imdb + '">' : '<span class="pill">') + '<b>IMDb</b> ★ ' + esc(d.imdb_rating) + (d.imdb_votes ? ' <small>' + votes(d.imdb_votes) + '</small>' : '') + (imdb ? '</a>' : '</span>'));
      if (d.rotten) p.push('<span class="pill rt"><b>Rotten Tomatoes</b> ' + esc(d.rotten) + '</span>');
      if (d.metascore) p.push('<span class="pill"><b>Metacritic</b> ' + esc(d.metascore) + '</span>');
      if (d.certification) p.push('<span class="pill"><b>Rated</b> ' + esc(d.certification) + '</span>');
      if (d.total_episodes && it.kind !== 'movie') p.push('<span class="pill"><b>Episodes</b> ' + esc(d.total_episodes) + '</span>');
      const yt = (d.trailers || [])[0];
      const links = '<div class="acts" style="margin:10px 0 12px">' +
        '<button data-trl="1" class="' + (this._trailer ? 'on' : '') + '">▶ Trailer</button>' +
        (imdb ? '<a class="lk" target="_blank" rel="noopener" href="' + imdb + '">IMDb ↗</a>' : '') +
        (d.imdb ? '<a class="lk" target="_blank" rel="noopener" href="https://www.rottentomatoes.com/search?search=' + encodeURIComponent(d.title || it.title || '') + '">Rotten Tomatoes ↗</a>' : '') +
        '<a class="lk" target="_blank" rel="noopener" href="https://simkl.com/' + (it.kind === 'movie' ? 'movies' : it.kind === 'anime' ? 'anime' : 'tv') + '/' + esc(it.id) + '/">SIMKL ↗</a></div>';
      let trailer = '';
      if (this._trailer) {
        trailer = yt
          ? '<div class="trl"><iframe src="https://www.youtube-nocookie.com/embed/' + esc(yt) + '?autoplay=1&rel=0" referrerpolicy="strict-origin-when-cross-origin" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe></div><div class="acts" style="margin:-6px 0 12px"><a class="lk" target="_blank" rel="noopener" href="https://www.youtube.com/watch?v=' + esc(yt) + '">▶ Watch on YouTube ↗</a><span class="m">If the player says it cannot play here, use this link.</span></div>'
          : '<div class="m" style="margin:0 0 12px">SIMKL has no trailer for this title. <a target="_blank" rel="noopener" href="https://www.youtube.com/results?search_query=' + encodeURIComponent((d.title || it.title || '') + ' ' + (d.year || it.year || '') + ' trailer') + '">Search YouTube ↗</a></div>';
      }
      return '<div class="rate">' + p.join('') + '</div>' + (!d.rotten && d.imdb ? '<div class="m" style="margin-top:6px;color:var(--dim)">Rotten Tomatoes and Metacritic scores appear here once you add a free OMDb key under SIMKL Hub → Configure → Calendar and sync.</div>' : '') + links + trailer;
    }
    _manageRow(d, it, what) {
      const isMovie = it.kind === 'movie';
      const cur = d.list;
      const lists = isMovie ? [['plantowatch', 'Plan to watch']] : [['plantowatch', 'Plan to watch'], ['watching', 'Watching'], ['hold', 'On hold'], ['dropped', 'Dropped'], ['completed', 'Completed']];
      const cf = (k, label) => '<button data-mk="' + k + '" class="' + (this._cf === k ? 'cf' : '') + '">' + (this._cf === k ? 'Tap again to confirm' : label) + '</button>';
      let h = '<div class="sec">Your list</div><div class="acts">' + lists.map(([k, l]) => '<button data-ls="' + k + '" class="' + (cur === k ? 'on' : '') + '">' + l + '</button>').join('') + '</div>';
      h += '<div class="sec">Mark as watched</div><div class="acts">';
      if (isMovie) h += '<button data-mk="movie">✓ Watched</button><button data-mk="unmovie">Not watched</button>';
      else {
        if (this._ep != null) h += '<button data-mk="ep">✓ ' + esc(what) + ' watched</button><button data-mk="unep">Unmark ' + esc(what) + '</button>';
        if (this._season != null && this._season > 0) h += cf('season', '✓ Season ' + this._season + ' watched');
        h += cf('all', '✓ Whole show watched');
      }
      return h + '</div>';
    }
    async _call(msg, okText) {
      try { await this._hass.callWS(msg); this._toast = okText; this._toastBad = false; }
      catch (e) { this._toast = (e && (e.message || e.code)) || 'Failed'; this._toastBad = true; }
      this._cf = null; this._render(); setTimeout(() => { this._toast = ''; this._render(); }, 6000);
      this._loadState(); try { const d = await this._hass.callWS({ type: 'simkl_hub/detail', kind: this._sel.kind, simkl_id: String(this._sel.id) }); this._det = d; this._render(); } catch (e) { /* keep old */ }
    }
    _mark(k) {
      const s = this._sel, base = { type: 'simkl_hub/mark', kind: s.kind, simkl_id: String(s.id) };
      if ((k === 'season' || k === 'all') && this._cf !== k) { this._cf = k; this._render(); clearTimeout(this._cft); this._cft = setTimeout(() => { this._cf = null; this._render(); }, 4000); return; }
      if (k === 'movie') return this._call(base, 'Marked as watched');
      if (k === 'unmovie') return this._call({ ...base, watched: false }, 'Marked as not watched');
      if (k === 'ep') return this._call({ ...base, season: this._season, episode: this._ep }, 'Marked S' + this._season + 'E' + this._ep + ' watched');
      if (k === 'unep') return this._call({ ...base, season: this._season, episode: this._ep, watched: false }, 'Unmarked S' + this._season + 'E' + this._ep);
      if (k === 'season') return this._call({ ...base, season: this._season }, 'Season ' + this._season + ' marked watched');
      if (k === 'all') return this._call(base, 'Whole show marked watched');
    }
    _setList(to) { const s = this._sel; return this._call({ type: 'simkl_hub/set_list', kind: s.kind, simkl_id: String(s.id), to }, 'Moved to ' + to.replace('plantowatch', 'Plan to watch').replace('hold', 'On hold')); }

    /* ---------- search / trending ---------- */
    _flash(msg) {
      const el = document.createElement('div'); el.textContent = msg;
      el.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:99;background:#fbbf24;color:#1b1500;padding:10px 16px;border-radius:12px;font:600 13px system-ui;max-width:90vw';
      this.shadowRoot.appendChild(el); setTimeout(() => el.remove(), 6000);
    }
    _status(kind, id) {
      const st = this._st || {}, k = kind + '|' + id;
      if ((st.done || []).includes(k)) return 'done';
      if ((st.watching || []).some((x) => x.kind + '|' + x.id === k)) return 'now';
      if ((st.plan || []).some((x) => x.kind + '|' + x.id === k)) return 'plan';
      return '';
    }
    _badge(kind, id) {
      const s = this._status(kind, id); if (!s) return '';
      return '<span class="bd ' + s + '">' + (s === 'done' ? '✓ Watched' : s === 'now' ? 'Watching' : 'Plan') + '</span>';
    }
    _store(list) { (list || []).forEach((x) => { this._pool[x.kind + '|' + x.id] = x; }); return list; }
    async _loadDone() {
      if (this._done || this._doneBusy) return; this._doneBusy = true;
      try { this._done = this._store(await this._hass.callWS({ type: 'simkl_hub/completed' })); } catch (e) { this._done = []; }
      this._doneBusy = false; this._render();
    }
    async _loadTrending() {
      const t = this._tr, key = t.kind + '|' + t.period; if (t.data[key] || t.busy === key) return; t.busy = key;
      try { t.data[key] = this._store(await this._hass.callWS({ type: 'simkl_hub/trending', kind: t.kind, period: t.period })); t.err = ''; }
      catch (e) { t.err = (e && (e.message || e.code)) || 'Could not load trending'; t.data[key] = []; }
      t.busy = null; this._render();
    }
    async _search() {
      const q = this._q.trim(); if (q.length < 2) return; this._sbusy = true; this._render();
      try { this._sr = this._store(await this._hass.callWS({ type: 'simkl_hub/search', q, kind: this._sk })); this._serr = ''; }
      catch (e) { this._sr = []; this._serr = (e && (e.message || e.code)) || 'Search failed'; }
      this._sbusy = false; this._render();
    }
    _trendingView(card) {
      const t = this._tr, key = t.kind + '|' + t.period; this._loadTrending();
      const seg = (attr, cur, opts) => '<div class="seg">' + opts.map(([k, l]) => '<button ' + attr + '="' + k + '" class="' + (cur === k ? 'on' : '') + '">' + l + '</button>').join('') + '</div>';
      const ctl = '<div class="sub2">' + seg('data-trk', t.kind, [['show', 'TV series'], ['movie', 'Movies'], ['anime', 'Anime']]) + seg('data-trp', t.period, [['today', 'Today'], ['week', 'This week'], ['month', 'This month']]) + '</div>';
      const list = t.data[key];
      if (!list) return ctl + '<div class="empty">Loading trending…</div>';
      if (!list.length) return ctl + '<div class="empty">' + esc(t.err || 'Nothing trending right now.') + '</div>';
      return ctl + '<div class="grid">' + list.map((x) => card(x, x.rating ? '<div class="m">★ ' + esc(x.rating) + '</div>' : '', '<span class="rk">#' + x.rank + '</span>')).join('') + '</div>';
    }
    _searchView(card) {
      const seg = '<div class="seg">' + [['all', 'All'], ['show', 'TV series'], ['movie', 'Movies'], ['anime', 'Anime']].map(([k, l]) => '<button data-sk="' + k + '" class="' + (this._sk === k ? 'on' : '') + '">' + l + '</button>').join('') + '</div>';
      const form = '<form class="sf" data-sf="1"><input type="search" placeholder="Search shows, movies and anime…" value="' + esc(this._q) + '" autocomplete="off"><button class="pri" type="submit">' + (this._sbusy ? 'Searching…' : 'Search') + '</button></form>';
      let res = '';
      if (this._sr) res = this._sr.length ? '<div class="grid">' + this._sr.map((x) => card(x, x.rating ? '<div class="m">★ ' + esc(x.rating) + '</div>' : '')).join('') + '</div>' : '<div class="empty">' + esc(this._serr || 'No matches.') + '</div>';
      else res = '<div class="empty">Type a title and press Enter.</div>';
      return form + '<div class="sub2">' + seg + '</div>' + res;
    }

    /* ---------- calendar ---------- */
    _dayRow(x) {
      const tags = (x.mine ? '<span class="tag mine">' + (x.st === 'watching' ? 'watching' : 'my list') + '</span>' : '') + (this._status(x.k, x.id) === 'done' ? '<span class="tag fin">watched</span>' : '') + (x.fin ? '<span class="tag fin">' + esc(String(x.fin).replace(/_/g, ' ')) + '</span>' : '');
      const sub = x.k === 'movie' ? 'Movie release' : [epLabel(x), x.et].filter(Boolean).map(esc).join(' · ');
      return '<div class="row" data-ci="' + esc(x.k + '|' + x.id + '|' + (x.s == null ? '' : x.s) + '|' + (x.e == null ? '' : x.e)) + '"><img loading="lazy" src="' + poster(x.poster) + '" alt=""><div class="x"><div class="t">' + esc(x.title) + tags + '</div><div class="m">' + sub + '</div><div class="m">' + fmtTime(x.date) + (x.rating ? ' · ★ ' + x.rating : '') + '</div></div></div>';
    }
    _calendarView() {
      this._ensureMonths();
      const map = this._byDay(), today = dkey(new Date());
      const ctl = () => {
        let label;
        if (this._view === 'month') label = MON[this._cursor.getMonth()] + ' ' + this._cursor.getFullYear();
        else if (this._view === 'week') { const s = this._weekStart(); const e = new Date(s); e.setDate(e.getDate() + 6); label = fmtDate(s) + ' – ' + fmtDate(e); }
        else label = 'Next 30 days';
        return '<div class="ctl"><button class="sm" data-nav="-1">‹</button><button class="sm" data-nav="0">Today</button><button class="sm" data-nav="1">›</button><h3>' + label + '</h3><span class="sp"></span>' +
          '<div class="seg">' + [['month', 'Month'], ['week', 'Week'], ['agenda', 'Agenda']].map(([k, l]) => '<button data-v="' + k + '" class="' + (this._view === k ? 'on' : '') + '">' + l + '</button>').join('') + '</div>' +
          '<div class="seg">' + [['mine', 'My list'], ['major', 'My list + major'], ['all', 'Everything']].map(([k, l]) => '<button data-sc="' + k + '" class="' + (this._scope === k ? 'on' : '') + '">' + l + '</button>').join('') + '</div></div>';
      };
      const dayPanel = () => { const a = map[this._day] || []; const d = new Date(this._day + 'T12:00:00'); return '<div class="panel"><h4>' + d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' }) + '</h4>' + (a.length ? a.map((x) => this._dayRow(x)).join('') : '<div class="empty">Nothing scheduled.</div>') + '</div>'; };
      if (this._view === 'month') {
        const y = this._cursor.getFullYear(), m = this._cursor.getMonth(), first = new Date(y, m, 1), off = (first.getDay() + 6) % 7;
        const start = new Date(y, m, 1 - off); const cells = Math.ceil((off + new Date(y, m + 1, 0).getDate()) / 7) * 7; const max = (this._narrow || (this.clientWidth && this.clientWidth < 640)) ? 2 : 3;
        let g = DOW.map((x) => '<div class="dow">' + x + '</div>').join('');
        for (let i = 0; i < cells; i++) {
          const d = new Date(start); d.setDate(start.getDate() + i); const k = dkey(d), a = map[k] || [];
          g += '<div class="day ' + (d.getMonth() !== m ? 'out ' : '') + (k === today ? 'today ' : '') + (k === this._day ? 'sel' : '') + '" data-d="' + k + '"><span class="n">' + d.getDate() + '</span>' +
            a.slice(0, max).map((x) => '<div class="chip ' + (x.k === 'movie' ? 'movie ' : '') + (x.mine ? 'mine' : '') + '" title="' + esc(x.title) + '">' + esc(x.title) + (x.s != null ? ' ' + epLabel(x) : '') + '</div>').join('') + (a.length > max ? '<div class="more">+' + (a.length - max) + ' more</div>' : '') + '</div>';
        }
        return ctl() + '<div class="cal side"><div class="mg">' + g + '</div>' + dayPanel() + '</div>';
      }
      if (this._view === 'week') {
        const s = this._weekStart(); let cols = '';
        for (let i = 0; i < 7; i++) { const d = new Date(s); d.setDate(s.getDate() + i); const k = dkey(d), a = map[k] || []; cols += '<div class="col ' + (k === today ? 'today' : '') + '"><h5>' + DOW[i] + ' ' + d.getDate() + '</h5>' + (a.length ? a.map((x) => this._dayRow(x)).join('') : '<div class="m">—</div>') + '</div>'; }
        return ctl() + '<div class="wk">' + cols + '</div>';
      }
      let out = ''; const n = new Date();
      for (let i = 0; i < 30; i++) { const d = new Date(n.getFullYear(), n.getMonth(), n.getDate() + i); const k = dkey(d), a = map[k] || []; if (!a.length) continue; out += '<h5 class="' + (k === today ? 'today' : '') + '">' + (i === 0 ? 'Today · ' : i === 1 ? 'Tomorrow · ' : '') + d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' }) + '</h5>' + a.map((x) => this._dayRow(x)).join(''); }
      return ctl() + '<div class="ag panel">' + (out || '<div class="empty">Nothing scheduled in the next 30 days.</div>') + '</div>';
    }
    _weekStart() { const b = this._wk || new Date(); const d = new Date(b.getFullYear(), b.getMonth(), b.getDate()); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return d; }
    _nav(n) {
      if (this._view === 'month') { if (n === 0) { this._cursor = new Date(); this._cursor.setDate(1); this._day = dkey(new Date()); } else this._cursor = new Date(this._cursor.getFullYear(), this._cursor.getMonth() + n, 1); }
      else if (this._view === 'week') { const s = n === 0 ? new Date() : this._weekStart(); if (n !== 0) s.setDate(s.getDate() + 7 * n); this._wk = s; }
    }

    /* ---------- main render ---------- */
    _render() {
      const st = this._st, root = this.shadowRoot; let body = '';
      if (!st) body = '<div class="empty">Loading…</div>';
      else if (!st.connected) body = '<div class="box"><div>SIMKL is not connected.</div><div>Go to <b>Settings → Devices &amp; services → Add integration → SIMKL Hub</b> to sign in.</div>' + (st.error ? '<div class="err">' + esc(st.error) + '</div>' : '') + '</div>';
      else if (this._sel) body = '<div class="tabs"><button data-back="1">← Back</button></div>' + this._detailView();
      else {
        const w = st.watching || [], p = st.plan || [], c = st.completed || {};
        const card = (x, extra, badge) => '<div class="it ' + (this._status(x.kind, x.id) === 'done' ? 'seen' : '') + '" data-k="' + esc(x.kind + '|' + x.id) + '">' + (badge || '') + (this._tab === 'watching' || this._tab === 'upnext' || this._tab === 'plan' ? '' : this._badge(x.kind, x.id)) + (this._status(x.kind, x.id) === 'done' ? '' : '<button class="qm" data-qm="' + esc(x.kind + '|' + x.id) + '" title="Mark as watched">✓</button>') + '<img loading="lazy" src="' + poster(x.poster) + '" alt=""><div class="b"><div class="t">' + esc(x.title) + '</div><div class="m">' + esc(x.year || '') + ' · ' + esc(x.kind) + '</div>' + (extra || '') + '</div></div>';
        const prog = (x) => { if (!x.total) return ''; const pc = Math.min(100, Math.round((x.watched || 0) / x.total * 100)); return '<div class="bar"><i style="width:' + pc + '%"></i></div><div class="m">' + (x.watched || 0) + '/' + x.total + ' eps</div>'; };
        const nxt = (x) => (x.next && x.next.episode != null ? '<div class="nx">Next: S' + (x.next.season || 1) + 'E' + x.next.episode + (x.next.date ? ' · ' + fmtDate(x.next.date) : '') + '</div>' : '');
        let inner;
        if (this._tab === 'calendar') inner = this._calendarView();
        else if (this._tab === 'upnext') { const u = w.filter((x) => x.next && x.next.episode != null).sort((a, b) => new Date(b.last || 0) - new Date(a.last || 0)); inner = u.length ? '<div class="grid">' + u.map((x) => card(x, nxt(x) + (x.next.date && new Date(x.next.date) > Date.now() ? '<div class="m">Not aired yet</div>' : '<div class="m">Ready to watch</div>'))).join('') + '</div>' : '<div class="empty">No episodes waiting.</div>'; }
        else if (this._tab === 'done') { this._loadDone(); inner = this._done ? (this._done.length ? '<div class="grid">' + this._done.map((x) => card(x)).join('') + '</div>' : '<div class="empty">Nothing marked as watched yet.</div>') : '<div class="empty">Loading…</div>'; }
        else if (this._tab === 'trending') inner = this._trendingView(card);
        else if (this._tab === 'search') inner = this._searchView(card);
        else if (this._tab === 'plan') inner = p.length ? '<div class="grid">' + p.map((x) => card(x)).join('') + '</div>' : '<div class="empty">Plan to watch is empty.</div>';
        else if (this._tab === 'stats') inner = '<div class="stats"><div class="st"><b>' + w.length + '</b><span>Watching</span></div><div class="st"><b>' + p.length + '</b><span>Plan to watch</span></div><div class="st"><b>' + (c.shows || 0) + '</b><span>Shows completed</span></div><div class="st"><b>' + (c.anime || 0) + '</b><span>Anime completed</span></div><div class="st"><b>' + (c.movies || 0) + '</b><span>Movies watched</span></div></div>';
        else inner = w.length ? '<div class="grid">' + w.map((x) => card(x, prog(x) + nxt(x))).join('') + '</div>' : '<div class="empty">Nothing in Watching.</div>';
        body = '<div class="tabs">' + [['calendar', 'Calendar'], ['upnext', 'Up next'], ['watching', 'Watching'], ['plan', 'Plan to watch'], ['done', 'Watched'], ['trending', 'Trending'], ['search', 'Search'], ['stats', 'Stats']].map(([k, l]) => '<button data-t="' + k + '" class="' + (this._tab === k ? 'on' : '') + '">' + l + '</button>').join('') + '</div>' + inner;
      }
      const upd = st && st.updated ? 'Updated ' + ago(st.updated) : '';
      root.innerHTML = '<style>' + CSS + '</style><div class="wrap"><div class="hd"><h2>SIMKL</h2><span class="sub">' + upd + '</span><span class="sp"></span>' + (st && st.connected ? '<button class="sm" data-a="sync">Sync now</button>' : '') + '</div>' + body + (st && st.connected && st.ok === false ? '<div class="err">Last sync failed; showing earlier data.</div>' : '') + '</div>';
      this._wire(root);
    }
    _wire(root) {
      const on = (sel, fn) => root.querySelectorAll(sel).forEach((b) => b.addEventListener('click', () => fn(b)));
      const all = () => [...((this._st && this._st.watching) || []), ...((this._st && this._st.plan) || [])];
      on('[data-t]', (b) => { this._tab = b.dataset.t; this._focusSearch = this._tab === 'search'; this._render(); });
      on('[data-k]', (b) => { const it = all().find((x) => x.kind + '|' + x.id === b.dataset.k) || this._pool[b.dataset.k]; if (it) this._open(it); });
      on('[data-back]', () => { this._sel = null; this._det = null; this._render(); });
      on('[data-s]', (b) => { this._season = Number(b.dataset.s); this._ep = null; this._render(); });
      on('[data-e]', (b) => { this._ep = Number(b.dataset.e); this._render(); });
      root.querySelectorAll('[data-qm]').forEach((b) => b.addEventListener('click', async (e) => {
        e.stopPropagation(); const [kind, id] = b.dataset.qm.split('|'); b.textContent = '…';
        try { await this._hass.callWS({ type: 'simkl_hub/mark', kind, simkl_id: id }); this._st = { ...this._st, done: [...((this._st && this._st.done) || []), kind + '|' + id] }; this._done = null; this._render(); this._loadState(); }
        catch (err) { b.textContent = '✓'; this._flash((err && (err.message || err.code)) || 'Could not mark as watched'); }
      }));
      on('[data-trl]', () => { this._trailer = !this._trailer; this._render(); });
      on('[data-mk]', (b) => this._mark(b.dataset.mk));
      on('[data-ls]', (b) => this._setList(b.dataset.ls));
      on('[data-trk]', (b) => { this._tr.kind = b.dataset.trk; this._render(); });
      on('[data-trp]', (b) => { this._tr.period = b.dataset.trp; this._render(); });
      on('[data-sk]', (b) => { this._sk = b.dataset.sk; if (this._q.trim().length > 1 && this._sr) this._search(); else this._render(); });
      root.querySelectorAll('[data-sf]').forEach((f) => { const inp = f.querySelector('input'); inp.addEventListener('input', () => { this._q = inp.value; }); f.addEventListener('submit', (e) => { e.preventDefault(); this._q = inp.value; this._search(); }); if (this._focusSearch) { this._focusSearch = false; inp.focus(); } });
      on('[data-p]', (b) => this._send(this._playerList()[Number(b.dataset.p)]));
      on('[data-v]', (b) => { this._view = b.dataset.v; this._render(); });
      on('[data-sc]', (b) => { this._scope = b.dataset.sc; this._render(); });
      on('[data-nav]', (b) => { this._nav(Number(b.dataset.nav)); this._render(); });
      on('[data-d]', (b) => { this._day = b.dataset.d; this._render(); });
      on('[data-ci]', (b) => {
        const [k, id, s, e] = b.dataset.ci.split('|'); const hit = Object.values(this._cal).flat().find((x) => x.k === k && String(x.id) === id);
        this._open({ kind: k, id: id, title: hit && hit.title, poster: hit && hit.poster }, s === '' ? null : Number(s), e === '' ? null : Number(e));
      });
      on('[data-a="sync"]', async (b) => { b.textContent = 'Syncing…'; try { await this._hass.callWS({ type: 'simkl_hub/refresh' }); } catch (e) { /* ignore */ } setTimeout(() => this._loadState(), 3000); });
    }
  }

  class SimklHubPanel extends HTMLElement {
    set hass(h) { this._h = h; this._ensure(); this._c.hass = h; }
    set narrow(n) { this._n = n; this._ensure(); this._c.narrow = n; }
    set panel(p) { /* unused */ }
    _ensure() {
      if (this._c) return;
      this.style.display = 'block'; this.style.padding = '16px'; this.style.minHeight = '100vh'; this.style.background = '#0b0d14'; this.style.boxSizing = 'border-box';
      this._c = document.createElement('simkl-hub-card'); this._c.setConfig({}); this.appendChild(this._c);
    }
  }

  if (!customElements.get('simkl-hub-card')) customElements.define('simkl-hub-card', SimklHubCard);
  if (!customElements.get('simkl-hub-panel')) customElements.define('simkl-hub-panel', SimklHubPanel);
  window.customCards = window.customCards || [];
  if (!window.customCards.find((c) => c.type === 'simkl-hub-card')) window.customCards.push({ type: 'simkl-hub-card', name: 'SIMKL Hub', description: 'Watchlist, release calendar, trending, search, ratings and open-in-Stremio' });
})();
