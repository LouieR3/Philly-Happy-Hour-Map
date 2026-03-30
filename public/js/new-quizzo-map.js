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

    // Populate the Neighborhood dropdown (multi-select)
    const neighborhoodOptions = document.getElementById("neighborhood-options");

    function updateNeighborhoodLabel() {
      const count = activeFilters.neighborhoods.size;
      if (count === 0) {
        setFilterLabel("neighborhood-button", "Neighborhood");
        setFilterActive("neighborhood-button", false);
      } else if (count === 1) {
        setFilterLabel("neighborhood-button", [...activeFilters.neighborhoods][0]);
        setFilterActive("neighborhood-button", true);
      } else {
        setFilterLabel("neighborhood-button", `${count} Neighborhoods`);
        setFilterActive("neighborhood-button", true);
      }
    }

    neighborhoods.forEach((neighborhood) => {
      const li = document.createElement("li");
      li.className = "neighborhood-option";
      li.setAttribute("data-value", neighborhood);
      li.textContent = neighborhood;
      li.style.cursor = "pointer";
      li.style.padding = "5px";
      li.addEventListener("click", () => {
        if (activeFilters.neighborhoods.has(neighborhood)) {
          activeFilters.neighborhoods.delete(neighborhood);
          li.classList.remove("filter-option-selected");
        } else {
          activeFilters.neighborhoods.add(neighborhood);
          li.classList.add("filter-option-selected");
        }
        updateNeighborhoodLabel();
        applyFilters();
      });
      neighborhoodOptions.appendChild(li);
    });

    const allNeighborhoodOption = document.createElement("li");
    allNeighborhoodOption.className = "neighborhood-option";
    allNeighborhoodOption.setAttribute("data-value", "All");
    allNeighborhoodOption.textContent = "All";
    allNeighborhoodOption.style.cursor = "pointer";
    allNeighborhoodOption.style.padding = "5px";
    allNeighborhoodOption.style.fontWeight = "bold";
    allNeighborhoodOption.addEventListener("click", () => {
      activeFilters.neighborhoods.clear();
      document.querySelectorAll(".neighborhood-option").forEach((opt) => opt.classList.remove("filter-option-selected"));
      updateNeighborhoodLabel();
      applyFilters();
    });
    neighborhoodOptions.prepend(allNeighborhoodOption);

    // Add search functionality
    const neighborhoodSearch = document.getElementById("neighborhood-search");
    neighborhoodSearch.addEventListener("input", () => {
      const query = neighborhoodSearch.value.toLowerCase();
      document.querySelectorAll(".neighborhood-option").forEach((option) => {
        const neighborhood = option.getAttribute("data-value").toLowerCase();
        if (
          neighborhood.includes(query) ||
          option.getAttribute("data-value") === "All"
        ) {
          option.style.display = "block";
        } else {
          option.style.display = "none";
        }
      });
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
        markers.push(marker);
        marker.addTo(leafletmap);
        markerLayerGroup.addLayer(marker); // Add marker to the layer group
      }
    });

    // Initialize Fuse.js for fuzzy search
    const fuse = new Fuse(data, {
      keys: ["BUSINESS", "ADDRESS_STREET", "ADDRESS_CITY", "ADDRESS_STATE"],
    });

    // Add Leaflet Search control
    const searchControl = new L.Control.Search({
      layer: markerLayerGroup,
      propertyName: "businessName", // Search by business name
      filterData: function (text, records) {
        const jsons = fuse.search(text);
        const ret = {};
        jsons.forEach((result) => {
          const key = result.item.BUSINESS;
          ret[key] = records[key];
        });
        return ret;
      },
      marker: false, // Disable default marker behavior
      moveToLocation: function (latlng, title, map) {
        // Zoom to the marker and open its popup
        map.setView(latlng, 16); // Adjust zoom level as needed
        const marker = markers.find((m) => m.getLatLng().equals(latlng));
        if (marker) {
          marker.openPopup();
        }
      },
    });

    // Add the search control to the map
    leafletmap.addControl(searchControl);

    // Handle search location found
    searchControl.on("search:locationfound", function (e) {
      e.layer.openPopup();
    });
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
setupDropdownToggle("neighborhood-button", "neighborhood-dropdown");

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

// Philly Yes/No toggle in Add Bar modal
document.querySelectorAll('input[name="isPhiladelphia"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    const isPhilly = document.getElementById("is-philly-yes").checked;
    document.getElementById("neighborhood-field").style.display = isPhilly ? "block" : "none";
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
        // Populate the edit fields with the selected bar's data
        document.getElementById("edit-business-name").value =
          marker.businessName;
        document.getElementById("edit-address").value = marker.address;

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

document
  .getElementById("bar-submission-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    const businessName = document.getElementById("business-name").value;
    const streetAddress = document.getElementById("street-address").value;
    const isPhilly = document.getElementById("is-philly-yes").checked;
    const neighborhood = isPhilly ? document.getElementById("neighborhood").value : "";
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

    // Geocode the address
    let lat = null, lng = null;
    try {
      const geoRes = await fetch(`${API_BASE}/api/geocode?address=${encodeURIComponent(fullAddress)}`);
      const geoData = await geoRes.json();
      lat = geoData.lat;
      lng = geoData.lng;
    } catch (e) {
      console.warn("Geocode failed:", e);
    }

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
        alert("Your submission has been sent for review!");
        document.getElementById("bar-submission-form").reset();
        bootstrap.Modal.getInstance(document.getElementById("addBarModal")).hide();
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("There was an error submitting your request. Please try again.");
      });
  });
// Populate the table with data from the CSV
function populateTable(data) {
  const tableBody = document.querySelector("#bar-table tbody");
  tableBody.innerHTML = ""; // Clear existing rows

  data.forEach((row, index) => {
    // Skip rows with undefined or missing required fields
    if (
      !row.BUSINESS ||
      !row.ADDRESS_STREET ||
      !row.NEIGHBORHOOD ||
      !row.WEEKDAY ||
      !row.TIME
    ) {
      return;
    }

    const tr = document.createElement("tr");
    tr.setAttribute("data-index", index); // Store the index for reference

    tr.innerHTML = `
    <td>${row.BUSINESS}</td>
    <td class="d-lg-none">${row.ADDRESS_STREET}, ${row.ADDRESS_CITY}, ${row.ADDRESS_STATE} ${row.ADDRESS_ZIP}</td>
    <td>${row.NEIGHBORHOOD}</td>
    <td>${row.WEEKDAY}</td>
    <td>${row.TIME}</td>
    `;

    // Add click event to zoom to marker and open popup
    tr.addEventListener("click", () => {
      const marker = markers[index];
      if (marker) {
        leafletmap.setView(marker.getLatLng(), 16); // Zoom to marker
        marker.openPopup(); // Open popup
      }
    });

    tableBody.appendChild(tr);
  });
}

// Filter the table based on search input
function filterTable(query) {
  const rows = document.querySelectorAll("#bar-table tbody tr");
  rows.forEach((row) => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(query.toLowerCase()) ? "" : "none";
  });
}

// Add event listener for the search bar
document.getElementById("bar-search").addEventListener("input", (event) => {
  filterTable(event.target.value);
});

// Populate the table after parsing the CSV
fetch(`${API_BASE}/api/quizzo`)
  .then((response) => response.json())
  .then(function (data) {
    populateTable(data);
  })
  .catch(function (err) {
    console.error("Failed to load quizzo data for table:", err);
  });
