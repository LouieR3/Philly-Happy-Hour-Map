const POOL_API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:3000'
  : 'https://philly-happy-hour-map-production.up.railway.app';
console.log(POOL_API_BASE);
// ─── Map init ─────────────────────────────────────────────────────────────────
var poolMap = L.map('pool-leaflet-map').setView([39.951, -75.163], 12);
poolMap.zoomControl.setPosition('bottomright');

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap & CartoDB',
  subdomains: 'abcd',
}).addTo(poolMap);

// ─── Marker icon ──────────────────────────────────────────────────────────────
function createPoolIcon(color = '#10b981') {
  return L.divIcon({
    html: `<div class="custom-pin">
      <div class="pin-circle" style="background-color:${color};">
        <i class="fa-solid fa-circle-dot" style="font-size:11px;"></i>
      </div>
      <div class="pin-tail" style="background-color:${color};"></div>
    </div>`,
    className: 'custom-fa-icon',
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });
}

function paymentColor(model) {
  if (!model) return '#10b981';
  const m = model.toLowerCase();
  if (m.includes('coin'))              return '#60a5fa';   // blue
  if (m.includes('hour'))              return '#fbbf24';   // yellow
  if (m.includes('free'))              return '#c084fc';   // purple
  return '#34d399';                                        // green (per_game / default)
}

// ─── Filter state ─────────────────────────────────────────────────────────────
var poolMarkers = [];
var poolAllData = [];
var poolGeoJson = null;

function getNhFromLatLng(lat, lng, geoJson) {
  if (!geoJson || !window.turf) return null;
  const pt = turf.point([lng, lat]);
  for (const feature of geoJson.features) {
    try {
      if (turf.booleanPointInPolygon(pt, feature)) return feature.properties.LISTNAME || null;
    } catch(e) {}
  }
  return null;
}
const poolActiveFilters = {
  paymentModel: null,
  minTables:    null,
  hasHappyHour: false,
  hasLeague:    false,
  neighborhood: null,
  region:       null,
};

function applyPoolFilters() {
  poolMarkers.forEach((marker) => {
    if (!(marker instanceof L.Marker)) return;
    const passes =
      (!poolActiveFilters.paymentModel || marker.paymentModel === poolActiveFilters.paymentModel) &&
      (poolActiveFilters.minTables === null || marker.tableCount >= poolActiveFilters.minTables) &&
      (!poolActiveFilters.hasHappyHour || marker.hasHappyHour) &&
      (!poolActiveFilters.hasLeague    || marker.hasLeague) &&
      (!poolActiveFilters.neighborhood || marker.neighborhood === poolActiveFilters.neighborhood);
    if (passes) {
      if (!poolMap.hasLayer(marker)) marker.addTo(poolMap);
    } else {
      if (poolMap.hasLayer(marker)) poolMap.removeLayer(marker);
    }
  });
}

function setPoolFilterLabel(buttonId, text) {
  const el = document.querySelector(`#${buttonId} .filter-label`);
  if (el) el.textContent = text;
}
function setPoolFilterActive(buttonId, isActive) {
  const btn = document.getElementById(buttonId);
  if (btn) btn.classList.toggle('filter-active', isActive);
}

// ─── Load data ────────────────────────────────────────────────────────────────
fetch(`${POOL_API_BASE}/api/pool-bars`)
  .then((res) => res.json())
  .then((data) => {
    poolAllData = data;

    // Populate Payment Model dropdown
    const paymentModels = [...new Set(data.map((d) => d.Payment_Model).filter(Boolean))].sort();
    const pmOptions = document.getElementById('pool-payment-options');
    paymentModels.forEach((pm) => {
      const li = document.createElement('li');
      li.className = 'pool-payment-option';
      li.textContent = pm;
      li.addEventListener('click', () => {
        poolActiveFilters.paymentModel = pm;
        setPoolFilterLabel('pool-payment-button', pm);
        setPoolFilterActive('pool-payment-button', true);
        document.getElementById('pool-payment-dropdown').style.display = 'none';
        applyPoolFilters();
      });
      pmOptions.appendChild(li);
    });
    const allPm = document.createElement('li');
    allPm.className = 'pool-payment-option';
    allPm.textContent = 'All';
    allPm.addEventListener('click', () => {
      poolActiveFilters.paymentModel = null;
      setPoolFilterLabel('pool-payment-button', 'Payment');
      setPoolFilterActive('pool-payment-button', false);
      document.getElementById('pool-payment-dropdown').style.display = 'none';
      applyPoolFilters();
    });
    pmOptions.prepend(allPm);

    // Create markers
    const markerGroup = L.layerGroup().addTo(poolMap);
    data.forEach((row, i) => {
      const lat = parseFloat(row.Latitude);
      const lng = parseFloat(row.Longitude);
      if (isNaN(lat) || isNaN(lng)) return;
      const pay_model = row.Payment_Model;

      const pmLower = (row.Payment_Model || '').toLowerCase();
      const costLine = pmLower === 'per hour' || pmLower === 'hourly'
        ? (row.Cost_Per_Hour ? `$${row.Cost_Per_Hour} per hour` : '')
        : pmLower === 'per game'
          ? (row.Cost_Per_Game ? `$${row.Cost_Per_Game} per game` : '')
          : '';

      const color = paymentColor(row.Payment_Model);
      const popupContent = `
        <div style="font-family:'Red Hat Text',sans-serif;width:240px;border-radius:8px;overflow:hidden;">
          <div style="background:#065a20;padding:14px 16px 10px;">
            <p style="margin:0;font-size:15px;font-weight:600;color:#fff;">🎱 ${row.Name || '—'}</p>
            <p style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,0.7);">${row.Address || ''}</p>
            <p style="margin:4px 0 0;font-size:14px;color:rgba(255,255,255);">${row.Neighborhood || ''}</p>
          </div>
          <div style="padding:12px 16px;display:flex;flex-direction:column;gap:8px;background:#1a2332;color:#e2e8f0;">
            ${row.Number_of_Tables ? `<div style="font-size:16px;"><b>${row.Number_of_Tables}</b> table${row.Number_of_Tables !== 1 ? 's' : ''} - ${costLine}</div>` : ''}
            ${row.Vibe ? `<div style="font-size:14px;color:#fff;">What's the vibe? <b>${row.Vibe}</b></div>` : ''}
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:2px;">
              ${row.Has_Happy_Hour ? `<span style="background:rgba(52,211,153,0.12);color:#34d399;font-size:14px;font-weight:600;padding:2px 8px;border-radius:20px;">Happy Hour</span>` : ''}
              ${row.Has_League    ? `<span style="background:rgba(96,165,250,0.12);color:#60a5fa;font-size:14px;font-weight:600;padding:2px 8px;border-radius:20px;">Has League</span>` : ''}
              ${row['Yelp Rating'] ? `<span style="background:rgba(251,191,36,0.12);color:#fbbf24;font-size:14px;font-weight:600;padding:2px 8px;border-radius:20px;">⭐ ${row['Yelp Rating']}</span>` : ''}
              ${row.Price ? `<span style="background:rgba(74, 150, 93, 0.82);color:#fff;font-size:14px;font-weight:600;padding:2px 8px;border-radius:20px;">Price: ${row.Price}</span>` : ''}
            </div>
            ${row.Website ? `<a href="${row.Website}" target="_blank" style="font-size:14px;color:#34d399;text-decoration:none;margin-top:2px;">Visit Website →</a>` : ''}
          </div>
        </div>`;

      const marker = L.marker([lat, lng], { icon: createPoolIcon(color) }).bindPopup(popupContent, { maxWidth: 260 });
      marker.paymentModel = row.Payment_Model || null;
      marker.tableCount   = row.Number_of_Tables ? Number(row.Number_of_Tables) : 0;
      marker.hasHappyHour = !!row.Has_Happy_Hour;
      marker.hasLeague    = !!row.Has_League;
      marker.name         = row.Name;
      marker.rowIndex     = i;
      marker.neighborhood = row.Neighborhood || null;
      marker.region       = row.Philly_Region || null;
      poolMarkers.push(marker);
      marker.addTo(poolMap);
      markerGroup.addLayer(marker);
    });

    populatePoolTable(data);

    // ── Custom map search overlay ──────────────────────────────────────────
    const PoolSearchControl = L.Control.extend({
      options: { position: 'topleft' },
      onAdd: function() {
        const c = L.DomUtil.create('div', 'map-search-control');
        c.innerHTML = '<input type="text" id="pool-map-search-field" placeholder="Search bars\u2026" autocomplete="off" /><ul id="pool-map-search-list"></ul>';
        L.DomEvent.disableClickPropagation(c);
        L.DomEvent.disableScrollPropagation(c);
        return c;
      }
    });
    poolMap.addControl(new PoolSearchControl());

    document.getElementById('pool-map-search-field').addEventListener('input', function() {
      const q = this.value.trim().toLowerCase();
      const list = document.getElementById('pool-map-search-list');
      list.innerHTML = '';
      if (q.length < 2) return;
      poolMarkers
        .filter(m => m.name && m.name.toLowerCase().includes(q))
        .slice(0, 8)
        .forEach(m => {
          const li = document.createElement('li');
          li.textContent = m.name;
          li.addEventListener('click', () => {
            poolMap.setView(m.getLatLng(), 16);
            m.openPopup();
            document.getElementById('pool-map-search-field').value = m.name;
            list.innerHTML = '';
          });
          list.appendChild(li);
        });
    });

    document.addEventListener('click', function(e) {
      const field = document.getElementById('pool-map-search-field');
      const list  = document.getElementById('pool-map-search-list');
      if (field && list && !field.contains(e.target) && !list.contains(e.target)) {
        list.innerHTML = '';
      }
    });

    // ── GeoJSON-based Region + Neighborhood filters for pool bars ─────────
    fetch('assets/philadelphia-neighborhoods.geojson')
      .then(r => r.json())
      .then(function(geoJson) {
        poolGeoJson = geoJson;
        const nhHasMarker     = {};  // LISTNAME → feature
        const regionHasMarker = {};  // GENERAL_AREA → [features]

        poolMarkers.forEach(function(marker) {
          const pt = turf.point([marker.getLatLng().lng, marker.getLatLng().lat]);
          geoJson.features.forEach(function(feature) {
            try {
              if (turf.booleanPointInPolygon(pt, feature)) {
                const name   = feature.properties.LISTNAME;
                const region = (feature.properties.GENERAL_AREA || '').trim();
                if (!nhHasMarker[name]) nhHasMarker[name] = feature;
                if (region) {
                  if (!regionHasMarker[region]) regionHasMarker[region] = [];
                  regionHasMarker[region].push(feature);
                }
              }
            } catch(e) {}
          });
        });

        function zoomPoolToFeatures(features) {
          const bbox = turf.bbox(turf.featureCollection(features));
          poolMap.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], { padding: [30, 30] });
        }

        const POOL_DD_STYLE = 'padding:7px 12px;cursor:pointer;color:#e2e8f0;';
        const POOL_DD_HOVER_IN  = function() { this.style.background = 'rgba(255,255,255,0.08)'; };
        const POOL_DD_HOVER_OUT = function() { this.style.background = ''; };

        function makeLi(text, onClick) {
          const li = document.createElement('li');
          li.style.cssText = POOL_DD_STYLE;
          li.textContent   = text;
          li.addEventListener('mouseover', POOL_DD_HOVER_IN);
          li.addEventListener('mouseout',  POOL_DD_HOVER_OUT);
          li.addEventListener('click', onClick);
          return li;
        }

        // ── Region dropdown ───────────────────────────────────────────────
        const regionOpts    = document.getElementById('pool-region-options');
        const sortedRegions = Object.keys(regionHasMarker).sort();

        regionOpts.appendChild(makeLi('All', () => {
          poolActiveFilters.region      = null;
          poolActiveFilters.neighborhood = null;
          setPoolFilterLabel('pool-region-button', 'Region');
          setPoolFilterActive('pool-region-button', false);
          document.getElementById('pool-region-dropdown').style.display = 'none';
          buildPoolNeighborhoodList(nhHasMarker, null);
          applyPoolFilters();
          poolMap.setView([39.951, -75.163], 12);
        }));

        sortedRegions.forEach(region => {
          regionOpts.appendChild(makeLi(region, () => {
            poolActiveFilters.region      = region;
            poolActiveFilters.neighborhood = null;
            setPoolFilterLabel('pool-region-button', region);
            setPoolFilterActive('pool-region-button', true);
            document.getElementById('pool-region-dropdown').style.display = 'none';
            buildPoolNeighborhoodList(nhHasMarker, region);
            applyPoolFilters();
            zoomPoolToFeatures(regionHasMarker[region]);
          }));
        });

        setupPoolDropdown('pool-region-button', 'pool-region-dropdown');

        // ── Neighborhood dropdown ─────────────────────────────────────────
        function buildPoolNeighborhoodList(nhMap, filterRegion) {
          const opts  = document.getElementById('pool-neighborhood-options');
          opts.innerHTML = '';

          opts.appendChild(makeLi('All', () => {
            poolActiveFilters.neighborhood = null;
            setPoolFilterLabel('pool-neighborhood-button', 'Neighborhood');
            setPoolFilterActive('pool-neighborhood-button', false);
            document.getElementById('pool-neighborhood-dropdown').style.display = 'none';
            applyPoolFilters();
          }));

          let names = Object.keys(nhMap).sort();
          if (filterRegion) {
            names = names.filter(n => (nhMap[n].properties.GENERAL_AREA || '').trim() === filterRegion);
          }

          names.forEach(name => {
            const feature = nhMap[name];
            opts.appendChild(makeLi(name, () => {
              poolActiveFilters.neighborhood = name;
              setPoolFilterLabel('pool-neighborhood-button', name);
              setPoolFilterActive('pool-neighborhood-button', true);
              document.getElementById('pool-neighborhood-dropdown').style.display = 'none';
              applyPoolFilters();
              zoomPoolToFeatures([feature]);
            }));
          });
        }

        buildPoolNeighborhoodList(nhHasMarker, null);
        setupPoolDropdown('pool-neighborhood-button', 'pool-neighborhood-dropdown');

        // Mobile filter options
        if (typeof populatePoolMobileFilterOptions === 'function') {
          populatePoolMobileFilterOptions({
            neighborhoods: Object.keys(nhHasMarker).sort(),
            regions:       sortedRegions,
          });
        }
      });
  })
  .catch((err) => console.error('Failed to load pool bars:', err));

// ─── Table population ─────────────────────────────────────────────────────────
function populatePoolTable(data) {
  const tbody = document.querySelector('#pool-bar-table tbody');
  tbody.innerHTML = '';
  const sorted = [...data].sort((a, b) => (Number(b.Number_of_Tables) || 0) - (Number(a.Number_of_Tables) || 0));
  sorted.forEach((row, i) => {
    if (!row.Name) return;
    const cost = row.Payment_Model === 'Per Hour'
      ? (row.Cost_Per_Hour  ? `$${row.Cost_Per_Hour}/hr`  : '—')
      : (row.Cost_Per_Game  ? `$${row.Cost_Per_Game}`     : '—');
    const tr = document.createElement('tr');
    
    const pay_model = row.Payment_Model;
    tr.innerHTML = `
      <td>${row.Name}</td>
      <td>${row.Number_of_Tables ?? '?'}</td>
      <td>${row.Payment_Model ?? '—'}</td>
      <td>${cost}</td>`;
    tr.addEventListener('click', () => {
      const marker = poolMarkers.find((m) => m.name === row.Name);
      if (marker) { poolMap.setView(marker.getLatLng(), 16); marker.openPopup(); }
    });
    tbody.appendChild(tr);
  });
}
// ── Pool bar search (prepopulate from bars collection) ────────────────────
const poolSearchInput = document.getElementById('pool-search-input');
const poolSearchResultsList = document.getElementById('pool-search-results-list');

// Only set up search if elements exist (for admin panel)
if (poolSearchInput && poolSearchResultsList) {
  poolSearchInput.addEventListener('input', async (e) => {
      const q = e.target.value.trim();
      if (q.length < 2) {
          poolSearchResultsList.innerHTML = '';
          return;
      }

      try {
          const res = await fetch(`${POOL_API_BASE}/api/search-bars?q=${encodeURIComponent(q)}`);
          const bars = await res.json();

          poolSearchResultsList.innerHTML = '';
          bars.forEach(bar => {
              const li = document.createElement('li');
              li.style.padding = '10px';
              li.style.cursor = 'pointer';
              li.style.borderBottom = '1px solid #334155';
              li.innerHTML = `<strong>${bar.Name}</strong><br><small style="color:#94a3b8">${bar.Address || ''}</small>`;
              
              li.onclick = () => {
                  document.getElementById('pool-business-name').value = bar.Name || '';
                  document.getElementById('pool-street-address').value = bar.Address || '';
                  document.getElementById('pool-lat').value = bar.Latitude || '';
                  document.getElementById('pool-lng').value = bar.Longitude || '';
                  const nh = getNhFromLatLng(bar.Latitude, bar.Longitude, poolGeoJson);
                  document.getElementById('pool-neighborhood-input').value = nh || '';
                  document.getElementById("pool-yelp-alias").value = bar["Yelp Alias"] || "";

                  if (bar["Sunday"]) document.getElementById("pool-Sunday").value = bar.Sunday;
                  if (bar["Monday"]) document.getElementById("pool-Monday").value = bar.Monday;
                  if (bar["Tuesday"]) document.getElementById("pool-Tuesday").value = bar.Tuesday;
                  if (bar["Wednesday"]) document.getElementById("pool-Wednesday").value = bar.Wednesday;
                  if (bar["Thursday"]) document.getElementById("pool-Thursday").value = bar.Thursday;
                  if (bar["Friday"]) document.getElementById("pool-Friday").value = bar.Friday;
                  if (bar["Saturday"]) document.getElementById("pool-Saturday").value = bar.Saturday;
                  poolSearchInput.value = bar.Name;
                  poolSearchResultsList.innerHTML = '';
              };
              poolSearchResultsList.appendChild(li);
          });
      } catch (err) {
          console.error('Search error:', err);
      }
  });

  document.addEventListener('click', (e) => {
    const poolSearchResults = document.getElementById('pool-search-results');
    if (poolSearchResults &&
        !poolSearchInput.contains(e.target) && !poolSearchResults.contains(e.target)) {
      poolSearchResultsList.innerHTML = '';
    }
  });
}

// ─── Table search ─────────────────────────────────────────────────────────────
document.getElementById('pool-bar-search').addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase();
  document.querySelectorAll('#pool-bar-table tbody tr').forEach((row) => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
});

// ─── Dropdown toggles ─────────────────────────────────────────────────────────
function setupPoolDropdown(buttonId, dropdownId) {
  const btn = document.getElementById(buttonId);
  const dd  = document.getElementById(dropdownId);
  if (!btn || !dd) return;
  btn.addEventListener('click', () => {
    const visible = dd.style.display === 'block';
    document.querySelectorAll('#pool-filters [id$="-dropdown"]').forEach((el) => (el.style.display = 'none'));
    dd.style.display = visible ? 'none' : 'block';
  });
  document.addEventListener('click', (e) => {
    if (!btn.contains(e.target) && !dd.contains(e.target)) dd.style.display = 'none';
  });
}
setupPoolDropdown('pool-payment-button', 'pool-payment-dropdown');
setupPoolDropdown('pool-tables-button',  'pool-tables-dropdown');

// Tables filter options (static in HTML)
document.querySelectorAll('.pool-tables-option').forEach((opt) => {
  opt.addEventListener('click', () => {
    const val = opt.getAttribute('data-value');
    if (val === 'All') {
      poolActiveFilters.minTables = null;
      setPoolFilterLabel('pool-tables-button', 'Tables');
      setPoolFilterActive('pool-tables-button', false);
    } else {
      poolActiveFilters.minTables = parseInt(val);
      setPoolFilterLabel('pool-tables-button', `${val}+ Tables`);
      setPoolFilterActive('pool-tables-button', true);
    }
    document.getElementById('pool-tables-dropdown').style.display = 'none';
    applyPoolFilters();
  });
});

// Happy Hour toggle
document.getElementById('pool-hh-button').addEventListener('click', () => {
  poolActiveFilters.hasHappyHour = !poolActiveFilters.hasHappyHour;
  setPoolFilterActive('pool-hh-button', poolActiveFilters.hasHappyHour);
  applyPoolFilters();
});

// League toggle
document.getElementById('pool-league-button').addEventListener('click', () => {
  poolActiveFilters.hasLeague = !poolActiveFilters.hasLeague;
  setPoolFilterActive('pool-league-button', poolActiveFilters.hasLeague);
  applyPoolFilters();
});

// Reset
document.getElementById('pool-reset-button').addEventListener('click', () => {
  poolActiveFilters.paymentModel  = null;
  poolActiveFilters.minTables     = null;
  poolActiveFilters.hasHappyHour  = false;
  poolActiveFilters.hasLeague     = false;
  poolActiveFilters.neighborhood  = null;
  poolActiveFilters.region        = null;
  setPoolFilterLabel('pool-payment-button',      'Payment');
  setPoolFilterActive('pool-payment-button',     false);
  setPoolFilterLabel('pool-tables-button',       'Tables');
  setPoolFilterActive('pool-tables-button',      false);
  setPoolFilterLabel('pool-region-button',       'Region');
  setPoolFilterActive('pool-region-button',      false);
  setPoolFilterLabel('pool-neighborhood-button', 'Neighborhood');
  setPoolFilterActive('pool-neighborhood-button',false);
  setPoolFilterActive('pool-hh-button',          false);
  setPoolFilterActive('pool-league-button',      false);
  poolMap.setView([39.951, -75.163], 12);
  applyPoolFilters();
});

// ─── Add / Edit modals ────────────────────────────────────────────────────────
document.getElementById('add-pool-bar-button').addEventListener('click', () => {
  new bootstrap.Modal(document.getElementById('addPoolBarModal')).show();
});
document.getElementById('edit-pool-bar-button').addEventListener('click', () => {
  new bootstrap.Modal(document.getElementById('editPoolBarModal')).show();
});

// Philly toggle in add pool bar form
document.querySelectorAll('input[name="poolIsPhiladelphia"]').forEach((radio) => {
  radio.addEventListener('change', () => {
    const isPhilly = document.getElementById('pool-philly-yes').checked;
    document.getElementById('pool-city-state-zip-fields').style.display = isPhilly ? 'none' : 'block';
  });
});

// Cost field visibility based on payment model
document.getElementById('pool-payment-model-select').addEventListener('change', function () {
  const v = this.value;
  document.getElementById('pool-cost-game-field').style.display = (v === 'Coin-op' || v === 'Per Game') ? 'block' : 'none';
  document.getElementById('pool-cost-hour-field').style.display = (v === 'Hourly') ? 'block' : 'none';
});

// Submit new pool bar
document.getElementById('pool-bar-submission-form').addEventListener('submit', async function (e) {
  e.preventDefault();
  const isPhilly      = document.getElementById('pool-philly-yes').checked;
  const streetAddress = document.getElementById('pool-street-address').value;
  
  let lat = parseFloat(document.getElementById('pool-lat').value) || null;
  let lng = parseFloat(document.getElementById('pool-lng').value) || null;
  
  let fullAddress = streetAddress;
  if (!lat || !lng) {
    const city  = isPhilly ? 'Philadelphia' : document.getElementById('pool-address-city').value;
    const state = isPhilly ? 'PA' : document.getElementById('pool-address-state').value;
    const zip   = isPhilly ? '' : document.getElementById('pool-address-zip').value;
    fullAddress = `${streetAddress}, ${city}, ${state}${zip ? ' ' + zip : ''}`;
    
    try {
      const geo = await fetch(`${POOL_API_BASE}/api/geocode?address=${encodeURIComponent(fullAddress)}`);
      const gd  = await geo.json();
      lat = gd.lat; lng = gd.lng;
    } catch (_) {}
  }

  const neighborhood = (isPhilly && lat && lng) ? (getNhFromLatLng(lat, lng, poolGeoJson) || '') : '';

  const payModel = document.getElementById('pool-payment-model-select').value;
  const submission = {
    name:          document.getElementById('pool-business-name').value,
    yelpAlias:     document.getElementById('pool-yelp-alias').value || null,
    streetAddress, city, state, zip, Latitude: lat, Longitude: lng,
    neighborhood,
    numTables:     document.getElementById('pool-num-tables').value || null,
    paymentModel:  payModel,
    costPerGame:   document.getElementById('pool-cost-per-game').value || null,
    costPerHour:   document.getElementById('pool-cost-per-hour').value || null,
    notes:         document.getElementById('pool-sub-notes').value,
  };

  fetch(`${POOL_API_BASE}/submit-pool-bar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(submission),
  })
    .then((r) => r.json())
    .then(() => {
      siteToast('Your pool bar has been submitted for review — thanks!');
      document.getElementById('pool-bar-submission-form').reset();
      document.getElementById('pool-cost-game-field').style.display = 'none';
      document.getElementById('pool-cost-hour-field').style.display = 'none';
      bootstrap.Modal.getInstance(document.getElementById('addPoolBarModal')).hide();
    })
    .catch(() => siteToast('Error submitting. Please try again.', 'error'));
});

// Edit pool bar — search
// Note: uses 'pool-edit-search-results' to avoid ID collision with add modal
const poolSearchBar      = document.getElementById('pool-search-bar');
const poolEditResultsEl  = document.getElementById('pool-edit-search-results');
const poolEditFields     = document.getElementById('pool-edit-fields');
 
if (poolSearchBar) {
  poolSearchBar.addEventListener('input', async () => {
    const q = poolSearchBar.value.trim().toLowerCase();
    poolEditResultsEl.innerHTML = '';
    if (q.length < 2) return;
 
    // First try poolAllData (already loaded from /api/pool-bars)
    let matches = poolAllData.filter((d) => d.Name && d.Name.toLowerCase().includes(q));
 
    // If poolAllData is empty (not yet loaded), fetch from API
    if (poolAllData.length === 0) {
      try {
        const res  = await fetch(`${POOL_API_BASE}/api/pool-bars`);
        const data = await res.json();
        poolAllData = data;
        matches = data.filter((d) => d.Name && d.Name.toLowerCase().includes(q));
      } catch (err) {
        console.error('Pool bar fetch error:', err);
      }
    }
 
    matches.forEach((bar) => {
      const li = document.createElement('li');
      li.className = 'search-option';
      li.style.cssText = 'cursor:pointer;padding:8px 4px;border-bottom:1px solid #dee2e6;';
      li.innerHTML = `<strong>${bar.Name}</strong><br><small style="color:#6c757d;">${bar.Address || ''}</small>`;
      li.addEventListener('click', () => {
        document.getElementById('pool-edit-name').value          = bar.Name;
        document.getElementById('pool-edit-address').value       = bar.Address || '';
        document.getElementById('pool-edit-num-tables').value    = bar.Number_of_Tables || '';
        document.getElementById('pool-edit-payment-model').value = bar.Payment_Model || '';
        document.getElementById('pool-edit-cost-per-game').value = bar.Cost_Per_Game || '';
        document.getElementById('pool-edit-cost-per-hour').value = bar.Cost_Per_Hour || '';
        document.getElementById('pool-edit-original-id').value   = bar._id || '';
        updateEditCostFields(bar.Payment_Model || '');
        poolEditFields.style.display = 'block';
        poolEditResultsEl.innerHTML  = '';
        poolSearchBar.value = bar.Name;
      });
      poolEditResultsEl.appendChild(li);
    });
  });
}

// Edit modal — cost field visibility
function updateEditCostFields(val) {
  const v = (val || '').toLowerCase();
  document.getElementById('pool-edit-cost-game-field').style.display = v.includes('game') ? 'block' : 'none';
  document.getElementById('pool-edit-cost-hour-field').style.display = v.includes('hour') ? 'block' : 'none';
}

document.getElementById('pool-edit-payment-model').addEventListener('change', function() {
  updateEditCostFields(this.value);
});

// Submit pool bar edit
document.getElementById('pool-edit-form').addEventListener('submit', async function (e) {
  e.preventDefault();
  const originalId   = document.getElementById('pool-edit-original-id').value;
  const originalName = document.getElementById('pool-edit-name').value;
  const changes = {
    Name:             document.getElementById('pool-edit-name').value,
    Address:          document.getElementById('pool-edit-address').value,
    Number_of_Tables: document.getElementById('pool-edit-num-tables').value    || undefined,
    Payment_Model:    document.getElementById('pool-edit-payment-model').value  || undefined,
    Cost_Per_Game:    document.getElementById('pool-edit-cost-per-game').value  || undefined,
    Cost_Per_Hour:    document.getElementById('pool-edit-cost-per-hour').value  || undefined,
  };
  const notes = document.getElementById('pool-edit-notes').value;
 
  fetch(`${POOL_API_BASE}/submit-pool-bar-edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ originalId, originalName, changes, notes }),
  })
    .then((r) => r.json())
    .then(() => {
      siteToast('Edit submitted for review — thanks!');
      document.getElementById('pool-edit-form').reset();
      poolEditFields.style.display = 'none';
      bootstrap.Modal.getInstance(document.getElementById('editPoolBarModal')).hide();
    })
    .catch(() => siteToast('Error submitting edit.', 'error'));
});