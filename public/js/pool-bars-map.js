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
  if (m.includes('coin'))    return '#60a5fa';
  if (m.includes('hourly'))  return '#34d399';
  if (m.includes('free'))    return '#c084fc';
  return '#fbbf24';
}

// ─── Filter state ─────────────────────────────────────────────────────────────
var poolMarkers = [];
var poolAllData = [];
const poolActiveFilters = {
  paymentModel: null,
  minTables:    null,
  hasHappyHour: false,
  hasLeague:    false,
};

function applyPoolFilters() {
  poolMarkers.forEach((marker) => {
    if (!(marker instanceof L.Marker)) return;
    const passes =
      (!poolActiveFilters.paymentModel || marker.paymentModel === poolActiveFilters.paymentModel) &&
      (poolActiveFilters.minTables === null || marker.tableCount >= poolActiveFilters.minTables) &&
      (!poolActiveFilters.hasHappyHour || marker.hasHappyHour) &&
      (!poolActiveFilters.hasLeague    || marker.hasLeague);
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
      const pay_model = !row.Payment_Model ? 'Unknown' : 
        row.Payment_Model.toLowerCase() === 'per_game' ? 'Per Game' :
        row.Payment_Model.toLowerCase() === 'per_hour' ? 'Per Hour' :
        row.Payment_Model;

      const pmLower = (row.Payment_Model || '').toLowerCase();
      const costLine = pmLower === 'per_hour' || pmLower === 'hourly'
        ? (row.Cost_Per_Hour ? `$${row.Cost_Per_Hour}/hr` : '')
        : pmLower === 'per_game'
          ? (row.Cost_Per_Game ? `$${row.Cost_Per_Game}/game` : '')
          : '';

      const color = paymentColor(row.Payment_Model);
      const popupContent = `
        <div style="font-family:'Red Hat Text',sans-serif;width:240px;border-radius:8px;overflow:hidden;">
          <div style="background:#065a20;padding:14px 16px 10px;">
            <p style="margin:0;font-size:15px;font-weight:600;color:#fff;">${row.Name || '—'}</p>
            <p style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,0.7);">${row.Address || ''}</p>
          </div>
          <div style="padding:12px 16px;display:flex;flex-direction:column;gap:8px;background:#1a2332;color:#e2e8f0;">
            ${row.Number_of_Tables ? `<div style="font-size:13px;">🎱 <b>${row.Number_of_Tables}</b> table${row.Number_of_Tables !== 1 ? 's' : ''}</div>` : ''}
            ${pay_model ? `<div style="font-size:13px;">💳 <b>${pay_model}</b>${costLine ? ' · ' + costLine : ''}</div>` : ''}
            ${row.Vibe ? `<div style="font-size:12px;color:#94a3b8;">${row.Vibe}</div>` : ''}
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:2px;">
              ${row.Has_Happy_Hour ? `<span style="background:rgba(52,211,153,0.12);color:#34d399;font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px;">Happy Hour</span>` : ''}
              ${row.Has_League    ? `<span style="background:rgba(96,165,250,0.12);color:#60a5fa;font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px;">Has League</span>` : ''}
              ${row['Yelp Rating'] ? `<span style="background:rgba(251,191,36,0.12);color:#fbbf24;font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px;">⭐ ${row['Yelp Rating']}</span>` : ''}
            </div>
            ${row.Website ? `<a href="${row.Website}" target="_blank" style="font-size:12px;color:#34d399;text-decoration:none;margin-top:2px;">Visit Website →</a>` : ''}
          </div>
        </div>`;

      const marker = L.marker([lat, lng], { icon: createPoolIcon(color) }).bindPopup(popupContent, { maxWidth: 260 });
      marker.paymentModel = row.Payment_Model || null;
      marker.tableCount   = row.Number_of_Tables ? Number(row.Number_of_Tables) : 0;
      marker.hasHappyHour = !!row.Has_Happy_Hour;
      marker.hasLeague    = !!row.Has_League;
      marker.name         = row.Name;
      marker.rowIndex     = i;
      poolMarkers.push(marker);
      marker.addTo(poolMap);
      markerGroup.addLayer(marker);
    });

    populatePoolTable(data);
  })
  .catch((err) => console.error('Failed to load pool bars:', err));

// ─── Table population ─────────────────────────────────────────────────────────
function populatePoolTable(data) {
  const tbody = document.querySelector('#pool-bar-table tbody');
  tbody.innerHTML = '';
  data.forEach((row, i) => {
    if (!row.Name) return;
    const cost = row.Payment_Model === 'Hourly'
      ? (row.Cost_Per_Hour  ? `$${row.Cost_Per_Hour}/hr`  : '—')
      : (row.Cost_Per_Game  ? `$${row.Cost_Per_Game}`     : '—');
    const tr = document.createElement('tr');
    
    const pay_model = !row.Payment_Model ? '—' : 
      row.Payment_Model.toLowerCase() === 'per_game' ? 'Per Game' :
      row.Payment_Model.toLowerCase() === 'per_hour' ? 'Per Hour' :
      row.Payment_Model;
    tr.innerHTML = `
      <td>${row.Name}</td>
      <td>${row.Number_of_Tables ?? '?'}</td>
      <td>${pay_model}</td>
      <td>${cost}</td>`;
    tr.addEventListener('click', () => {
      const marker = poolMarkers.find((m) => m.rowIndex === i);
      if (marker) { poolMap.setView(marker.getLatLng(), 16); marker.openPopup(); }
    });
    tbody.appendChild(tr);
  });
}
// ── Pool bar search (prepopulate from bars collection) ────────────────────
const poolSearchInput = document.getElementById('pool-search-input');
const poolSearchResultsList = document.getElementById('pool-search-results-list');

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
                document.getElementById('pool-neighborhood-input').value = bar.Neighborhood || bar.Neighborhoods || '';
                document.getElementById('pool-lat').value = bar.Latitude || '';
                document.getElementById('pool-lng').value = bar.Longitude || '';
                document.getElementById("pool-Yelp Alias").value = bar["Yelp Alias"] || "";
                if (bar["Yelp Rating"]) document.getElementById("pool-Yelp Rating").value = bar["Yelp Rating"];

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
  if (poolSearchInput && poolSearchResults &&
      !poolSearchInput.contains(e.target) && !poolSearchResults.contains(e.target)) {
    poolSearchResultsList.innerHTML = '';
  }
});

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
  poolActiveFilters.paymentModel = null;
  poolActiveFilters.minTables    = null;
  poolActiveFilters.hasHappyHour = false;
  poolActiveFilters.hasLeague    = false;
  setPoolFilterLabel('pool-payment-button', 'Payment');
  setPoolFilterActive('pool-payment-button', false);
  setPoolFilterLabel('pool-tables-button', 'Tables');
  setPoolFilterActive('pool-tables-button', false);
  setPoolFilterActive('pool-hh-button', false);
  setPoolFilterActive('pool-league-button', false);
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
    document.getElementById('pool-neighborhood-field').style.display   = isPhilly ? 'block' : 'none';
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
  const isPhilly     = document.getElementById('pool-philly-yes').checked;
  const streetAddress = document.getElementById('pool-street-address').value;
  const city          = isPhilly ? 'Philadelphia' : document.getElementById('pool-address-city').value;
  const state         = isPhilly ? 'PA' : document.getElementById('pool-address-state').value;
  const zip           = isPhilly ? '' : document.getElementById('pool-address-zip').value;
  const fullAddress   = `${streetAddress}, ${city}, ${state}${zip ? ' ' + zip : ''}`;

  let lat = null, lng = null;
  try {
    const geo = await fetch(`${POOL_API_BASE}/api/geocode?address=${encodeURIComponent(fullAddress)}`);
    const gd  = await geo.json();
    lat = gd.lat; lng = gd.lng;
  } catch (_) {}

  const payModel = document.getElementById('pool-payment-model-select').value;
  const submission = {
    name:          document.getElementById('pool-business-name').value,
    streetAddress, city, state, zip, Latitude: lat, Longitude: lng,
    neighborhood:  isPhilly ? document.getElementById('pool-neighborhood-input').value : '',
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
      alert('Your pool bar has been submitted for review — thanks!');
      document.getElementById('pool-bar-submission-form').reset();
      document.getElementById('pool-cost-game-field').style.display = 'none';
      document.getElementById('pool-cost-hour-field').style.display = 'none';
      bootstrap.Modal.getInstance(document.getElementById('addPoolBarModal')).hide();
    })
    .catch(() => alert('Error submitting. Please try again.'));
});

// Edit pool bar — search
const poolSearchBar     = document.getElementById('pool-search-bar');
const poolSearchResults = document.getElementById('pool-search-results');
const poolEditFields    = document.getElementById('pool-edit-fields');

poolSearchBar.addEventListener('input', () => {
  const q = poolSearchBar.value.toLowerCase();
  poolSearchResults.innerHTML = '';
  if (q.length < 1) return;
  poolAllData
    .filter((d) => d.Name && d.Name.toLowerCase().includes(q))
    .forEach((bar) => {
      const li = document.createElement('li');
      li.textContent  = bar.Name;
      li.style.cursor = 'pointer';
      li.addEventListener('click', () => {
        document.getElementById('pool-edit-name').value          = bar.Name;
        document.getElementById('pool-edit-address').value       = bar.Address || '';
        document.getElementById('pool-edit-num-tables').value    = bar.Number_of_Tables || '';
        document.getElementById('pool-edit-payment-model').value = bar.Payment_Model || '';
        document.getElementById('pool-edit-original-id').value   = bar._id || '';
        poolEditFields.style.display = 'block';
        poolSearchResults.innerHTML  = '';
      });
      poolSearchResults.appendChild(li);
    });
});

// Submit pool bar edit
document.getElementById('pool-edit-form').addEventListener('submit', async function (e) {
  e.preventDefault();
  const originalId   = document.getElementById('pool-edit-original-id').value;
  const originalName = document.getElementById('pool-edit-name').value;
  const changes = {
    Name:            document.getElementById('pool-edit-name').value,
    Address:         document.getElementById('pool-edit-address').value,
    Number_of_Tables: document.getElementById('pool-edit-num-tables').value || undefined,
    Payment_Model:   document.getElementById('pool-edit-payment-model').value || undefined,
  };
  const notes = document.getElementById('pool-edit-notes').value;

  fetch(`${POOL_API_BASE}/submit-pool-bar-edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ originalId, originalName, changes, notes }),
  })
    .then((r) => r.json())
    .then(() => {
      alert('Edit submitted for review — thanks!');
      document.getElementById('pool-edit-form').reset();
      poolEditFields.style.display = 'none';
      bootstrap.Modal.getInstance(document.getElementById('editPoolBarModal')).hide();
    })
    .catch(() => alert('Error submitting edit.'));
});