// ─── Shared basemap tile provider ───────────────────────────────────────────
// CARTO's free basemaps.cartocdn.com tiles started requiring an API key we
// don't have, which broke every map (tiles rendered as "API KEY REQUIRED"
// watermarks). This swaps in Esri's ArcGIS Online "Canvas" basemaps, which are
// free, require no key/signup, and ship both a light and dark gray style — the
// closest no-key equivalent to CARTO's light_all/dark_all.
//
// Esri splits each style into two layers: a "Base" (the gray canvas) and a
// "Reference" (labels/roads/borders) drawn on top. MappyBasemap.create()
// bundles both into one object so every map can keep treating "the basemap"
// as a single thing to add/remove, same as the old single-layer CARTO setup.
//
// Usage:
//   var bm = MappyBasemap.create(map, 'dark');   // or 'light'
//   ...
//   bm.remove();
//   bm = MappyBasemap.create(map, 'light');
(function (global) {
  var ATTRIBUTION = 'Esri, HERE, Garmin, &copy; OpenStreetMap contributors, and the GIS user community';

  function urlFor(style, layer) {
    var cap = style === 'dark' ? 'Dark' : 'Light';
    return 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_' +
      cap + '_Gray_' + layer + '/MapServer/tile/{z}/{y}/{x}';
  }

  // These Esri tiles are only rendered natively up to zoom 16; maxNativeZoom
  // tells Leaflet to upscale those tiles for deeper zoom instead of showing
  // blank gaps when a user scrolls/pinches in past that level.
  var TILE_OPTS = { maxZoom: 19, maxNativeZoom: 16 };

  function create(map, style) {
    var base = L.tileLayer(urlFor(style, 'Base'),
      Object.assign({ attribution: ATTRIBUTION }, TILE_OPTS)).addTo(map);
    var labels = L.tileLayer(urlFor(style, 'Reference'),
      Object.assign({ pane: base.options.pane }, TILE_OPTS)).addTo(map);
    return {
      style: style,
      base: base,
      labels: labels,
      remove: function () { map.removeLayer(base); map.removeLayer(labels); },
    };
  }

  global.MappyBasemap = { create: create, ATTRIBUTION: ATTRIBUTION };
})(window);
