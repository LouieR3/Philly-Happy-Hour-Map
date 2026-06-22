// ─── Happy Hour map (SCOPE Phase 5) ────────────────────────────────────────
// Reads /api/happy-hours (happy_hours ⨝ bars ⨝ happy_hour_items) and renders a
// toggleable layer with day / drink / neighborhood filters. Mirrors the
// pool/sports map conventions so it slots into the mobile hub + Near Me.

const HH_API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:3000'
  : 'https://philly-happy-hour-map-production.up.railway.app';

var happyHourMap = L.map('happy-hour-leaflet-map').setView([39.951, -75.163], 12);
happyHourMap.zoomControl.setPosition('bottomright');

var hhBasemap = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap & CartoDB', subdomains: 'abcd',
}).addTo(happyHourMap);
var hhLight = false;
(function () {
  var btn = document.getElementById('hh-basemap-toggle');
  if (!btn) return;
  btn.addEventListener('click', function () {
    happyHourMap.removeLayer(hhBasemap);
    hhBasemap = L.tileLayer('https://{s}.basemaps.cartocdn.com/' + (hhLight ? 'dark_all' : 'light_all') + '/{z}/{x}/{y}{r}.png',
      { attribution: '&copy; OpenStreetMap & CartoDB', subdomains: 'abcd' }).addTo(happyHourMap);
    hhLight = !hhLight;
    btn.innerHTML = hhLight ? '<i class="fa-solid fa-moon"></i><span>Dark Mode</span>'
                            : '<i class="fa-solid fa-sun"></i><span>Light Mode</span>';
  });
})();

var hhAllData = [];
var hhMarkers = [];
var hhSearch = '';
const hhFilters = { day: '', drink: '', neighborhood: '' };

function hhEsc(s) {
  if (s === undefined || s === null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function createHHIcon() {
  return L.divIcon({
    html: '<div class="custom-pin"><div class="pin-circle" style="background-color:#f59e0b;">' +
          '<i class="fa-solid fa-martini-glass-citrus" style="font-size:12px;"></i></div>' +
          '<div class="pin-tail" style="background-color:#f59e0b;"></div></div>',
    className: 'custom-fa-icon', iconSize: [30, 30], iconAnchor: [15, 30], popupAnchor: [0, -30],
  });
}

function buildHHPopup(bar) {
  var items = (bar.items || []).slice(0, 10).map(function (i) {
    var label = i.normalized_item || i.raw_item || '';
    return '<div style="display:flex;justify-content:space-between;gap:10px;font-size:12px;">' +
           '<span style="color:#e2e8f0;">' + hhEsc(label) + '</span>' +
           '<span style="color:#fbbf24;font-weight:600;">' + (i.hh_price != null ? '$' + i.hh_price : '') + '</span></div>';
  }).join('');
  return '<div style="font-family:\'Red Hat Text\',sans-serif;width:240px;border-radius:8px;overflow:hidden;">' +
    '<div style="background:#7c2d12;padding:12px 16px;">' +
      '<p style="margin:0;font-size:15px;font-weight:600;color:#fff;">🍸 ' + hhEsc(bar.name || '—') + '</p>' +
      (bar.neighborhood ? '<p style="margin:3px 0 0;font-size:12px;color:rgba(255,255,255,0.7);">' + hhEsc(bar.neighborhood) + '</p>' : '') +
    '</div>' +
    '<div style="padding:12px 14px;background:#1a2332;color:#e2e8f0;">' +
      (bar.hh_times_raw ? '<div style="font-size:12px;color:#fbbf24;margin-bottom:8px;"><i class="fa-regular fa-clock"></i> ' + hhEsc(bar.hh_times_raw) + '</div>' : '') +
      (items ? '<div style="display:flex;flex-direction:column;gap:3px;margin-bottom:8px;">' + items + '</div>'
             : '<div style="font-size:12px;color:rgba(255,255,255,0.6);margin-bottom:8px;">Menu items not parsed yet — see source.</div>') +
      (bar.source_url ? '<a href="' + hhEsc(bar.source_url) + '" target="_blank" rel="noopener" style="font-size:12px;color:#34d399;text-decoration:none;">View happy hour menu →</a>' : '') +
    '</div></div>';
}

// ── Filter predicates ───────────────────────────────────────────────────────
function hhDayMatches(bar) {
  if (!hhFilters.day) return true;
  var d = (bar.hh_days || '').toLowerCase();
  if (!d) return true;                       // unknown days stay visible
  if (/dai|every|all|week/.test(d)) return true;
  return d.indexOf(hhFilters.day.slice(0, 3)) !== -1;   // "mon" matches "monday"/"mon-fri"
}
function hhDrinkMatches(bar) {
  if (!hhFilters.drink) return true;
  return (bar.categories || []).indexOf(hhFilters.drink) !== -1;
}
function hhNeighborhoodMatches(bar) {
  if (!hhFilters.neighborhood) return true;
  return (bar.neighborhood || null) === hhFilters.neighborhood;
}
function hhSearchMatches(bar) {
  if (!hhSearch) return true;
  return (bar.name || '').toLowerCase().indexOf(hhSearch) !== -1;
}
function getFilteredHH() {
  return hhAllData.filter(function (b) {
    return hhDayMatches(b) && hhDrinkMatches(b) && hhNeighborhoodMatches(b) && hhSearchMatches(b);
  });
}

// ── Render ───────────────────────────────────────────────────────────────────
function applyHHFilters() {
  var filtered = getFilteredHH();
  var keep = new Set(filtered.map(function (b) { return b.name; }));
  hhMarkers.forEach(function (m) {
    if (keep.has(m.barName)) { if (!happyHourMap.hasLayer(m)) m.addTo(happyHourMap); }
    else if (happyHourMap.hasLayer(m)) happyHourMap.removeLayer(m);
  });
  var ordered = filtered;
  if (window.mappyUserLocation && typeof window.mappyHaversineMiles === 'function') {
    var u = window.mappyUserLocation;
    ordered = filtered.slice().sort(function (a, b) {
      return window.mappyHaversineMiles(u.lat, u.lng, +a.lat, +a.lng) -
             window.mappyHaversineMiles(u.lat, u.lng, +b.lat, +b.lng);
    });
  }
  populateHHSidebar(ordered);
  if (window._hhDrawerSetData) window._hhDrawerSetData(ordered);
}

function hhCard(bar) {
  var card = document.createElement('div');
  card.className = 'bar-card';
  var ph = document.createElement('div');
  ph.className = 'bar-card-thumb-placeholder';
  ph.innerHTML = '<i class="fa-solid fa-martini-glass-citrus"></i>';
  var tags = (bar.categories || []).slice(0, 4)
    .map(function (c) { return '<span class="bar-card-tag">' + hhEsc(c) + '</span>'; }).join('');
  var body = document.createElement('div');
  body.className = 'bar-card-body';
  body.innerHTML = '<div class="bar-card-name">' + hhEsc(bar.name) + '</div>' +
    '<div class="bar-card-address">' + hhEsc(bar.neighborhood || '') + '</div>' +
    (bar.hh_times_raw ? '<div class="bar-card-address" style="color:#fbbf24;font-weight:normal;">' + hhEsc(bar.hh_times_raw) + '</div>' : '') +
    (tags ? '<div class="bar-card-tags">' + tags + '</div>' : '');
  card.appendChild(ph);
  card.appendChild(body);
  card.addEventListener('click', function () {
    var m = hhMarkers.find(function (x) { return x.barName === bar.name; });
    if (m) { happyHourMap.setView(m.getLatLng(), 16); m.openPopup(); }
  });
  return card;
}

function populateHHSidebar(list) {
  var el = document.getElementById('hh-bar-list');
  if (!el) return;
  el.innerHTML = '';
  if (!list.length) { el.innerHTML = '<p style="color:var(--mh-text-muted);padding:12px;">No happy hours match.</p>'; return; }
  list.forEach(function (b) { el.appendChild(hhCard(b)); });
}

function populateHHNeighborhoods() {
  var hoods = [...new Set(hhAllData.map(function (b) { return b.neighborhood; }).filter(Boolean))].sort();
  ['hh-neighborhood-filter', 'hh-mobile-neighborhood-select'].forEach(function (id) {
    var sel = document.getElementById(id);
    if (!sel) return;
    hoods.forEach(function (h) {
      var o = document.createElement('option'); o.value = h; o.textContent = h; sel.appendChild(o);
    });
  });
}

// ── Load data ─────────────────────────────────────────────────────────────────
fetch(HH_API_BASE + '/api/happy-hours')
  .then(function (r) { return r.json(); })
  .then(function (data) {
    hhAllData = Array.isArray(data) ? data.filter(function (b) { return b.lat != null && b.lng != null; }) : [];
    hhAllData.forEach(function (bar) {
      var m = L.marker([bar.lat, bar.lng], { icon: createHHIcon() }).bindPopup(buildHHPopup(bar), { maxWidth: 260 });
      m.barName = bar.name;
      hhMarkers.push(m);
      m.addTo(happyHourMap);
    });
    populateHHNeighborhoods();
    populateHHSidebar(hhAllData);
    if (window._hhDrawerSetData) window._hhDrawerSetData(hhAllData);
  })
  .catch(function (err) { console.error('[happy-hour] load failed:', err); });

// ── Filter wiring ───────────────────────────────────────────────────────────
function bindHHSelect(id, key, mirrorId) {
  var el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('change', function () {
    hhFilters[key] = el.value;
    if (mirrorId) { var mm = document.getElementById(mirrorId); if (mm) mm.value = el.value; }
    applyHHFilters();
  });
}
bindHHSelect('hh-day-filter', 'day', 'hh-mobile-day-select');
bindHHSelect('hh-drink-filter', 'drink', 'hh-mobile-drink-select');
bindHHSelect('hh-neighborhood-filter', 'neighborhood', 'hh-mobile-neighborhood-select');

var hhSearchEl = document.getElementById('hh-bar-search');
if (hhSearchEl) hhSearchEl.addEventListener('input', function () { hhSearch = this.value.trim().toLowerCase(); applyHHFilters(); });

var hhResetBtn = document.getElementById('hh-reset-button');
if (hhResetBtn) hhResetBtn.addEventListener('click', function () {
  hhFilters.day = hhFilters.drink = hhFilters.neighborhood = ''; hhSearch = '';
  ['hh-day-filter', 'hh-drink-filter', 'hh-neighborhood-filter', 'hh-mobile-day-select', 'hh-mobile-drink-select', 'hh-mobile-neighborhood-select'].forEach(function (id) {
    var el = document.getElementById(id); if (el) el.value = '';
  });
  if (hhSearchEl) hhSearchEl.value = '';
  applyHHFilters();
});

// ── Mobile filter modal ───────────────────────────────────────────────────────
(function () {
  var modal = document.getElementById('hh-mobile-filter-modal');
  var openBtn = document.getElementById('hh-mobile-filter-btn');
  var closeBtn = document.getElementById('hh-filter-close');
  var applyBtn = document.getElementById('hh-mobile-filter-apply');
  var resetBtn = document.getElementById('hh-mobile-filter-reset');
  if (openBtn) openBtn.addEventListener('click', function () { if (modal) modal.classList.add('active'); });
  if (closeBtn) closeBtn.addEventListener('click', function () { if (modal) modal.classList.remove('active'); });
  if (applyBtn) applyBtn.addEventListener('click', function () {
    hhFilters.day = (document.getElementById('hh-mobile-day-select') || {}).value || '';
    hhFilters.drink = (document.getElementById('hh-mobile-drink-select') || {}).value || '';
    hhFilters.neighborhood = (document.getElementById('hh-mobile-neighborhood-select') || {}).value || '';
    // mirror to desktop selects
    var map = { 'hh-day-filter': hhFilters.day, 'hh-drink-filter': hhFilters.drink, 'hh-neighborhood-filter': hhFilters.neighborhood };
    Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) el.value = map[id]; });
    if (modal) modal.classList.remove('active');
    applyHHFilters();
  });
  if (resetBtn) resetBtn.addEventListener('click', function () {
    ['hh-mobile-day-select', 'hh-mobile-drink-select', 'hh-mobile-neighborhood-select'].forEach(function (id) {
      var el = document.getElementById(id); if (el) el.value = '';
    });
  });
})();

// ── Mobile bottom drawer ────────────────────────────────────────────────────
(function () {
  var drawerData = [];
  function render(list) {
    var row = document.getElementById('hh-drawer-cards');
    if (!row) return;
    var q = ((document.getElementById('hh-drawer-search') || {}).value || '').toLowerCase();
    row.innerHTML = '';
    var shown = list.filter(function (b) { return !q || (b.name || '').toLowerCase().indexOf(q) !== -1; });
    if (!shown.length) { row.innerHTML = '<p style="color:#64748b;padding:20px;font-size:0.85rem;">No happy hours match.</p>'; return; }
    shown.forEach(function (bar) {
      var card = document.createElement('div');
      card.className = 'drawer-card';
      var ph = document.createElement('div');
      ph.className = 'drawer-card-thumb-placeholder';
      ph.innerHTML = '<i class="fa-solid fa-martini-glass-citrus"></i>';
      var body = document.createElement('div');
      body.className = 'drawer-card-body';
      body.innerHTML = '<div class="drawer-card-name">' + hhEsc(bar.name || '') + '</div>' +
        (bar.neighborhood ? '<div class="drawer-card-meta">' + hhEsc(bar.neighborhood) + '</div>' : '') +
        (bar.hh_times_raw ? '<div class="drawer-card-tags"><span class="drawer-card-tag">' + hhEsc(bar.hh_times_raw) + '</span></div>' : '');
      card.appendChild(ph); card.appendChild(body);
      card.addEventListener('click', function () {
        var m = hhMarkers.find(function (x) { return x.barName === bar.name; });
        if (m) { close(); happyHourMap.setView(m.getLatLng(), 16); m.openPopup(); }
      });
      row.appendChild(card);
    });
  }
  function open() {
    document.getElementById('hh-drawer').classList.add('open');
    document.getElementById('hh-drawer-backdrop').classList.add('open');
    render(drawerData);
  }
  function close() {
    var d = document.getElementById('hh-drawer'); if (d) d.classList.remove('open');
    var b = document.getElementById('hh-drawer-backdrop'); if (b) b.classList.remove('open');
  }
  window._hhDrawerSetData = function (data) { drawerData = data; };
  var listBtn = document.getElementById('hh-list-btn');
  if (listBtn) listBtn.addEventListener('click', open);
  var closeBtn = document.getElementById('hh-drawer-close');
  if (closeBtn) closeBtn.addEventListener('click', function (e) { e.preventDefault(); close(); });
  var backdrop = document.getElementById('hh-drawer-backdrop');
  if (backdrop) backdrop.addEventListener('click', close);
  var search = document.getElementById('hh-drawer-search');
  if (search) search.addEventListener('input', function () { render(drawerData); });
})();

// ── Location services: "Near Me" ──────────────────────────────────────────────
if (window.LocationServices) {
  window.LocationServices.attach({
    map:           happyHourMap,
    getData:       function () { return getFilteredHH(); },
    getLatLng:     function (b) { return [b.lat, b.lng]; },
    getName:       function (b) { return b.name; },
    renderList:    function (d) { populateHHSidebar(d); },
    setDrawerData: function (d) { if (window._hhDrawerSetData) window._hhDrawerSetData(d); },
    listSelectors: ['#hh-bar-list', '#hh-drawer-cards'],
  });
}
