// ─── Happy Hour map (SCOPE Phase 5) ────────────────────────────────────────
// Progressive loading: the map opens showing the Philadelphia neighborhood
// overlay (no points). Click a neighborhood to load just that area's happy-hour
// points — this keeps the initial render light instead of dropping every marker
// at once. Day / drink / search filters apply on top of the selected areas.

const HH_API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:3000'
  : 'https://philly-happy-hour-map-production.up.railway.app';

var happyHourMap = L.map('happy-hour-leaflet-map').setView([39.9526, -75.1652], 12);
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

// ── State ─────────────────────────────────────────────────────────────────────
var hhAllData = [];                 // bars (with ._nh assigned) inside a Philly neighborhood
var hhLayer = L.layerGroup().addTo(happyHourMap);   // currently-shown markers
var hhGeoLayer = null;              // neighborhood polygon overlay
var hhCountByNh = {};               // LISTNAME -> # of HH bars
var selectedHoods = new Set();      // LISTNAME(s) the user has clicked into
var hhSearch = '';
// Hour slider bounds: 11:00 AM (660) → 12:00 AM (1440), 30-min steps.
const HH_TIME_MIN = 660, HH_TIME_MAX = 1440;
// timeLo/timeHi in minutes; equal to the full range means "any time".
const hhFilters = { day: '', drink: '', timeLo: HH_TIME_MIN, timeHi: HH_TIME_MAX };

function hhFmt12(min) {
  if (min >= 1440) return '12:00 AM';
  var h = Math.floor(min / 60) % 24, m = min % 60;
  var ap = h >= 12 ? 'PM' : 'AM';
  h = h % 12; if (h === 0) h = 12;
  return h + (m ? ':' + String(m).padStart(2, '0') : ':00') + ' ' + ap;
}

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
      (bar.time_label ? '<div style="font-size:12px;color:#fbbf24;margin-bottom:8px;"><i class="fa-regular fa-clock"></i> ' + hhEsc(bar.time_label) + '</div>' : '') +
      (items ? '<div style="display:flex;flex-direction:column;gap:3px;margin-bottom:8px;">' + items + '</div>'
             : '<div style="font-size:12px;color:rgba(255,255,255,0.6);margin-bottom:8px;">Menu items not parsed yet — see source.</div>') +
      (bar.source_url ? '<a href="' + hhEsc(bar.source_url) + '" target="_blank" rel="noopener" style="font-size:12px;color:#34d399;text-decoration:none;">View happy hour menu →</a>' : '') +
    '</div></div>';
}

function ensureMarker(bar) {
  if (!bar._marker) {
    bar._marker = L.marker([bar.lat, bar.lng], { icon: createHHIcon() })
      .bindPopup(function () { return buildHHPopup(bar); }, { maxWidth: 260 });  // lazy popup HTML
    bar._marker.barName = bar.name;
  }
  return bar._marker;
}

// ── Filters ───────────────────────────────────────────────────────────────────
function hhDayMatches(bar) {
  if (!hhFilters.day) return true;                 // "Any day"
  var days = bar.days || [];
  if (!days.length) return false;                  // no parsed days → can't match a chosen day
  return days.indexOf(hhFilters.day.slice(0, 3)) !== -1;
}
function hhTimeMatches(bar) {
  // Full slider range = "any time": everything passes.
  if (hhFilters.timeLo <= HH_TIME_MIN && hhFilters.timeHi >= HH_TIME_MAX) return true;
  if (bar.start_min == null || bar.end_min == null) return false;  // no parsed time → can't confirm
  var s = bar.start_min, e = bar.end_min;
  if (e <= s) e += 1440;                            // window crosses midnight
  // The bar's happy hour overlaps the selected window.
  return s < hhFilters.timeHi && e > hhFilters.timeLo;
}
function hhDrinkMatches(bar) {
  if (!hhFilters.drink) return true;
  return (bar.categories || []).indexOf(hhFilters.drink) !== -1;
}
function hhSearchMatches(bar) {
  return !hhSearch || (bar.name || '').toLowerCase().indexOf(hhSearch) !== -1;
}

// Bars to actually show = those in a selected neighborhood that pass the filters.
function getVisibleHH() {
  if (!selectedHoods.size) return [];
  return hhAllData.filter(function (b) {
    return selectedHoods.has(b._nh) && hhDayMatches(b) && hhTimeMatches(b) &&
           hhDrinkMatches(b) && hhSearchMatches(b);
  });
}

// ── Render ───────────────────────────────────────────────────────────────────
function renderHHView() {
  var visible = getVisibleHH();
  hhLayer.clearLayers();
  visible.forEach(function (b) { hhLayer.addLayer(ensureMarker(b)); });
  if (hhGeoLayer) hhGeoLayer.setStyle(hhPolyStyle);

  var ordered = visible;
  if (window.mappyUserLocation && typeof window.mappyHaversineMiles === 'function') {
    var u = window.mappyUserLocation;
    ordered = visible.slice().sort(function (a, b) {
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
    '<div class="bar-card-address">' + hhEsc(bar.neighborhood || bar._nh || '') + '</div>' +
    (bar.time_label ? '<div class="bar-card-address" style="color:#fbbf24;font-weight:normal;">' + hhEsc(bar.time_label) + '</div>' : '') +
    (tags ? '<div class="bar-card-tags">' + tags + '</div>' : '');
  card.appendChild(ph);
  card.appendChild(body);
  card.addEventListener('click', function () {
    var m = bar._marker;
    if (m) { happyHourMap.setView(m.getLatLng(), 16); m.openPopup(); }
  });
  return card;
}

function populateHHSidebar(list) {
  var el = document.getElementById('hh-bar-list');
  if (!el) return;
  el.innerHTML = '';
  if (!selectedHoods.size) {
    el.innerHTML = '<p style="color:var(--mh-text-muted);padding:12px;">Tap a neighborhood on the map to load its happy hours.</p>';
    return;
  }
  if (!list.length) { el.innerHTML = '<p style="color:var(--mh-text-muted);padding:12px;">No happy hours match here.</p>'; return; }
  list.forEach(function (b) { el.appendChild(hhCard(b)); });
}

// ── Neighborhood overlay ───────────────────────────────────────────────────────
function hhPolyStyle(feature) {
  var name = feature.properties.LISTNAME;
  var has = hhCountByNh[name] > 0;
  if (selectedHoods.has(name)) {
    return { color: '#34d399', weight: 2, fillColor: '#34d399', fillOpacity: 0.22 };
  }
  return {
    color: has ? '#f59e0b' : '#475569',
    weight: 1,
    fillColor: '#f59e0b',
    fillOpacity: has ? 0.10 : 0.02,
    dashArray: has ? null : '3',
  };
}

function toggleHood(name) {
  if (selectedHoods.has(name)) selectedHoods.delete(name);
  else selectedHoods.add(name);
  // keep the dropdown in sync (single selection) for clarity
  var sel = document.getElementById('hh-neighborhood-filter');
  if (sel) sel.value = selectedHoods.size === 1 ? [...selectedHoods][0] : '';
  renderHHView();
}

function buildHHGeoLayer(geo) {
  hhGeoLayer = L.geoJSON(geo, {
    style: hhPolyStyle,
    onEachFeature: function (feature, layer) {
      var name = feature.properties.LISTNAME;
      var count = hhCountByNh[name] || 0;
      layer.bindTooltip(name + (count ? ' · ' + count + ' happy hour' + (count !== 1 ? 's' : '') : ''),
        { sticky: true });
      layer.on({
        click: function () { toggleHood(name); },
        mouseover: function () { if (!selectedHoods.has(name)) layer.setStyle({ fillOpacity: 0.2 }); },
        mouseout: function () { if (!selectedHoods.has(name)) hhGeoLayer.resetStyle(layer); },
      });
    },
  }).addTo(happyHourMap);
}

function assignNeighborhood(bar, geo) {
  if (!window.turf) return bar.neighborhood || null;
  try {
    var pt = turf.point([+bar.lng, +bar.lat]);
    for (var i = 0; i < geo.features.length; i++) {
      if (turf.booleanPointInPolygon(pt, geo.features[i])) return geo.features[i].properties.LISTNAME;
    }
  } catch (e) {}
  return null;
}

function populateHHNeighborhoods() {
  var hoods = Object.keys(hhCountByNh).filter(function (n) { return hhCountByNh[n] > 0; }).sort();
  ['hh-neighborhood-filter', 'hh-mobile-neighborhood-select'].forEach(function (id) {
    var sel = document.getElementById(id);
    if (!sel) return;
    hoods.forEach(function (h) {
      var o = document.createElement('option'); o.value = h; o.textContent = h + ' (' + hhCountByNh[h] + ')'; sel.appendChild(o);
    });
  });
}

// ── Load data + overlay together ────────────────────────────────────────────
Promise.all([
  fetch(HH_API_BASE + '/api/happy-hours').then(function (r) { return r.json(); }).catch(function () { return []; }),
  fetch('assets/philadelphia-neighborhoods.geojson').then(function (r) { return r.json(); }).catch(function () { return null; }),
]).then(function (res) {
  var data = Array.isArray(res[0]) ? res[0] : [];
  var geo = res[1];
  data = data.filter(function (b) { return b.lat != null && b.lng != null; });
  if (geo) {
    data.forEach(function (b) { b._nh = assignNeighborhood(b, geo); });
    data = data.filter(function (b) { return b._nh; });   // Philadelphia proper only
    hhAllData = data;
    hhAllData.forEach(function (b) { hhCountByNh[b._nh] = (hhCountByNh[b._nh] || 0) + 1; });
    buildHHGeoLayer(geo);
  } else {
    hhAllData = data;   // no overlay available — fall back to showing everything
    hhAllData.forEach(function (b) { ensureMarker(b); hhLayer.addLayer(b._marker); });
  }
  populateHHNeighborhoods();
  renderHHView();
}).catch(function (err) { console.error('[happy-hour] load failed:', err); });

// ── Filter wiring ───────────────────────────────────────────────────────────
var hhDayEl = document.getElementById('hh-day-filter');
if (hhDayEl) hhDayEl.addEventListener('change', function () {
  hhFilters.day = this.value;
  var mm = document.getElementById('hh-mobile-day-select'); if (mm) mm.value = this.value;
  renderHHView();
});
var hhDrinkEl = document.getElementById('hh-drink-filter');
if (hhDrinkEl) hhDrinkEl.addEventListener('change', function () {
  hhFilters.drink = this.value;
  var mm = document.getElementById('hh-mobile-drink-select'); if (mm) mm.value = this.value;
  renderHHView();
});
// Dual-thumb hour range slider. `live` desktop slider re-renders on drag; the
// mobile one only updates its readout and is applied via the modal's Apply.
function setupHHTimeSlider(minId, maxId, readoutId, live) {
  var lo = document.getElementById(minId), hi = document.getElementById(maxId),
      out = document.getElementById(readoutId);
  if (!lo || !hi) return null;
  function update(render) {
    var a = +lo.value, b = +hi.value;
    if (a > b - 30) {                         // keep the thumbs at least one step apart
      if (document.activeElement === lo) { a = Math.min(a, HH_TIME_MAX - 30); b = a + 30; hi.value = b; }
      else { b = Math.max(b, HH_TIME_MIN + 30); a = b - 30; lo.value = a; }
    }
    var any = (a <= HH_TIME_MIN && b >= HH_TIME_MAX);
    if (out) out.textContent = any ? 'Any time' : (hhFmt12(a) + ' – ' + hhFmt12(b));
    if (render) { hhFilters.timeLo = a; hhFilters.timeHi = b; renderHHView(); }
  }
  lo.addEventListener('input', function () { update(live); });
  hi.addEventListener('input', function () { update(live); });
  update(false);
  return {
    get: function () { return [+lo.value, +hi.value]; },
    reset: function () { lo.value = HH_TIME_MIN; hi.value = HH_TIME_MAX; update(false); },
  };
}
var hhTimeSliderDesktop = setupHHTimeSlider('hh-time-min', 'hh-time-max', 'hh-time-readout', true);
var hhTimeSliderMobile  = setupHHTimeSlider('hh-mobile-time-min', 'hh-mobile-time-max', 'hh-mobile-time-readout', false);

var hhNhEl = document.getElementById('hh-neighborhood-filter');
if (hhNhEl) hhNhEl.addEventListener('change', function () {
  selectedHoods.clear();
  if (this.value) {
    selectedHoods.add(this.value);
    var lyr = hhGeoLayer && hhGeoLayer.getLayers().find(function (l) { return l.feature.properties.LISTNAME === hhNhEl.value; });
    if (lyr) happyHourMap.fitBounds(lyr.getBounds(), { maxZoom: 15 });
  }
  renderHHView();
});

var hhSearchEl = document.getElementById('hh-bar-search');
if (hhSearchEl) hhSearchEl.addEventListener('input', function () { hhSearch = this.value.trim().toLowerCase(); renderHHView(); });

var hhResetBtn = document.getElementById('hh-reset-button');
if (hhResetBtn) hhResetBtn.addEventListener('click', function () {
  hhFilters.day = hhFilters.drink = ''; hhSearch = ''; selectedHoods.clear();
  hhFilters.timeLo = HH_TIME_MIN; hhFilters.timeHi = HH_TIME_MAX;
  if (hhTimeSliderDesktop) hhTimeSliderDesktop.reset();
  if (hhTimeSliderMobile)  hhTimeSliderMobile.reset();
  ['hh-day-filter', 'hh-drink-filter', 'hh-neighborhood-filter', 'hh-mobile-day-select', 'hh-mobile-drink-select', 'hh-mobile-neighborhood-select'].forEach(function (id) {
    var el = document.getElementById(id); if (el) el.value = '';
  });
  if (hhSearchEl) hhSearchEl.value = '';
  renderHHView();
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
    var nh = (document.getElementById('hh-mobile-neighborhood-select') || {}).value || '';
    if (hhTimeSliderMobile) {
      var t = hhTimeSliderMobile.get();
      hhFilters.timeLo = t[0]; hhFilters.timeHi = t[1];
    }
    selectedHoods.clear();
    if (nh) selectedHoods.add(nh);
    var map = { 'hh-day-filter': hhFilters.day, 'hh-drink-filter': hhFilters.drink, 'hh-neighborhood-filter': nh };
    Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) el.value = map[id]; });
    if (modal) modal.classList.remove('active');
    renderHHView();
  });
  if (resetBtn) resetBtn.addEventListener('click', function () {
    ['hh-mobile-day-select', 'hh-mobile-drink-select', 'hh-mobile-neighborhood-select'].forEach(function (id) {
      var el = document.getElementById(id); if (el) el.value = '';
    });
    if (hhTimeSliderMobile) hhTimeSliderMobile.reset();
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
    if (!shown.length) { row.innerHTML = '<p style="color:#64748b;padding:20px;font-size:0.85rem;">Tap a neighborhood, then your happy hours show here.</p>'; return; }
    shown.forEach(function (bar) {
      var card = document.createElement('div');
      card.className = 'drawer-card';
      var ph = document.createElement('div');
      ph.className = 'drawer-card-thumb-placeholder';
      ph.innerHTML = '<i class="fa-solid fa-martini-glass-citrus"></i>';
      var body = document.createElement('div');
      body.className = 'drawer-card-body';
      body.innerHTML = '<div class="drawer-card-name">' + hhEsc(bar.name || '') + '</div>' +
        (bar.neighborhood || bar._nh ? '<div class="drawer-card-meta">' + hhEsc(bar.neighborhood || bar._nh) + '</div>' : '') +
        (bar.time_label ? '<div class="drawer-card-tags"><span class="drawer-card-tag">' + hhEsc(bar.time_label) + '</span></div>' : '');
      card.appendChild(ph); card.appendChild(body);
      card.addEventListener('click', function () {
        var m = bar._marker;
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

// ── Location services: "Near Me" (sorts the loaded points by distance) ─────────
if (window.LocationServices) {
  window.LocationServices.attach({
    map:           happyHourMap,
    getData:       function () { return getVisibleHH(); },
    getLatLng:     function (b) { return [b.lat, b.lng]; },
    getName:       function (b) { return b.name; },
    renderList:    function (d) { populateHHSidebar(d); },
    setDrawerData: function (d) { if (window._hhDrawerSetData) window._hhDrawerSetData(d); },
    listSelectors: ['#hh-bar-list', '#hh-drawer-cards'],
  });
}
