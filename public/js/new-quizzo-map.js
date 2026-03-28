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

// 2. Load CSV and add markers
var markers = [];

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

      li.addEventListener("click", (event) => {
        const selectedTime = event.target.getAttribute("data-value");
        console.log("Selected time:", selectedTime);

        markers.forEach(function (marker) {
          if (!(marker instanceof L.Marker)) return;

          // If "All" is selected, add all markers back to the map
          if (selectedTime === "All" || marker.time === selectedTime) {
            if (!leafletmap.hasLayer(marker)) {
              marker.addTo(leafletmap);
            }
          } else {
            if (leafletmap.hasLayer(marker)) {
              leafletmap.removeLayer(marker);
            }
          }
        });
      });

      timeOptions.appendChild(li);
    });

    // Add the "All" option at the top of the dropdown
    const allOption = document.createElement("li");
    allOption.className = "time-option";
    allOption.setAttribute("data-value", "All");
    allOption.textContent = "All";
    allOption.addEventListener("click", (event) => {
      const selectedTime = event.target.getAttribute("data-value");
      console.log("Selected time:", selectedTime);

      markers.forEach(function (marker) {
        if (!(marker instanceof L.Marker)) return;

        // Add all markers back to the map when "All" is selected
        if (!leafletmap.hasLayer(marker)) {
          marker.addTo(leafletmap);
        }
      });

      // Close the dropdown after selection
      const timeDropdown = document.getElementById("time-dropdown");
      timeDropdown.style.display = "none";
    });
    // Prepend the "All" option to the dropdown
    timeOptions.prepend(allOption);

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

      li.addEventListener("click", (event) => {
        const selectedFirstPrize = event.target.getAttribute("data-value");
        console.log("Selected firstPrize:", selectedFirstPrize);

        markers.forEach(function (marker) {
          if (!(marker instanceof L.Marker)) return;

          // If "All" is selected, add all markers back to the map
          if (
            selectedFirstPrize === "All" ||
            marker.firstPrize === selectedFirstPrize
          ) {
            if (!leafletmap.hasLayer(marker)) {
              marker.addTo(leafletmap);
            }
          } else {
            if (leafletmap.hasLayer(marker)) {
              leafletmap.removeLayer(marker);
            }
          }
        });
      });

      firstPrizeOptions.appendChild(li);
    });
    // Add the "All" option to the First Prize dropdown
    const allFirstPrizeOption = document.createElement("li");
    allFirstPrizeOption.className = "first-prize-option";
    allFirstPrizeOption.setAttribute("data-value", "All");
    allFirstPrizeOption.textContent = "All";
    allFirstPrizeOption.addEventListener("click", (event) => {
      const selectedFirstPrize = event.target.getAttribute("data-value");
      console.log("Selected firstPrize:", selectedFirstPrize);

      markers.forEach(function (marker) {
        if (!(marker instanceof L.Marker)) return;

        // Add all markers back to the map when "All" is selected
        if (!leafletmap.hasLayer(marker)) {
          marker.addTo(leafletmap);
        }
      });

      // Close the dropdown after selection
      const firstPrizeDropdown = document.getElementById(
        "first-prize-dropdown",
      );
      firstPrizeDropdown.style.display = "none";
    });
    firstPrizeOptions.prepend(allFirstPrizeOption);

    // Populate the Neighborhood dropdown
    const neighborhoodOptions = document.getElementById("neighborhood-options");
    const selectedNeighborhoods = new Set(); // Store selected neighborhoods

    neighborhoods.forEach((neighborhood) => {
      const li = document.createElement("li");
      li.className = "neighborhood-option";
      li.setAttribute("data-value", neighborhood);
      li.textContent = neighborhood;
      li.style.cursor = "pointer";
      li.style.padding = "5px";

      // Handle selection toggle
      li.addEventListener("click", (event) => {
        const selectedNeighborhood = event.target.getAttribute("data-value");

        if (selectedNeighborhoods.has(selectedNeighborhood)) {
          selectedNeighborhoods.delete(selectedNeighborhood);
          li.style.backgroundColor = ""; // Deselect
        } else {
          selectedNeighborhoods.add(selectedNeighborhood);
          li.style.backgroundColor = "#d3d3d3"; // Highlight selected
        }

        console.log(
          "Selected neighborhoods:",
          Array.from(selectedNeighborhoods),
        );

        // Filter markers based on selected neighborhoods
        markers.forEach((marker) => {
          if (!(marker instanceof L.Marker)) return;

          if (
            selectedNeighborhoods.size === 0 || // Show all markers if none selected
            selectedNeighborhoods.has(marker.neighborhood)
          ) {
            if (!leafletmap.hasLayer(marker)) {
              marker.addTo(leafletmap);
            }
          } else {
            if (leafletmap.hasLayer(marker)) {
              leafletmap.removeLayer(marker);
            }
          }
        });
      });

      neighborhoodOptions.appendChild(li);
    });

    // Add the "All" option to reset selections
    const allNeighborhoodOption = document.createElement("li");
    allNeighborhoodOption.className = "neighborhood-option";
    allNeighborhoodOption.setAttribute("data-value", "All");
    allNeighborhoodOption.textContent = "All";
    allNeighborhoodOption.style.cursor = "pointer";
    allNeighborhoodOption.style.padding = "5px";
    allNeighborhoodOption.style.fontWeight = "bold";

    allNeighborhoodOption.addEventListener("click", () => {
      selectedNeighborhoods.clear(); // Clear all selections
      document.querySelectorAll(".neighborhood-option").forEach((option) => {
        option.style.backgroundColor = ""; // Reset background color
      });

      console.log("All neighborhoods selected");

      // Show all markers
      markers.forEach((marker) => {
        if (!(marker instanceof L.Marker)) return;

        if (!leafletmap.hasLayer(marker)) {
          marker.addTo(leafletmap);
        }
      });
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
        var popupContent = `
        <div style="font-family: Lato;">
            <p style="text-align: center; font-size: 18px; font-weight: bold; margin: 15px 0;"><u>${row.BUSINESS}</u></p>
            <p style="text-align: center; font-size: 14px; margin: 15px 0;">${address}</p>
            <p style="text-align: center; font-size: 14px; margin: 5px 0;">${neighborhood}</p>
            <p style="text-align: center; font-size: 16px; margin: 15px 0;"><b>${row.WEEKDAY} - ${row.TIME}</b></p>
            ${row.HOST ? `<p style="text-align: center; font-size: 16px; margin: 15px 0;">Host: ${row.HOST} <br>` : ""}
            ${row.PRIZE_1_TYPE ? `<p style="text-align: center; font-size: 16px; margin: 15px 0;">First Prize: ${firstPrize} - $${row.PRIZE_1_AMOUNT}${secondPrize ? `<br> Second Prize: ${secondPrize} - $${row.PRIZE_2_AMOUNT}0</p>` : "</p>"}` : ""}
        </div>
        `;
        var marker = L.marker([lat, lng], {
          icon: createMartiniIcon("darkgreen"),
        }).bindPopup(popupContent);
        marker.weekday = weekday; // Store weekday in marker for filtering
        marker.time = time; // Store time in marker for filtering
        // marker.eventType = eventType;
        marker.firstPrize = firstPrize;
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
    // Reset all dropdown selections
    document.querySelectorAll(".filter-box ul li").forEach((li) => {
      li.style.backgroundColor = ""; // Reset background color
    });

    // Clear selected neighborhoods
    // selectedNeighborhoods.clear();

    // Show all markers on the map
    markers.forEach((marker) => {
      if (!(marker instanceof L.Marker)) return;
      if (!leafletmap.hasLayer(marker)) {
        marker.addTo(leafletmap);
      }
    });

    // Reset the map view to the default center and zoom
    leafletmap.setView(defaultCenter, defaultZoom);

    // Reset search inputs
    document.getElementById("neighborhood-search").value = "";
    document.getElementById("bar-search").value = "";

    console.log("Filters and map view reset.");
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

// Toggle First Prize dropdown visibility
const firstPrizeButton = document.getElementById("first-prize-button");
const firstPrizeDropdown = document.getElementById("first-prize-dropdown");
firstPrizeButton.addEventListener("click", () => {
  const isVisible = firstPrizeDropdown.style.display === "block";
  firstPrizeDropdown.style.display = isVisible ? "none" : "block";
});
// Close dropdown if clicked outside
document.addEventListener("click", (event) => {
  if (
    !firstPrizeButton.contains(event.target) &&
    !firstPrizeDropdown.contains(event.target)
  ) {
    firstPrizeDropdown.style.display = "none";
  }
});

// Toggle Start Time dropdown visibility
const timeButton = document.getElementById("time-button");
const timeDropdown = document.getElementById("time-dropdown");
timeButton.addEventListener("click", () => {
  const isVisible = timeDropdown.style.display === "block";
  timeDropdown.style.display = isVisible ? "none" : "block";
});
// Close dropdown if clicked outside
document.addEventListener("click", (event) => {
  if (
    !timeButton.contains(event.target) &&
    !timeDropdown.contains(event.target)
  ) {
    timeDropdown.style.display = "none";
  }
});
// Toggle Neighborhood dropdown visibility
const neighborhoodButton = document.getElementById("neighborhood-button");
const neighborhoodDropdown = document.getElementById("neighborhood-dropdown");
neighborhoodButton.addEventListener("click", () => {
  const isVisible = neighborhoodDropdown.style.display === "block";
  neighborhoodDropdown.style.display = isVisible ? "none" : "block";
});
// Close dropdown if clicked outside
document.addEventListener("click", (event) => {
  if (
    !neighborhoodButton.contains(event.target) &&
    !neighborhoodDropdown.contains(event.target)
  ) {
    neighborhoodDropdown.style.display = "none";
  }
});
const weekdayButton = document.getElementById("weekday-button");
const weekdayDropdown = document.getElementById("weekday-dropdown");
// Toggle dropdown visibility
weekdayButton.addEventListener("click", () => {
  const isVisible = weekdayDropdown.style.display === "block";
  weekdayDropdown.style.display = isVisible ? "none" : "block";
});
// Handle weekday selection
document.querySelectorAll(".weekday-option").forEach((option) => {
  option.addEventListener("click", (event) => {
    const selectedWeekday = event.target.getAttribute("data-value");
    console.log("Selected weekday:", selectedWeekday);
    markers.forEach(function (marker) {
      // Ensure marker is valid before acting on it
      if (!(marker instanceof L.Marker)) return;

      if (selectedWeekday === "All" || marker.weekday === selectedWeekday) {
        if (!leafletmap.hasLayer(marker)) {
          marker.addTo(leafletmap);
        }
      } else {
        if (leafletmap.hasLayer(marker)) {
          leafletmap.removeLayer(marker);
        }
      }
    });

    // Close the dropdown after selection
    // weekdayDropdown.style.display = "none";
  });
});

// Close dropdown if clicked outside
document.addEventListener("click", (event) => {
  if (
    !weekdayButton.contains(event.target) &&
    !weekdayDropdown.contains(event.target)
  ) {
    weekdayDropdown.style.display = "none";
  }
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
