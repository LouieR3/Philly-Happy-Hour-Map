/* ============================================================
   MAPPY HOUR — LOCATION SERVICES (SCOPE Phase 3)
   Reusable "Near Me" behavior for any of the Leaflet maps:
     • Browser Geolocation prompt ("share location")
     • Distinct "you are here" marker
     • Re-sorts the map's sidebar/drawer list by straight-line
       distance and shows a per-row distance label ("0.3 mi")
     • One-tap toggle that preserves the map's other filters

   Distance is computed client-side (Haversine) over the bars already
   loaded for the map — no extra round trip and no geo-index/migration
   needed. (A server-side MongoDB $near endpoint could replace this
   later if the dataset outgrows client-side sorting.)

   Loaded before the per-map scripts; each map calls
   LocationServices.attach({...}) once.
   ============================================================ */
(function () {
  var EARTH_MI = 3958.8;

  function haversineMiles(lat1, lng1, lat2, lng2) {
    var toRad = function (d) { return d * Math.PI / 180; };
    var dLat = toRad(lat2 - lat1);
    var dLng = toRad(lng2 - lng1);
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return EARTH_MI * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function fmtMiles(mi) {
    if (mi == null || isNaN(mi) || mi === Infinity) return '';
    return (mi < 10 ? mi.toFixed(1) : Math.round(mi)) + ' mi';
  }

  // Position shared globally so map code / future features can read it.
  window.mappyUserLocation = null;
  window.mappyHaversineMiles = haversineMiles;

  function hereIcon() {
    return L.divIcon({
      className: 'mappy-here-wrap',
      html: '<div class="mappy-here-pin"></div>',
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });
  }

  window.LocationServices = {
    /**
     * cfg = {
     *   map,            // Leaflet map instance
     *   getData,        // () => array of bar rows (live data)
     *   getLatLng,      // (row) => [lat, lng]
     *   getName,        // (row) => display name (matches the .*-card-name text)
     *   renderList,     // (sortedRows) => void  — re-render the sidebar list
     *   setDrawerData,  // (sortedRows) => void  — optional, update mobile drawer
     *   listSelectors,  // [container selectors] to stamp distance badges into
     * }
     */
    attach: function (cfg) {
      var active = false;
      var hereMarker = null;
      var btn = null;

      function clearBadges() {
        document.querySelectorAll('.mappy-dist').forEach(function (b) { b.remove(); });
      }

      // Append a distance label after each card-name element whose text matches
      // a bar we measured. Post-processing the DOM keeps the per-map card
      // builders untouched.
      function setBadges(nameToDist) {
        clearBadges();
        if (!nameToDist) return;
        (cfg.listSelectors || []).forEach(function (sel) {
          var els = document.querySelectorAll(sel + ' .bar-card-name, ' + sel + ' .drawer-card-name');
          els.forEach(function (el) {
            var key = (el.textContent || '').trim();
            var d = nameToDist[key];
            if (d == null) return;
            var span = document.createElement('span');
            span.className = 'mappy-dist';
            span.textContent = fmtMiles(d);
            el.appendChild(span);
          });
        });
      }

      function activateWith(pos) {
        var lat = pos.coords.latitude, lng = pos.coords.longitude;
        window.mappyUserLocation = { lat: lat, lng: lng };

        if (hereMarker) cfg.map.removeLayer(hereMarker);
        hereMarker = L.marker([lat, lng], { icon: hereIcon(), interactive: false, zIndexOffset: 2000 }).addTo(cfg.map);
        cfg.map.setView([lat, lng], 14);

        var data = cfg.getData() || [];
        var measured = data.map(function (row) {
          var ll = cfg.getLatLng(row) || [];
          var ok = ll[0] != null && ll[1] != null && !isNaN(Number(ll[0])) && !isNaN(Number(ll[1]));
          return { row: row, d: ok ? haversineMiles(lat, lng, Number(ll[0]), Number(ll[1])) : Infinity };
        }).sort(function (a, b) { return a.d - b.d; });

        var sorted = measured.map(function (m) { return m.row; });
        var nameToDist = {};
        measured.forEach(function (m) {
          if (m.d !== Infinity) nameToDist[String(cfg.getName(m.row)).trim()] = m.d;
        });

        if (cfg.renderList) cfg.renderList(sorted);
        if (cfg.setDrawerData) cfg.setDrawerData(sorted);
        // Badges after the list paints.
        setTimeout(function () { setBadges(nameToDist); }, 0);

        active = true;
        if (btn) btn.classList.add('active');
        if (window.siteToast) window.siteToast('Showing bars nearest you.');
      }

      function deactivate() {
        active = false;
        window.mappyUserLocation = null;
        if (hereMarker) { cfg.map.removeLayer(hereMarker); hereMarker = null; }
        clearBadges();
        var data = cfg.getData() || [];
        if (cfg.renderList) cfg.renderList(data);       // restore original order
        if (cfg.setDrawerData) cfg.setDrawerData(data);
        if (btn) btn.classList.remove('active');
      }

      function toggle() {
        if (active) { deactivate(); return; }
        if (!navigator.geolocation) {
          if (window.siteToast) window.siteToast('Location is not supported by your browser.', 'error');
          return;
        }
        if (btn) btn.classList.add('loading');
        navigator.geolocation.getCurrentPosition(
          function (pos) { if (btn) btn.classList.remove('loading'); activateWith(pos); },
          function (err) {
            if (btn) btn.classList.remove('loading');
            var msg = err && err.code === 1 ? 'Location permission denied.' : 'Could not get your location.';
            if (window.siteToast) window.siteToast(msg, 'error');
          },
          { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
        );
      }

      var Ctrl = L.Control.extend({
        options: { position: 'topright' },
        onAdd: function () {
          var c = L.DomUtil.create('button', 'mappy-locate-btn');
          c.type = 'button';
          c.title = 'Find bars near me';
          c.setAttribute('aria-label', 'Find bars near me');
          c.innerHTML = '<i class="fa-solid fa-location-crosshairs" aria-hidden="true"></i><span>Near Me</span>';
          L.DomEvent.disableClickPropagation(c);
          L.DomEvent.on(c, 'click', toggle);
          btn = c;
          return c;
        }
      });
      cfg.map.addControl(new Ctrl());
    }
  };
})();
