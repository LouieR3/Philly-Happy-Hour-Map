const API_BASE = window.location.hostname === 'localhost' 
  ? 'http://localhost:3000'
  : 'https://philly-happy-hour-map-production.up.railway.app';

var leafletmap = L.map("leaflet-map").setView([39.951, -75.163], 12);

leafletmap.zoomControl.setPosition("bottomright");

// Add OpenStreetMap tile layer
// L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
//     attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
// }).addTo(leafletmap);

L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  attribution: "&copy; OpenStreetMap & CartoDB",
  subdomains: "abcd",
}).addTo(leafletmap);

function createMartiniIcon(color = "green") {
  return L.divIcon({
    html: `
    <div class="custom-pin">
        <div class="pin-circle" style="background-color: ${color};">
        <i class="fa-solid fa-martini-glass"></i>
        </div>
        <div class="pin-tail" style="background-color: ${color};"></div>
    </div>
    `,
    className: "custom-fa-icon", // avoids default icon styling
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });
}

// ─── Active filter state ────────────────────────────────────────────────────
var markers = [];
var quizzoGeoJson = null;

function getQuizzoNhFromLatLng(lat, lng) {
  if (!quizzoGeoJson || !window.turf) return null;
  const pt = turf.point([lng, lat]);
  for (const feature of quizzoGeoJson.features) {
    try {
      if (turf.booleanPointInPolygon(pt, feature)) return feature.properties.LISTNAME || null;
    } catch(e) {}
  }
  return null;
}
const activeFilters = {
  weekday: null,
  time: null,
  firstPrize: null,
  prizeAmount: null,
  neighborhoods: new Set(),
};

function applyFilters() {
  markers.forEach((marker) => {
    if (!(marker instanceof L.Marker)) return;
    const passes =
      (!activeFilters.weekday || marker.weekday === activeFilters.weekday) &&
      (!activeFilters.time || marker.time === activeFilters.time) &&
      (!activeFilters.firstPrize || marker.firstPrize === activeFilters.firstPrize) &&
      (!activeFilters.prizeAmount || marker.prizeAmount === activeFilters.prizeAmount) &&
      (activeFilters.neighborhoods.size === 0 || activeFilters.neighborhoods.has(marker.neighborhood));
    if (passes) {
      if (!leafletmap.hasLayer(marker)) marker.addTo(leafletmap);
    } else {
      if (leafletmap.hasLayer(marker)) leafletmap.removeLayer(marker);
    }
  });
}

function setFilterLabel(buttonId, text) {
  document.querySelector(`#${buttonId} .filter-label`).textContent = text;
}

function setFilterActive(buttonId, isActive) {
  document.getElementById(buttonId).classList.toggle("filter-active", isActive);
}

// 2. Load CSV and add markers

fetch(`${API_BASE}/api/quizzo`)
  .then((response) => response.json())
  .then(function (data) {
    const times = [
      ...new Set(data.map((row) => row.TIME).filter((eventType) => eventType)),
    ].sort((a, b) => {
      return new Date(`1970/01/01 ${a}`) - new Date(`1970/01/01 ${b}`);
    });
    const eventTypes = [
      ...new Set(
        data
          .map((row) => row.EVENT_TYPE)
          .filter((eventType) => eventType) // Remove null or undefined values
          .map((eventType) => eventType.replace(/_/g, " ")), // Replace underscores with spaces
      ),
    ].sort();
    const firstPrizes = [
      ...new Set(
        data
          .map((row) => row.PRIZE_1_TYPE)
          .filter((firstPrize) => firstPrize) // Remove null or undefined values
          .map((firstPrize) => firstPrize.replace(/_/g, " ")), // Replace underscores with spaces
      ),
    ].sort();
    const neighborhoods = [
      ...new Set(
        data
          .map((row) => row.NEIGHBORHOOD)
          .filter((neighborhood) => neighborhood) // Remove null or undefined values
          .map((neighborhood) => neighborhood.replace(/_/g, " ")), // Replace underscores with spaces
      ),
    ].sort();

    // Populate the Start Time dropdown
    const timeOptions = document.getElementById("time-options");
    times.forEach((time) => {
      const li = document.createElement("li");
      li.className = "time-option";
      li.setAttribute("data-value", time);
      li.textContent = time;
      li.addEventListener("click", () => {
        activeFilters.time = time;
        setFilterLabel("time-button", time);
        setFilterActive("time-button", true);
        document.getElementById("time-dropdown").style.display = "none";
        applyFilters();
      });
      timeOptions.appendChild(li);
    });
    const allTimeOption = document.createElement("li");
    allTimeOption.className = "time-option";
    allTimeOption.setAttribute("data-value", "All");
    allTimeOption.textContent = "All";
    allTimeOption.addEventListener("click", () => {
      activeFilters.time = null;
      setFilterLabel("time-button", "Start Time");
      setFilterActive("time-button", false);
      document.getElementById("time-dropdown").style.display = "none";
      applyFilters();
    });
    timeOptions.prepend(allTimeOption);

    // // Populate the Event Type dropdown
    // const eventTypeOptions = document.getElementById("event-type-options");
    // eventTypes.forEach(eventType => {
    //   const li = document.createElement("li");
    //   li.className = "event-type-option";
    //   li.setAttribute("data-value", eventType);
    //   li.textContent = eventType;

    //   li.addEventListener("click", event => {
    //     const selectedEventType = event.target.getAttribute("data-value");
    //     console.log("Selected eventType:", selectedEventType);

    //     markers.forEach(function (marker) {
    //       if (!(marker instanceof L.Marker)) return;

    //       // If "All" is selected, add all markers back to the map
    //       if (selectedEventType === "All" || marker.eventType === selectedEventType) {
    //         if (!leafletmap.hasLayer(marker)) {
    //           marker.addTo(leafletmap);
    //         }
    //       } else {
    //         if (leafletmap.hasLayer(marker)) {
    //           leafletmap.removeLayer(marker);
    //         }
    //       }
    //     });

    //   });
    //   eventTypeOptions.appendChild(li);
    // });
    // // Add the "All" option to the Event Type dropdown
    // const allEventTypeOption = document.createElement("li");
    // allEventTypeOption.className = "event-type-option";
    // allEventTypeOption.setAttribute("data-value", "All");
    // allEventTypeOption.textContent = "All";
    // allEventTypeOption.addEventListener("click", event => {
    //   const selectedEventType = event.target.getAttribute("data-value");
    //   console.log("Selected eventType:", selectedEventType);

    //   markers.forEach(function (marker) {
    //     if (!(marker instanceof L.Marker)) return;

    //     // Add all markers back to the map when "All" is selected
    //     if (!leafletmap.hasLayer(marker)) {
    //       marker.addTo(leafletmap);
    //     }
    //   });

    //   // Close the dropdown after selection
    //   const eventTypeDropdown = document.getElementById("event-type-dropdown");
    //   eventTypeDropdown.style.display = "none";
    // });
    // eventTypeOptions.prepend(allEventTypeOption);

    // Populate the First Prize dropdown
    const firstPrizeOptions = document.getElementById("first-prize-options");
    firstPrizes.forEach((firstPrize) => {
      const li = document.createElement("li");
      li.className = "first-prize-option";
      li.setAttribute("data-value", firstPrize);
      li.textContent = firstPrize;
      li.addEventListener("click", () => {
        activeFilters.firstPrize = firstPrize;
        setFilterLabel("first-prize-button", firstPrize);
        setFilterActive("first-prize-button", true);
        document.getElementById("first-prize-dropdown").style.display = "none";
        applyFilters();
      });
      firstPrizeOptions.appendChild(li);
    });
    const allFirstPrizeOption = document.createElement("li");
    allFirstPrizeOption.className = "first-prize-option";
    allFirstPrizeOption.setAttribute("data-value", "All");
    allFirstPrizeOption.textContent = "All";
    allFirstPrizeOption.addEventListener("click", () => {
      activeFilters.firstPrize = null;
      setFilterLabel("first-prize-button", "First Prize");
      setFilterActive("first-prize-button", false);
      document.getElementById("first-prize-dropdown").style.display = "none";
      applyFilters();
    });
    firstPrizeOptions.prepend(allFirstPrizeOption);

    // Populate the Prize Amount dropdown
    const prizeAmounts = [
      ...new Set(
        data
          .flatMap((row) => [row.PRIZE_1_AMOUNT, row.PRIZE_2_AMOUNT, row.PRIZE_3_AMOUNT])
          .filter((a) => a != null && a !== "" && !isNaN(a))
          .map((a) => Number(a))
      ),
    ].sort((a, b) => a - b);

    const prizeAmountOptions = document.getElementById("prize-amount-options");
    prizeAmounts.forEach((amount) => {
      const li = document.createElement("li");
      li.className = "prize-amount-option";
      li.setAttribute("data-value", amount);
      li.textContent = `$${amount}`;
      li.addEventListener("click", () => {
        activeFilters.prizeAmount = amount;
        setFilterLabel("prize-amount-button", `$${amount}`);
        setFilterActive("prize-amount-button", true);
        document.getElementById("prize-amount-dropdown").style.display = "none";
        applyFilters();
      });
      prizeAmountOptions.appendChild(li);
    });
    const allPrizeAmountOption = document.createElement("li");
    allPrizeAmountOption.className = "prize-amount-option";
    allPrizeAmountOption.setAttribute("data-value", "All");
    allPrizeAmountOption.textContent = "All";
    allPrizeAmountOption.addEventListener("click", () => {
      activeFilters.prizeAmount = null;
      setFilterLabel("prize-amount-button", "Prize Amount");
      setFilterActive("prize-amount-button", false);
      document.getElementById("prize-amount-dropdown").style.display = "none";
      applyFilters();
    });
    prizeAmountOptions.prepend(allPrizeAmountOption);

    // ── GeoJSON-based Region + Neighborhood filters ──────────────────────
    fetch('assets/philadelphia-neighborhoods.geojson')
      .then(r => r.json())
      .then(function(geoJson) {
        quizzoGeoJson = geoJson;
        const nhHasMarker     = {};  // LISTNAME → feature
        const regionHasMarker = {};  // GENERAL_AREA → [features]

        markers.forEach(function(marker) {
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

        function zoomToFeatures(features) {
          const bbox = turf.bbox(turf.featureCollection(features));
          leafletmap.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], { padding: [30, 30] });
        }

        const DD_STYLE = 'padding:7px 12px;cursor:pointer;color:#e2e8f0;';
        const DD_HOVER_IN  = function() { this.style.background = 'rgba(255,255,255,0.08)'; };
        const DD_HOVER_OUT = function() { this.style.background = ''; };

        function makeLi(text, onClick) {
          const li = document.createElement('li');
          li.style.cssText = DD_STYLE;
          li.textContent   = text;
          li.addEventListener('mouseover', DD_HOVER_IN);
          li.addEventListener('mouseout',  DD_HOVER_OUT);
          li.addEventListener('click', onClick);
          return li;
        }

        // ── Region dropdown ───────────────────────────────────────────────
        const regionOpts    = document.getElementById('region-options');
        const sortedRegions = Object.keys(regionHasMarker).sort();

        regionOpts.appendChild(makeLi('All', () => {
          activeFilters.region      = null;
          activeFilters.neighborhoods.clear();
          setFilterLabel('region-button', 'Region');
          setFilterActive('region-button', false);
          document.getElementById('region-dropdown').style.display = 'none';
          buildQuizzoNeighborhoodList(nhHasMarker, null);
          applyFilters();
          leafletmap.setView([39.951, -75.163], 12);
        }));

        sortedRegions.forEach(region => {
          regionOpts.appendChild(makeLi(region, () => {
            activeFilters.region      = region;
            activeFilters.neighborhoods.clear();
            setFilterLabel('region-button', region);
            setFilterActive('region-button', true);
            document.getElementById('region-dropdown').style.display = 'none';
            buildQuizzoNeighborhoodList(nhHasMarker, region);
            applyFilters();
            zoomToFeatures(regionHasMarker[region]);
          }));
        });

        setupDropdownToggle('region-button', 'region-dropdown');

        // ── Neighborhood dropdown ─────────────────────────────────────────
        function buildQuizzoNeighborhoodList(nhMap, filterRegion) {
          const opts  = document.getElementById('neighborhood-options');
          opts.innerHTML = '';

          opts.appendChild(makeLi('All', () => {
            activeFilters.neighborhoods.clear();
            setFilterLabel('neighborhood-button', 'Neighborhood');
            setFilterActive('neighborhood-button', false);
            document.getElementById('neighborhood-dropdown').style.display = 'none';
            applyFilters();
          }));

          let names = Object.keys(nhMap).sort();
          if (filterRegion) {
            names = names.filter(n => (nhMap[n].properties.GENERAL_AREA || '').trim() === filterRegion);
          }

          names.forEach(name => {
            const feature = nhMap[name];
            opts.appendChild(makeLi(name, () => {
              activeFilters.neighborhoods.clear();
              activeFilters.neighborhoods.add(name);
              setFilterLabel('neighborhood-button', name);
              setFilterActive('neighborhood-button', true);
              document.getElementById('neighborhood-dropdown').style.display = 'none';
              applyFilters();
              zoomToFeatures([feature]);
            }));
          });
        }

        buildQuizzoNeighborhoodList(nhHasMarker, null);
        setupDropdownToggle('neighborhood-button', 'neighborhood-dropdown');

        // Mobile filter options
        if (typeof populateQuizzoMobileFilterOptions === 'function') {
          populateQuizzoMobileFilterOptions({
            times: times,
            firstPrizes: firstPrizes,
            prizeAmounts: prizeAmounts,
            neighborhoods: Object.keys(nhHasMarker).sort()
          });
        }
      });


    // Create a layer group for markers
    const markerLayerGroup = L.layerGroup().addTo(leafletmap);

    data.forEach(function (row) {
      var lat = parseFloat(row.Latitude);
      var lng = parseFloat(row.Longitude);
      var weekday = row.WEEKDAY;
      var neighborhood = row.NEIGHBORHOOD;
      var time = row.TIME;
      var businessName = row.BUSINESS;
      // var eventType = row.EVENT_TYPE.replace(/_/g, ' ');
      var firstPrize = row.PRIZE_1_TYPE
        ? row.PRIZE_1_TYPE.replace(/_/g, " ")
        : "";
      var secondPrize = row.PRIZE_2_TYPE
        ? row.PRIZE_2_TYPE.replace(/_/g, " ")
        : "";
      var address =
        row.ADDRESS_STREET +
        ", " +
        row.ADDRESS_CITY +
        ", " +
        row.ADDRESS_STATE +
        " " +
        row.ADDRESS_ZIP;

      if (!isNaN(lat) && !isNaN(lng)) {
        
        var address = [row.ADDRESS_STREET, row.ADDRESS_CITY, row.ADDRESS_STATE]
          .filter(Boolean).join(', ');
        var locationLine = row.ADDRESS_STREET 
          ? address 
          : `${row.NEIGHBORHOOD ? row.NEIGHBORHOOD + ' · ' : ''}${row.ADDRESS_CITY || 'Philadelphia'}, PA`;

        var popupContent = `
          <div style="font-family: 'Red Hat Text', sans-serif; width: 240px; overflow: hidden; border-radius: 8px;">
            <div style="background: #1a6b4a; padding: 14px 16px 12px;">
              <p style="margin: 0; font-size: 15px; font-weight: 600; color: #fff;">${row.BUSINESS}</p>
              <p style="margin: 4px 0 0; font-size: 12px; color: rgba(255,255,255,0.75);">${locationLine}</p>
              <p style="margin: 4px 0 0; font-size: 12px; color: rgba(255, 255, 255);">${row.NEIGHBORHOOD}</p>
            </div>
            <div style="padding: 12px 16px; display: flex; flex-direction: column; gap: 10px; background: #fff;">
              <div style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: #555;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                <span style="color: #111; font-weight: 600;">${row.WEEKDAY}</span>
                <span style="color: #ccc;">·</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-left:4px"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                <span style="color: #111; font-weight: 600;">${row.TIME}</span>
              </div>
              ${row.HOST ? `
              <div style="font-size: 12px; color: #555;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                Host: <span style="color: #111; font-weight: 600;">${row.HOST}</span>
              </div>` : ''}
              ${firstPrize || secondPrize ? `
              <div style="border-top: 1px solid #eee; padding-top: 10px; display: flex; gap: 6px; flex-wrap: wrap;">
                ${firstPrize ? `<span style="background: #e8f5ee; color: #0f6e56; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 20px;">🥇 ${firstPrize}${row.PRIZE_1_AMOUNT ? ' · $' + row.PRIZE_1_AMOUNT : ''}</span>` : ''}
                ${secondPrize ? `<span style="background: #f1f5e8; color: #3b6d11; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 20px;">🥈 ${secondPrize}${row.PRIZE_2_AMOUNT ? ' · $' + row.PRIZE_2_AMOUNT : ''}</span>` : ''}
              </div>` : ''}
            </div>
          </div>
        `;
        var marker = L.marker([lat, lng], {
          icon: createMartiniIcon("darkgreen"),
        }).bindPopup(popupContent);
        marker.weekday = weekday;
        marker.time = time;
        marker.firstPrize = firstPrize;
        marker.prizeAmount = row.PRIZE_1_AMOUNT != null ? Number(row.PRIZE_1_AMOUNT) : null;
        marker.businessName = businessName;
        marker.neighborhood = neighborhood;
        marker.address = address;
        marker.mongoId = row._id || null;
        marker.secondPrize = row.PRIZE_2_TYPE ? row.PRIZE_2_TYPE.replace(/_/g, ' ') : '';
        marker.host = row.HOST || '';
        markers.push(marker);
        marker.addTo(leafletmap);
        markerLayerGroup.addLayer(marker); // Add marker to the layer group
      }
    });

    // ── Custom map search overlay ─────────────────────────────────────────
    const QuizzoSearchControl = L.Control.extend({
      options: { position: 'topleft' },
      onAdd: function() {
        const c = L.DomUtil.create('div', 'map-search-control');
        c.innerHTML = '<input type="text" id="map-search-field" placeholder="Search bars\u2026" autocomplete="off" /><ul id="map-search-list"></ul>';
        L.DomEvent.disableClickPropagation(c);
        L.DomEvent.disableScrollPropagation(c);
        return c;
      }
    });
    leafletmap.addControl(new QuizzoSearchControl());

    document.getElementById('map-search-field').addEventListener('input', function() {
      const q = this.value.trim().toLowerCase();
      const list = document.getElementById('map-search-list');
      list.innerHTML = '';
      if (q.length < 2) return;
      markers
        .filter(m => m.businessName && m.businessName.toLowerCase().includes(q))
        .slice(0, 8)
        .forEach(m => {
          const li = document.createElement('li');
          li.textContent = m.businessName;
          li.addEventListener('click', () => {
            leafletmap.setView(m.getLatLng(), 16);
            m.openPopup();
            document.getElementById('map-search-field').value = m.businessName;
            list.innerHTML = '';
          });
          list.appendChild(li);
        });
    });

    document.addEventListener('click', function(e) {
      const field = document.getElementById('map-search-field');
      const list  = document.getElementById('map-search-list');
      if (field && list && !field.contains(e.target) && !list.contains(e.target)) {
        list.innerHTML = '';
      }
    });

    // Populate the table here — markers are fully built so the name lookup works
    populateTable(data);
    if (window._quizzoDrawerSetData) window._quizzoDrawerSetData(data);

    // Populate mobile filter options
    if (window.populateQuizzoMobileFilterOptions) {
      window.populateQuizzoMobileFilterOptions({
        times: times,
        firstPrizes: firstPrizes,
        prizeAmounts: prizeAmounts,
        neighborhoods: neighborhoods
      });
    }
  })
  .catch(function (err) {
    console.error("Failed to load quizzo data:", err);
  });

// Default map center and zoom level
const defaultCenter = [39.951, -75.163]; // Philadelphia center
const defaultZoom = 12;

// Reset Filters Button Functionality
document
  .getElementById("reset-filters-button")
  .addEventListener("click", () => {
    // Clear all active filters
    activeFilters.weekday = null;
    activeFilters.time = null;
    activeFilters.firstPrize = null;
    activeFilters.prizeAmount = null;
    activeFilters.neighborhoods.clear();

    // Reset button labels and active state
    setFilterLabel("weekday-button", "Weekday");
    setFilterActive("weekday-button", false);
    setFilterLabel("time-button", "Start Time");
    setFilterActive("time-button", false);
    setFilterLabel("first-prize-button", "First Prize");
    setFilterActive("first-prize-button", false);
    setFilterLabel("prize-amount-button", "Prize Amount");
    setFilterActive("prize-amount-button", false);
    setFilterLabel("neighborhood-button", "Neighborhood");
    setFilterActive("neighborhood-button", false);

    // Clear neighborhood selection highlights
    document.querySelectorAll(".filter-option-selected").forEach((el) => el.classList.remove("filter-option-selected"));

    // Show all markers and reset map view
    applyFilters();
    leafletmap.setView(defaultCenter, defaultZoom);

    // Reset search inputs
    document.getElementById("neighborhood-search").value = "";
    document.getElementById("bar-search").value = "";
    filterTable("");
  });

// // Toggle Event Type dropdown visibility
// const eventTypeButton = document.getElementById("event-type-button");
// const eventTypeDropdown = document.getElementById("event-type-dropdown");
// eventTypeButton.addEventListener("click", () => {
//   const isVisible = eventTypeDropdown.style.display === "block";
//   eventTypeDropdown.style.display = isVisible ? "none" : "block";
// });
// // Close dropdown if clicked outside
// document.addEventListener("click", event => {
//   if (!eventTypeButton.contains(event.target) && !eventTypeDropdown.contains(event.target)) {
//     eventTypeDropdown.style.display = "none";
//   }
// });

// ─── Dropdown toggles ────────────────────────────────────────────────────────
function setupDropdownToggle(buttonId, dropdownId) {
  const btn = document.getElementById(buttonId);
  const dd = document.getElementById(dropdownId);
  btn.addEventListener("click", () => {
    const isVisible = dd.style.display === "block";
    // Close all other dropdowns first
    document.querySelectorAll(".filter-dropdown-panel").forEach((el) => (el.style.display = "none"));
    dd.style.display = isVisible ? "none" : "block";
  });
  document.addEventListener("click", (event) => {
    if (!btn.contains(event.target) && !dd.contains(event.target)) {
      dd.style.display = "none";
    }
  });
}

setupDropdownToggle("weekday-button", "weekday-dropdown");
setupDropdownToggle("time-button", "time-dropdown");
setupDropdownToggle("first-prize-button", "first-prize-dropdown");
setupDropdownToggle("prize-amount-button", "prize-amount-dropdown");
// setupDropdownToggle for region and neighborhood are now initialized inside the GeoJSON fetch

// Handle weekday selection
document.querySelectorAll(".weekday-option").forEach((option) => {
  option.addEventListener("click", (event) => {
    const selectedWeekday = event.target.getAttribute("data-value");
    if (selectedWeekday === "All") {
      activeFilters.weekday = null;
      setFilterLabel("weekday-button", "Weekday");
      setFilterActive("weekday-button", false);
    } else {
      activeFilters.weekday = selectedWeekday;
      // Title-case the day for the label
      const label = selectedWeekday.charAt(0) + selectedWeekday.slice(1).toLowerCase();
      setFilterLabel("weekday-button", label);
      setFilterActive("weekday-button", true);
    }
    document.getElementById("weekday-dropdown").style.display = "none";
    applyFilters();
  });
});

// Open Add New Bar modal
const addBarButton = document.getElementById("add-bar-button");
addBarButton.addEventListener("click", () => {
  new bootstrap.Modal(document.getElementById("addBarModal")).show();
});

// Open Edit Bar modal
const editBarButton = document.getElementById("edit-bar-button");
editBarButton.addEventListener("click", () => {
  new bootstrap.Modal(document.getElementById("editBarModal")).show();
});

// Mobile buttons for Add/Edit (visible only on mobile)
const mobileAddBtn = document.getElementById("quizzo-mobile-add-btn");
const mobileEditBtn = document.getElementById("quizzo-mobile-edit-btn");
if (mobileAddBtn) {
  mobileAddBtn.addEventListener("click", () => {
    new bootstrap.Modal(document.getElementById("addBarModal")).show();
  });
}
if (mobileEditBtn) {
  mobileEditBtn.addEventListener("click", () => {
    new bootstrap.Modal(document.getElementById("editBarModal")).show();
  });
}

// ── Search-from-bars for Add Bar modal ────────────────────────────────────────
const quizzoSearchInput       = document.getElementById('quizzo-search-input');
const quizzoSearchResultsList = document.getElementById('quizzo-search-results-list');

if (quizzoSearchInput && quizzoSearchResultsList) {
  quizzoSearchInput.addEventListener('input', async (e) => {
    const q = e.target.value.trim();
    if (q.length < 2) { quizzoSearchResultsList.innerHTML = ''; return; }
    try {
      const res  = await fetch(`${API_BASE}/api/search-bars?q=${encodeURIComponent(q)}`);
      const bars = await res.json();
      quizzoSearchResultsList.innerHTML = '';
      bars.forEach(bar => {
        const li = document.createElement('li');
        li.style.cssText = 'padding:10px;cursor:pointer;border-bottom:1px solid #334155;';
        li.innerHTML = `<strong>${bar.Name}</strong><br><small style="color:#94a3b8">${bar.Address || ''}</small>`;
        li.onclick = () => {
          document.getElementById('business-name').value  = bar.Name    || '';
          document.getElementById('street-address').value = bar.Address || '';
          document.getElementById('quizzo-lat').value     = bar.Latitude  || '';
          document.getElementById('quizzo-lng').value     = bar.Longitude || '';
          const nh = getQuizzoNhFromLatLng(bar.Latitude, bar.Longitude);
          document.getElementById('neighborhood').value = nh || '';
          quizzoSearchInput.value = bar.Name;
          quizzoSearchResultsList.innerHTML = '';
        };
        quizzoSearchResultsList.appendChild(li);
      });
    } catch(err) { console.error('Quizzo search error:', err); }
  });

  document.addEventListener('click', (e) => {
    const container = document.getElementById('quizzo-search-results');
    if (container && !quizzoSearchInput.contains(e.target) && !container.contains(e.target)) {
      quizzoSearchResultsList.innerHTML = '';
    }
  });
}

// Philly Yes/No toggle in Add Bar modal
document.querySelectorAll('input[name="isPhiladelphia"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    const isPhilly = document.getElementById("is-philly-yes").checked;
    document.getElementById("city-state-zip-fields").style.display = isPhilly ? "none" : "block";
  });
});

// Handle Search for Editing
const searchBar = document.getElementById("search-bar");
const searchResults = document.getElementById("search-results");
const editFields = document.getElementById("edit-fields");

searchBar.addEventListener("input", () => {
  const query = searchBar.value.toLowerCase();
  searchResults.innerHTML = ""; // Clear previous results

  if (query.length > 0) {
    const matchingBars = markers.filter((marker) =>
      marker.businessName.toLowerCase().includes(query),
    );
    matchingBars.forEach((marker) => {
      const li = document.createElement("li");
      li.className = "search-option";
      li.textContent = marker.businessName;
      li.style.cursor = "pointer";
      li.addEventListener("click", () => {
        document.getElementById("edit-business-name").value = marker.businessName;
        document.getElementById("edit-address").value = marker.address;
        document.getElementById("edit-original-id").value = marker.mongoId || '';

        // Populate Weekday dropdown
        const weekdayDropdown = document.getElementById("edit-weekday");
        weekdayDropdown.innerHTML = ""; // Clear existing options
        const weekdays = [
          "MONDAY",
          "TUESDAY",
          "WEDNESDAY",
          "THURSDAY",
          "FRIDAY",
          "SATURDAY",
          "SUNDAY",
        ];
        weekdays.forEach((day) => {
          const option = document.createElement("option");
          option.value = day;
          option.textContent = day;
          if (day === marker.weekday) {
            option.selected = true; // Set the selected option
          }
          weekdayDropdown.appendChild(option);
        });

        // // Populate Event Type dropdown
        // const eventTypeDropdown = document.getElementById("edit-event-type");
        // eventTypeDropdown.innerHTML = ""; // Clear existing options
        // const eventTypes = [...new Set(results.data.map(row => row.EVENT_TYPE).filter(eventType => eventType))];
        // eventTypes.forEach(eventType => {
        //   const option = document.createElement("option");
        //   option.value = eventType;
        //   option.textContent = eventType.replace(/_/g, " "); // Replace underscores with spaces
        //   if (eventType === marker.eventType) {
        //     option.selected = true; // Set the selected option
        //   }
        //   eventTypeDropdown.appendChild(option);
        // });

        // Handle empty fields for Second Prize and Host
        document.getElementById("edit-first-prize").value =
          marker.firstPrize || "";
        document.getElementById("edit-second-prize").value =
          marker.secondPrize || "";
        document.getElementById("edit-host").value = marker.host || "";

        document.getElementById("edit-time").value = marker.time;

        editFields.style.display = "block"; // Show the edit fields
        searchResults.innerHTML = ""; // Clear search results
      });
      searchResults.appendChild(li);
    });
  }
});

// ─── Form submission throttling ─────────────────────────────────────────────────
// Helper to prevent duplicate/rapid form submissions
function createThrottledSubmitter(cooldownMs = 1000) {
  let isSubmitting = false;
  let lastSubmitTime = 0;
  
  return function(formElement, submitFn) {
    return async function(event) {
      event.preventDefault();
      
      const now = Date.now();
      if (isSubmitting || (now - lastSubmitTime) < cooldownMs) {
        console.warn('Form submission throttled — please wait before submitting again');
        return;
      }
      
      isSubmitting = true;
      const submitBtn = formElement.querySelector('button[type="submit"]');
      const originalText = submitBtn ? submitBtn.textContent : '';
      
      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Submitting...';
        }
        
        await submitFn(event);
        lastSubmitTime = Date.now();
      } catch (error) {
        console.error('Submission error:', error);
      } finally {
        isSubmitting = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    };
  };
}

const throttleSubmit = createThrottledSubmitter(1500); // 1.5 second cooldown

// ─── Bar submission form ────────────────────────────────────────────────────────
const barSubmissionForm = document.getElementById("bar-submission-form");
barSubmissionForm.addEventListener("submit", throttleSubmit(barSubmissionForm, async function (event) {

    const businessName = document.getElementById("business-name").value;
    const streetAddress = document.getElementById("street-address").value;
    const isPhilly = document.getElementById("is-philly-yes").checked;
    const city = isPhilly ? "Philadelphia" : document.getElementById("address-city").value;
    const state = isPhilly ? "PA" : document.getElementById("address-state").value;
    const zip = isPhilly ? "" : document.getElementById("address-zip").value;
    const weekday = document.getElementById("weekday").value;
    const time = document.getElementById("time").value;
    const firstPrize = document.getElementById("first-prize").value;
    const firstPrizeAmount = document.getElementById("first-prize-amount").value;
    const secondPrize = document.getElementById("second-prize").value;
    const secondPrizeAmount = document.getElementById("second-prize-amount").value;
    const host = document.getElementById("host").value;
    const notes = document.getElementById("notes").value;

    const fullAddress = `${streetAddress}, ${city}, ${state}${zip ? " " + zip : ""}`;

    // Use pre-filled lat/lng from bar search, or geocode the address
    let lat = parseFloat(document.getElementById("quizzo-lat").value) || null;
    let lng = parseFloat(document.getElementById("quizzo-lng").value) || null;
    if (!lat || !lng) {
      try {
        const geoRes  = await fetch(`${API_BASE}/api/geocode?address=${encodeURIComponent(fullAddress)}`);
        const geoData = await geoRes.json();
        lat = geoData.lat;
        lng = geoData.lng;
      } catch (e) {
        console.warn("Geocode failed:", e);
      }
    }

    const neighborhood = (isPhilly && lat && lng) ? (getQuizzoNhFromLatLng(lat, lng) || "") : "";

    const submission = {
      businessName, streetAddress, city, state, zip, neighborhood,
      fullAddress, lat, lng, weekday, time,
      firstPrize, firstPrizeAmount, secondPrize, secondPrizeAmount,
      host, notes,
    };

    fetch(`${API_BASE}/submit-bar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(submission),
    })
      .then((response) => response.json())
      .then(() => {
        siteToast("Your submission has been sent for review!");
        document.getElementById("bar-submission-form").reset();
        bootstrap.Modal.getInstance(document.getElementById("addBarModal")).hide();
      })
      .catch((error) => {
        console.error("Error:", error);
        siteToast("There was an error submitting your request. Please try again.", "error");
      });
}));
// Build a name → placeholder-el Map and kick off photo fetch
function populateTable(data) {
  const markerByName = {};
  markers.forEach((m) => { if (m.businessName) markerByName[m.businessName] = m; });

  const list = document.getElementById('bar-list');
  list.innerHTML = '';
  // name → { thumbEl, tagsEl } for post-fetch enrichment
  const barRefs = new Map();

  data.forEach((row) => {
    if (!row.BUSINESS || !row.NEIGHBORHOOD || !row.WEEKDAY || !row.TIME) return;

    const card = document.createElement('div');
    card.className = 'bar-card';

    const placeholder = document.createElement('div');
    placeholder.className = 'bar-card-thumb-placeholder';
    placeholder.innerHTML = '<i class="fa-solid fa-martini-glass-citrus"></i>';

    const tagsEl = document.createElement('div');
    tagsEl.className = 'bar-card-tags';
    tagsEl.innerHTML = `
      <span class="bar-card-tag">${row.WEEKDAY}</span>
      <span class="bar-card-tag">${row.TIME}</span>`;

    barRefs.set(row.BUSINESS, { thumbEl: placeholder, tagsEl });

    const nameEl = document.createElement('div');
    nameEl.className = 'bar-card-name';
    nameEl.textContent = row.BUSINESS;

    const addrEl = document.createElement('div');
    addrEl.className = 'bar-card-address';
    addrEl.textContent = row.NEIGHBORHOOD;

    const body = document.createElement('div');
    body.className = 'bar-card-body';
    body.appendChild(nameEl);
    body.appendChild(addrEl);
    body.appendChild(tagsEl);

    card.appendChild(placeholder);
    card.appendChild(body);
    card.addEventListener('click', () => {
      const marker = markerByName[row.BUSINESS];
      if (marker) {
        leafletmap.setView(marker.getLatLng(), 16);
        marker.openPopup();
        // Close mobile sheet after tap
        const sheet = document.getElementById('table-column');
        if (sheet) sheet.classList.remove('sheet-open');
      }
    });
    list.appendChild(card);
  });

  fetchAndApplyMeta(barRefs, API_BASE);
}

// Filter cards by search text
function filterTable(query) {
  const lower = query.toLowerCase();
  document.querySelectorAll('#bar-list .bar-card').forEach((card) => {
    card.style.display = card.textContent.toLowerCase().includes(lower) ? '' : 'none';
  });
}

// Batch-fetch photos + rating + price for drawer cards and inject into cards
async function fetchAndApplyMetaForDrawer(nameToRefs, base) {
  if (!nameToRefs.size) return;
  try {
    const names = [...nameToRefs.keys()];
    const res = await fetch(`${base}/api/bar-photos?names=${encodeURIComponent(names.join('|'))}`);
    const metaMap = await res.json();
    Object.entries(metaMap).forEach(([name, meta]) => {
      const refs = nameToRefs.get(name);
      if (!refs) return;
      const { thumbEl } = refs;
      if (meta.photos?.length) {
        const img = document.createElement('img');
        img.className = 'drawer-card-thumb';
        img.src = meta.photos[0];
        img.alt = name;
        thumbEl.replaceWith(img);
      }
    });
  } catch (e) {
    console.warn('[drawer-meta]', e.message);
  }
}

// Batch-fetch photos + rating + price and inject into cards
async function fetchAndApplyMeta(nameToRefs, base) {
  if (!nameToRefs.size) return;
  try {
    const names = [...nameToRefs.keys()];
    const res = await fetch(`${base}/api/bar-photos?names=${encodeURIComponent(names.join('|'))}`);
    const metaMap = await res.json();
    Object.entries(metaMap).forEach(([name, meta]) => {
      const refs = nameToRefs.get(name);
      if (!refs) return;
      const { thumbEl, tagsEl } = refs;
      if (meta.photos?.length) {
        const img = document.createElement('img');
        img.className = 'bar-card-thumb';
        img.src = meta.photos[0];
        img.alt = name;
        thumbEl.replaceWith(img);
      }
      if (meta.rating) {
        const t = document.createElement('span');
        t.className = 'bar-card-tag';
        t.textContent = `⭐ ${meta.rating}`;
        tagsEl.appendChild(t);
      }
      if (meta.price) {
        const t = document.createElement('span');
        t.className = 'bar-card-tag';
        t.textContent = meta.price;
        tagsEl.appendChild(t);
      }
    });
  } catch (e) {
    console.warn('[bar-meta]', e.message);
  }
}

// Add event listener for the search bar
document.getElementById("bar-search").addEventListener("input", (event) => {
  filterTable(event.target.value);
});

// Table is populated inside the main quizzo fetch above

// ── Quizzo edit form submission ────────────────────────────────────────────
const editBarForm = document.getElementById("edit-bar-form");
editBarForm.addEventListener("submit", throttleSubmit(editBarForm, async function (event) {
    const originalId   = document.getElementById("edit-original-id").value;
    const originalName = document.getElementById("edit-business-name").value;

    const changes = {};
    const newName    = document.getElementById("edit-business-name").value.trim();
    const newAddress = document.getElementById("edit-address").value.trim();
    const newWeekday = document.getElementById("edit-weekday").value;
    const newTime    = document.getElementById("edit-time").value;
    const newPrize1  = document.getElementById("edit-first-prize").value.trim();
    const newPrize2  = document.getElementById("edit-second-prize").value.trim();
    const newHost    = document.getElementById("edit-host").value.trim();
    const notes      = document.getElementById("edit-notes") ? document.getElementById("edit-notes").value.trim() : "";

    if (newName)    changes.BUSINESS        = newName.toUpperCase();
    if (newAddress) changes.Full_Address    = newAddress;
    if (newWeekday) changes.WEEKDAY         = newWeekday;
    if (newTime)    changes.TIME            = newTime;
    if (newPrize1)  changes.PRIZE_1_TYPE    = newPrize1.toUpperCase().replace(/ /g, '_');
    if (newPrize2)  changes.PRIZE_2_TYPE    = newPrize2.toUpperCase().replace(/ /g, '_');
    if (newHost)    changes.HOST            = newHost.toUpperCase();

    fetch(`${API_BASE}/submit-edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ originalBusiness: originalName, originalId, changes, notes }),
    })
      .then((r) => r.json())
      .then(() => {
        siteToast("Your edit has been submitted for review — thanks!");
        document.getElementById("edit-bar-form").reset();
        document.getElementById("edit-fields").style.display = "none";
        bootstrap.Modal.getInstance(document.getElementById("editBarModal")).hide();
      })
      .catch((err) => {
        console.error("Edit submission error:", err);
        siteToast("There was an error submitting your edit. Please try again.", "error");
      });
}));
// ── Quizzo mobile bottom drawer ────────────────────────────────────────────
(function() {
  var drawerData = [];   // all bars — set when data loads
  var drawerOpen = false;

  function openDrawer() {
    document.getElementById('quizzo-drawer').classList.add('open');
    document.getElementById('quizzo-drawer-backdrop').classList.add('open');
    drawerOpen = true;
    renderDrawerCards(drawerData);
  }

  function closeDrawer() {
    console.log('[Quizzo Drawer] closeDrawer() called');
    const drawerEl = document.getElementById('quizzo-drawer');
    const backdropEl = document.getElementById('quizzo-drawer-backdrop');
    console.log('[Quizzo Drawer] Found drawer:', !!drawerEl, 'backdrop:', !!backdropEl);
    if (drawerEl) {
      console.log('[Quizzo Drawer] Removing open class from drawer');
      drawerEl.classList.remove('open');
    }
    if (backdropEl) {
      console.log('[Quizzo Drawer] Removing open class from backdrop');
      backdropEl.classList.remove('open');
    }
    drawerOpen = false;
    console.log('[Quizzo Drawer] closeDrawer() complete');
  }

  function renderDrawerCards(data) {
    var row = document.getElementById('quizzo-drawer-cards');
    var q = (document.getElementById('quizzo-drawer-search').value || '').toLowerCase();
    row.innerHTML = '';

    var filtered = data.filter(function(bar) {
      if (!bar.BUSINESS || !bar.WEEKDAY) return false;
      if (!q) return true;
      return JSON.stringify(bar).toLowerCase().includes(q);
    });

    if (filtered.length === 0) {
      row.innerHTML = '<p style="color:#64748b;padding:20px;font-size:0.85rem;">No bars match your search.</p>';
      return;
    }

    var drawerBarRefs = new Map(); // Map of name -> { thumbEl }

    filtered.forEach(function(bar) {
      var card = document.createElement('div');
      card.className = 'drawer-card';

      var thumbEl = document.createElement('div');
      thumbEl.className = 'drawer-card-thumb-placeholder';
      thumbEl.innerHTML = '<i class="fa-solid fa-martini-glass"></i>';

      drawerBarRefs.set(bar.BUSINESS, { thumbEl: thumbEl });

      var addr = [bar.ADDRESS_STREET, bar.ADDRESS_CITY].filter(Boolean).join(', ') || bar.NEIGHBORHOOD || '';
      var prize = bar.PRIZE_1_TYPE ? bar.PRIZE_1_TYPE.replace(/_/g, ' ') : '';

      var body = document.createElement('div');
      body.className = 'drawer-card-body';
      body.innerHTML = '<div class="drawer-card-name">' + (bar.BUSINESS || '') + '</div>' +
        '<div class="drawer-card-meta">' + (bar.WEEKDAY || '') + ' · ' + (bar.TIME || '') + '</div>' +
        (addr ? '<div class="drawer-card-meta">' + addr + '</div>' : '') +
        (prize ? '<div class="drawer-card-tags"><span class="drawer-card-tag">🥇 ' + prize + '</span></div>' : '');

      card.appendChild(thumbEl);
      card.appendChild(body);

      card.addEventListener('click', function() {
        var markerByName = {};
        markers.forEach(function(m) { if (m.businessName) markerByName[m.businessName] = m; });
        var marker = markerByName[bar.BUSINESS];
        if (marker) {
          closeDrawer();
          leafletmap.setView(marker.getLatLng(), 16);
          marker.openPopup();
        }
      });

      row.appendChild(card);
    });

    // Batch-fetch photos for drawer cards
    if (drawerBarRefs.size) {
      fetchAndApplyMetaForDrawer(drawerBarRefs, API_BASE);
    }
  }

  // Expose so the main fetch can seed the data
  window._quizzoDrawerSetData = function(data) {
    drawerData = data;
    console.log('[Quizzo Drawer] Data set, count:', data.length);
  };

  // Defer initialization until drawer elements are in DOM
  // Use longer timeout to ensure all DOM is ready
  setTimeout(function() {
    console.log('[Quizzo Drawer] ===== INITIALIZATION START =====');
    var listBtn  = document.getElementById('quizzo-list-btn');
    var closeBtn = document.getElementById('quizzo-drawer-close');
    var backdrop = document.getElementById('quizzo-drawer-backdrop');
    var search   = document.getElementById('quizzo-drawer-search');
    var drawer   = document.getElementById('quizzo-drawer');

    console.log('[Quizzo Drawer] Elements found:');
    console.log('  - listBtn:', !!listBtn);
    console.log('  - closeBtn:', !!closeBtn, closeBtn ? 'ID=' + closeBtn.id : '');
    console.log('  - backdrop:', !!backdrop);
    console.log('  - search:', !!search);
    console.log('  - drawer:', !!drawer);

    if (listBtn) {
      listBtn.addEventListener('click', function() {
        console.log('[Quizzo Drawer] List button clicked');
        openDrawer();
      });
    }
    
    if (closeBtn) {
      console.log('[Quizzo Drawer] Attaching close button listener (by ID)');
      closeBtn.addEventListener('click', function(e) {
        console.log('[Quizzo Drawer] Close button clicked (direct)');
        e.preventDefault();
        e.stopPropagation();
        closeDrawer();
      });
    } else {
      console.warn('[Quizzo Drawer] Close button NOT found with ID quizzo-drawer-close');
      var allCloseButtons = document.querySelectorAll('#quizzo-drawer .drawer-close');
      console.log('[Quizzo Drawer] Found', allCloseButtons.length, 'close buttons via selector');
      allCloseButtons.forEach(function(btn, idx) {
        console.log('[Quizzo Drawer] Attaching listener to close button #' + idx);
        btn.addEventListener('click', function(e) {
          console.log('[Quizzo Drawer] Close button clicked (fallback #' + idx + ')');
          e.preventDefault();
          e.stopPropagation();
          closeDrawer();
        });
      });
    }
    
    if (backdrop) {
      backdrop.addEventListener('click', function(e) {
        console.log('[Quizzo Drawer] Backdrop clicked');
        e.stopPropagation();
        closeDrawer();
      });
    }
    
    if (search) {
      console.log('[Quizzo Drawer] Attaching search listener');
      search.addEventListener('input', function(e) {
        console.log('[Quizzo Drawer] Search input changed, drawerData length:', drawerData.length);
        renderDrawerCards(drawerData);
      });
    } else {
      console.warn('[Quizzo Drawer] Search input NOT found');
    }
    
    // Keyboard close on Escape
    if (drawer) {
      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          console.log('[Quizzo Drawer] Escape key pressed');
          closeDrawer();
        }
      });
    }
    console.log('[Quizzo Drawer] ===== INITIALIZATION COMPLETE =====');
  }, 500);
})();