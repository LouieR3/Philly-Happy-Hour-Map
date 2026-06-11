/* ============================================================
   MAPPY HOUR — MOBILE MAP HUB CONTROLLER
   Consolidates the three map sections into a tabbed, zero-scroll
   view on mobile (<= 991.98px). On desktop it does nothing — the
   page renders its normal scrolling sections.

   Pairs with css/map-hub.css and the #map-hub-tabs element.
   Must load AFTER the three map scripts so the map globals
   (leafletmap / poolMap / sportsMap) already exist.
   ============================================================ */
(function () {
  var MOBILE_MQ = window.matchMedia('(max-width: 991.98px)');

  // section id -> getter for that map's Leaflet instance (declared as
  // top-level `var`s in their map scripts, hence on window).
  var SECTIONS = [
    { sec: 'quizzo',      getMap: function () { return window.leafletmap; } },
    { sec: 'pool-bars',   getMap: function () { return window.poolMap; } },
    { sec: 'sports-bars', getMap: function () { return window.sportsMap; } },
  ];

  var tabsEl = document.getElementById('map-hub-tabs');
  var navEl  = document.getElementById('mainNav');
  if (!tabsEl) return;

  var current = null;

  // Measure the live navbar + tab-strip heights so the fixed shell starts
  // exactly below them (fonts/zoom can change these from the CSS fallbacks).
  function setVars() {
    var navH  = navEl  ? navEl.offsetHeight  : 56;
    var tabsH = tabsEl ? tabsEl.offsetHeight : 52;
    document.documentElement.style.setProperty('--hub-nav-h', navH + 'px');
    document.documentElement.style.setProperty('--hub-tabs-h', tabsH + 'px');
  }

  function sectionEl(sec) { return document.getElementById(sec); }

  // Leaflet maps initialized inside a hidden/resized container render gray
  // until invalidateSize() runs once they're visible at final dimensions.
  function invalidate(sec) {
    var entry = SECTIONS.filter(function (s) { return s.sec === sec; })[0];
    var m = entry && entry.getMap();
    if (m && typeof m.invalidateSize === 'function') {
      setTimeout(function () { m.invalidateSize(); }, 60);
    }
  }

  function activate(sec) {
    current = sec;
    document.body.classList.add('hub-active');
    SECTIONS.forEach(function (s) {
      var el = sectionEl(s.sec);
      if (el) {
        el.classList.add('hub-map');
        el.classList.toggle('hub-current', s.sec === sec);
      }
    });
    Array.prototype.forEach.call(tabsEl.querySelectorAll('.hub-tab'), function (t) {
      t.classList.toggle('active', t.getAttribute('data-section') === sec);
    });
    setVars();
    invalidate(sec);
  }

  function exitHub() {
    current = null;
    document.body.classList.remove('hub-active');
    SECTIONS.forEach(function (s) {
      var el = sectionEl(s.sec);
      if (el) el.classList.remove('hub-current');
    });
    Array.prototype.forEach.call(tabsEl.querySelectorAll('.hub-tab'), function (t) {
      t.classList.remove('active');
    });
  }

  // ── Tab clicks ───────────────────────────────────────────────
  tabsEl.addEventListener('click', function (e) {
    var btn = e.target.closest('.hub-tab');
    if (!btn) return;
    if (btn.classList.contains('hub-tab-locked')) {
      if (typeof window.siteToast === 'function') {
        window.siteToast('Happy Hour map is coming soon!');
      }
      return;
    }
    var sec = btn.getAttribute('data-section');
    if (sec) activate(sec);
  });

  // ── Navbar links ─────────────────────────────────────────────
  // On mobile, map links re-enter the hub on the right tab; non-map links
  // (About, Bar Map, brand) exit the hub so the full page scrolls normally —
  // this keeps the marketing/About content reachable on mobile.
  var MAP_HASHES = { '#quizzo': 'quizzo', '#pool-bars': 'pool-bars', '#sports-bars': 'sports-bars' };
  function collapseNav() {
    var c = document.getElementById('navbarResponsive');
    if (!c || !c.classList.contains('show')) return;
    if (window.bootstrap && window.bootstrap.Collapse) {
      var inst = window.bootstrap.Collapse.getInstance(c) || new window.bootstrap.Collapse(c, { toggle: false });
      inst.hide();
    } else {
      c.classList.remove('show');
    }
  }
  Array.prototype.forEach.call(
    document.querySelectorAll('#mainNav a.nav-link, #mainNav .navbar-brand'),
    function (a) {
      a.addEventListener('click', function (e) {
        if (!MOBILE_MQ.matches) return;
        var href = a.getAttribute('href') || '';
        if (MAP_HASHES[href]) {
          e.preventDefault();
          activate(MAP_HASHES[href]);
        } else {
          exitHub();   // let the default anchor scroll to About / Bar Map
        }
        collapseNav();
      });
    }
  );

  // ── Viewport sync ────────────────────────────────────────────
  function syncToViewport() {
    if (MOBILE_MQ.matches) {
      if (!current) activate(SECTIONS[0].sec); // default: first map (Quizzo)
      else { setVars(); invalidate(current); }
    } else {
      exitHub();
    }
  }

  function init() {
    // Tag the map sections up front so the CSS catch-all can target them.
    SECTIONS.forEach(function (s) {
      var el = sectionEl(s.sec);
      if (el) el.classList.add('hub-map');
    });
    setVars();
    syncToViewport();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  // Re-measure once everything (fonts, navbar) has fully painted.
  window.addEventListener('load', function () { setVars(); if (current) invalidate(current); });

  if (MOBILE_MQ.addEventListener) MOBILE_MQ.addEventListener('change', syncToViewport);
  else if (MOBILE_MQ.addListener) MOBILE_MQ.addListener(syncToViewport);

  window.addEventListener('resize', function () { if (current) setVars(); });
})();
