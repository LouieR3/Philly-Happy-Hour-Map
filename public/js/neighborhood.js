// NEIGHBORHOOD MAP 

// Initialize the map
const map = L.map('neighborhood-map').setView([39.9526, -75.1652], 12); // Centered on Philadelphia

// Add a tile layer (OpenStreetMap)
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap & CartoDB',
  subdomains: 'abcd'
}).addTo(map);

// Store references to the neighborhood labels and polygons
const neighborhoodLabels = [];
const neighborhoodPolygons = []; // Store polygons for point-in-polygon checks

// Fetch the GeoJSON file and add it to the map
fetch('../Quizzo/philadelphia-neighborhoods.geojson')
  .then(response => response.json())
  .then(geojsonData => {
    // Add a buffer of 50 feet (approximately 15.24 meters) to each polygon
    const bufferedGeoJSON = {
      type: 'FeatureCollection',
      features: geojsonData.features.map(feature => {
        const buffered = turf.buffer(feature, 18.00, { units: 'meters' }); // Buffer by 15.24 meters
        return buffered;
      })
    };

    // Add the buffered GeoJSON data to the map
    L.geoJSON(bufferedGeoJSON, {
      style: function (feature) {
        return {
          color: "#3388ff", // Border color
          weight: 2, // Border width
          fillColor: "#6baed6", // Fill color
          fillOpacity: 0.5 // Fill opacity
        };
      },
      onEachFeature: function (feature, layer) {
        if (feature.properties && feature.properties.NAME) {
          // Replace underscores with spaces in the NAME property
          const neighborhoodName = feature.properties.NAME.replace(/_/g, ' ');

          // Add a label on top of the polygon (but hide it initially)
          const center = layer.getBounds().getCenter(); // Get the center of the polygon
          const label = L.marker(center, {
            icon: L.divIcon({
              className: 'neighborhood-label',
              html: `<div style="font-size: 12px; font-weight: bold; color: #333;">${neighborhoodName}</div>`,
              iconSize: [100, 20],
              iconAnchor: [50, 10]
            })
          });

          // Store the label and polygon for later use
          neighborhoodLabels.push(label);
          neighborhoodPolygons.push({ name: neighborhoodName, layer });

          // Bind a popup to the polygon
          layer.bindPopup(`<strong>${neighborhoodName}</strong>`);
        }
      }
    }).addTo(map);

    // Load quizzo_list.csv and add points to the map
    Papa.parse('../Quizzo/quizzo_extra.csv', {
      download: true,
      header: true,
      complete: function (results) {
        results.data.forEach(row => {
          const lat = parseFloat(row.Latitude);
          const lng = parseFloat(row.Longitude);
          const businessName = row.BUSINESS;
          const neighborhood = row.NEIGHBORHOOD ? row.NEIGHBORHOOD.replace(/_/g, ' ').trim().toUpperCase() : '';

          if (!isNaN(lat) && !isNaN(lng)) {
            // Check if the point is inside any polygon
            let markerColor = 'black'; // Default color
            let matchedPolygonName = null;

            neighborhoodPolygons.forEach(({ name, layer }) => {
              if (layer.getBounds().contains([lat, lng])) {
                matchedPolygonName = name; // Get the NAME of the polygon the point falls within
              }
            });

            // Compare the neighborhood of the point with the polygon NAME
            if (matchedPolygonName && matchedPolygonName === neighborhood) {
              markerColor = 'green'; // Point is inside the correct polygon
            }

            // Create a marker
            const marker = L.circleMarker([lat, lng], {
              radius: 6,
              fillColor: markerColor,
              color: markerColor,
              weight: 1,
              opacity: 1,
              fillOpacity: 0.8
            }).addTo(map);

            // Add a popup to the marker
            marker.bindPopup(`
              <div style="font-family: Arial; font-size: 14px;">
                <strong>${businessName}</strong><br>
                Neighborhood: ${neighborhood}<br>
                Latitude: ${lat}<br>
                Longitude: ${lng}
              </div>
            `);
          }
        });
      }
    });

    // Add or remove labels based on zoom level
    map.on('zoomend', () => {
      const currentZoom = map.getZoom();
      if (currentZoom >= 13) {
        // Add labels to the map if zoomed in
        neighborhoodLabels.forEach(label => {
          if (!map.hasLayer(label)) {
            label.addTo(map);
          }
        });
      } else {
        // Remove labels from the map if zoomed out
        neighborhoodLabels.forEach(label => {
          if (map.hasLayer(label)) {
            map.removeLayer(label);
          }
        });
      }
    });
  })
  .catch(error => {
    console.error('Error loading GeoJSON:', error);
  });