const SPORTS_API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:3000'
  : 'https://philly-happy-hour-map-production.up.railway.app';

// ─── Map init ─────────────────────────────────────────────────────────────────
var sportsMap = L.map('sports-leaflet-map').setView([39.951, -75.163], 12);
sportsMap.zoomControl.setPosition('bottomright');

var sportsBasemapLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap & CartoDB',
  subdomains: 'abcd',
}).addTo(sportsMap);

var sportsIsLightMode = false;

// ─── Basemap toggle ───────────────────────────────────────────────────────────
function toggleSportsBasemap() {
  sportsMap.removeLayer(sportsBasemapLayer);
  if (sportsIsLightMode) {
    sportsBasemapLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap & CartoDB', subdomains: 'abcd',
    }).addTo(sportsMap);
    sportsIsLightMode = false;
    document.getElementById('sports-basemap-toggle').innerHTML = '<i class="fa-solid fa-sun"></i><span>Light Mode</span>';
  } else {
    sportsBasemapLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap & CartoDB', subdomains: 'abcd',
    }).addTo(sportsMap);
    sportsIsLightMode = true;
    document.getElementById('sports-basemap-toggle').innerHTML = '<i class="fa-solid fa-moon"></i><span>Dark Mode</span>';
  }
}

const sportsToggleBtn = document.getElementById('sports-basemap-toggle');
if (sportsToggleBtn) sportsToggleBtn.addEventListener('click', toggleSportsBasemap);

// ─── Marker icon ──────────────────────────────────────────────────────────────
function createSportsIcon(color, logoUrl) {
  color = color || '#f59e0b';
  
  // If logo URL provided, use it as the icon
  if (logoUrl) {
    return L.divIcon({
      html: `<div class="custom-pin">
        <div class="pin-circle" style="background-color:${color};overflow:hidden;">
          <img src="${logoUrl}" style="width:100%;height:100%;object-fit:cover;" alt="team-logo" />
        </div>
        <div class="pin-tail" style="background-color:${color};"></div>
      </div>`,
      className: 'custom-fa-icon',
      iconSize: [30, 30],
      iconAnchor: [15, 30],
      popupAnchor: [0, -30],
    });
  }
  
  // Default TV icon
  return L.divIcon({
    html: `<div class="custom-pin">
      <div class="pin-circle" style="background-color:${color};">
        <i class="fa-solid fa-tv" style="font-size:11px;"></i>
      </div>
      <div class="pin-tail" style="background-color:${color};"></div>
    </div>`,
    className: 'custom-fa-icon',
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });
}

// League → accent color
function leagueColor(league) {
  switch ((league || '').toUpperCase()) {
    case 'NFL':            return '#013369';
    case 'NBA':            return '#c9082a';
    case 'MLB':            return '#002d72';
    case 'NHL':            return '#00539b';
    case 'MLS':            return '#1a7a4a';
    case 'PREMIER LEAGUE': return '#38003c';
    default:               return '#f59e0b';
  }
}

// ─── State ────────────────────────────────────────────────────────────────────
var sportsMarkers = [];
var sportsAllData = [];
var sportsAllTeams = [];
var sportsGeoJson = null;
var sportsTeamLogoMap  = {};   // team_name → logo_url
var sportsTeamLeagueMap = {};  // team_name → league key

const sportsActiveFilters = {
  league:       null,
  team:         null,
  phillyOnly:   false,
  neighborhood: null,
  region:       null,
};

// ─── Filter engine ────────────────────────────────────────────────────────────
function updateMarkerIconForFilter(marker) {
  let newColor = '#f59e0b';
  let newLogo = null;

  // If a specific team is selected, use that team's color and logo
  if (sportsActiveFilters.team) {
    const selectedTeam = sportsAllTeams.find(t => t.team_name === sportsActiveFilters.team);
    if (selectedTeam) {
      newColor = selectedTeam.team_color || '#f59e0b';
      newLogo = selectedTeam.logo_url;
    }
  } 
  // If a league is selected, find first team from that league that the bar has
  else if (sportsActiveFilters.league) {
    for (let team of marker.allTeams) {
      const teamObj = sportsAllTeams.find(t => t.team_name === team && t.league === sportsActiveFilters.league);
      if (teamObj) {
        newColor = teamObj.team_color || '#f59e0b';
        newLogo = teamObj.logo_url;
        break;
      }
    }
    // If no team from this league found, use league color with TV icon
    if (!newLogo) {
      newColor = leagueColor(sportsActiveFilters.league);
    }
  }
  // No filter - use default
  else {
    if (marker.defaultColor !== undefined) {
      newColor = marker.defaultColor;
      newLogo = marker.defaultLogo;
    }
  }

  marker.setIcon(createSportsIcon(newColor, newLogo));
}

function applySportsFilters() {
  sportsMarkers.forEach(function(marker) {
    if (!(marker instanceof L.Marker)) return;
    const passes =
      (!sportsActiveFilters.phillyOnly || marker.hasPhillyAffil) &&
      (!sportsActiveFilters.league     || marker.leagues.has(sportsActiveFilters.league)) &&
      (!sportsActiveFilters.team       || marker.allTeams.has(sportsActiveFilters.team)) &&
      (!sportsActiveFilters.neighborhood || marker.neighborhood === sportsActiveFilters.neighborhood);

    if (passes) {
      if (!sportsMap.hasLayer(marker)) marker.addTo(sportsMap);
      updateMarkerIconForFilter(marker);
    } else {
      if (sportsMap.hasLayer(marker)) sportsMap.removeLayer(marker);
    }
  });
}

// ─── Filter UI helpers ────────────────────────────────────────────────────────
function setSportsFilterLabel(btnId, text) {
  const el = document.querySelector('#' + btnId + ' .filter-label');
  if (el) el.textContent = text;
}
function setSportsFilterActive(btnId, isActive) {
  const btn = document.getElementById(btnId);
  if (btn) btn.classList.toggle('filter-active', isActive);
}

// ─── Derive team/league sets for a bar document ───────────────────────────────
function getBarTeamSets(bar) {
  const allTeams = new Set();
  (bar.philly_affiliates || []).forEach(function(t) { if (t) allTeams.add(t); });
  (bar.other_nhl_nba_mlb_nfl_teams || []).forEach(function(t) { if (t) allTeams.add(t); });
  (bar.other_soccer_teams || []).forEach(function(t) { if (t) allTeams.add(t); });
  if (bar.premier_league_team) allTeams.add(bar.premier_league_team);

  const leagues = new Set();
  allTeams.forEach(function(t) {
    var l = sportsTeamLeagueMap[t];
    if (l) leagues.add(l);
  });
  return { allTeams: allTeams, leagues: leagues };
}

// ─── Build popup HTML ─────────────────────────────────────────────────────────
function buildSportsPopup(bar) {
  const phillyTeams = (bar.philly_affiliates || []).filter(Boolean);
  const otherTeams  = [
    ...(bar.other_nhl_nba_mlb_nfl_teams || []),
    bar.premier_league_team,
    ...(bar.other_soccer_teams || []),
  ].filter(Boolean);

  function teamChip(team, size) {
    var logo = sportsTeamLogoMap[team];
    if (logo) {
      return '<img src="' + logo + '" alt="' + team + '" title="' + team +
             '" style="height:' + size + 'px;width:' + size + 'px;object-fit:contain;border-radius:2px;"' +
             ' onerror="this.style.display=\'none\'"/>';
    }
    return '<span style="font-size:11px;background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:10px;">' + team + '</span>';
  }

  var phillyHtml = phillyTeams.map(function(t) { return teamChip(t, 24); }).join('');
  var otherHtml  = otherTeams.map(function(t)  { return teamChip(t, 20); }).join('');

  var teamsSection = '';
  if (phillyTeams.length) {
    teamsSection += '<div style="margin-bottom:6px;">' +
      '<div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Philly Teams</div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">' + phillyHtml + '</div></div>';
  }
  if (otherTeams.length) {
    teamsSection += '<div style="margin-bottom:6px;">' +
      '<div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Other Teams</div>' +
      '<div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;">' + otherHtml + '</div></div>';
  }
  if (!phillyTeams.length && !otherTeams.length) {
    teamsSection = '<div style="font-size:12px;color:#64748b;font-style:italic;margin-bottom:6px;">Team affiliations not yet listed</div>';
  }

  var badges = '';
  if (bar['Yelp Rating']) badges += '<span style="background:rgba(251,191,36,0.12);color:#fbbf24;font-size:13px;font-weight:600;padding:2px 8px;border-radius:20px;">⭐ ' + bar['Yelp Rating'] + '</span>';
  if (bar.Price)          badges += '<span style="background:rgba(74,150,93,0.82);color:#fff;font-size:13px;font-weight:600;padding:2px 8px;border-radius:20px;">' + bar.Price + '</span>';

  return '<div style="font-family:\'Red Hat Text\',sans-serif;width:240px;border-radius:8px;overflow:hidden;">' +
    '<div style="background:#7c2d12;padding:14px 16px 10px;">' +
      '<p style="margin:0;font-size:15px;font-weight:600;color:#fff;">📺 ' + (bar.Name || '—') + '</p>' +
      '<p style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,0.7);">' + (bar.Address || '') + '</p>' +
      (bar.Neighborhood ? '<p style="margin:4px 0 0;font-size:13px;color:#fff;">' + bar.Neighborhood + '</p>' : '') +
    '</div>' +
    '<div style="padding:12px 16px;display:flex;flex-direction:column;gap:2px;background:#1a2332;color:#e2e8f0;">' +
      teamsSection +
      (badges ? '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px;">' + badges + '</div>' : '') +
      (bar.Website ? '<a href="' + bar.Website + '" target="_blank" style="font-size:14px;color:#f59e0b;text-decoration:none;margin-top:6px;">Visit Website →</a>' : '') +
    '</div></div>';
}

// ─── Sidebar card list ────────────────────────────────────────────────────────
function populateSportsSidebar(data) {
  var list = document.getElementById('sports-bar-list');
  if (!list) return;
  list.innerHTML = '';
  var photoTargets = new Map();

  var sorted = data.slice().sort(function(a, b) {
    return (a.Name || '').localeCompare(b.Name || '');
  });

  sorted.forEach(function(row) {
    if (!row.Name) return;

    var phillyTeams = (row.philly_affiliates || []).filter(Boolean);
    var tags = [];
    if (phillyTeams.length) tags.push('🦅 ' + phillyTeams.slice(0, 2).join(', '));
    if (row['Yelp Rating'])  tags.push('⭐ ' + row['Yelp Rating']);
    if (row.Price)           tags.push(row.Price);

    var card = document.createElement('div');
    card.className = 'bar-card';

    var placeholder = document.createElement('div');
    placeholder.className = 'bar-card-thumb-placeholder';
    placeholder.innerHTML = '<i class="fa-solid fa-tv"></i>';
    photoTargets.set(row.Name, placeholder);

    var body = document.createElement('div');
    body.className = 'bar-card-body';
    body.innerHTML =
      '<div class="bar-card-name">' + row.Name + '</div>' +
      '<div class="bar-card-address">' + (row.Address || row.Neighborhood || '') + '</div>' +
      '<div class="bar-card-tags">' + tags.map(function(t) { return '<span class="bar-card-tag">' + t + '</span>'; }).join('') + '</div>';

    card.appendChild(placeholder);
    card.appendChild(body);

    card.addEventListener('click', function() {
      var marker = sportsMarkers.find(function(m) { return m.name === row.Name; });
      if (marker) {
        sportsMap.setView(marker.getLatLng(), 16);
        marker.openPopup();
        var sheet = document.getElementById('sports-table-column');
        if (sheet) sheet.classList.remove('sheet-open');
      }
    });
    list.appendChild(card);
  });

  fetchSportsPhotos(photoTargets);
}

async function fetchSportsPhotos(nameToEl) {
  if (!nameToEl.size) return;
  try {
    var names = Array.from(nameToEl.keys());
    var res = await fetch(SPORTS_API_BASE + '/api/bar-photos?names=' + encodeURIComponent(names.join('|')));
    var metaMap = await res.json();
    Object.entries(metaMap).forEach(function([name, meta]) {
      var el = nameToEl.get(name);
      if (!el || !meta.photos || !meta.photos.length) return;
      var img = document.createElement('img');
      img.className = 'bar-card-thumb';
      img.src = meta.photos[0];
      img.alt = name;
      el.replaceWith(img);
    });
  } catch (e) {
    console.warn('[sports-bar-photos]', e.message);
  }
}

// ─── Populate team dropdown (grouped by league) ───────────────────────────────
function buildSportsTeamDropdown(teams) {
  var opts = document.getElementById('sports-team-options');
  if (!opts) return;
  opts.innerHTML = '';

  var DD_STYLE      = 'padding:6px 12px;cursor:pointer;color:#e2e8f0;display:flex;align-items:center;gap:8px;';
  var DD_HOVER_IN   = function() { this.style.background = 'rgba(255,255,255,0.08)'; };
  var DD_HOVER_OUT  = function() { this.style.background = ''; };

  // "All teams" option
  var allLi = document.createElement('li');
  allLi.style.cssText = 'padding:7px 12px;cursor:pointer;color:#e2e8f0;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:4px;';
  allLi.textContent = 'All Teams';
  allLi.addEventListener('mouseover', DD_HOVER_IN);
  allLi.addEventListener('mouseout', DD_HOVER_OUT);
  allLi.addEventListener('click', function() {
    sportsActiveFilters.team = null;
    setSportsFilterLabel('sports-team-button', 'Team');
    setSportsFilterActive('sports-team-button', false);
    document.getElementById('sports-team-dropdown').style.display = 'none';
    applySportsFilters();
  });
  opts.appendChild(allLi);

  var LEAGUE_ORDER = ['NFL', 'NBA', 'MLB', 'NHL', 'MLS', 'Premier League'];
  var byLeague = {};
  teams.forEach(function(t) {
    if (!byLeague[t.league]) byLeague[t.league] = [];
    byLeague[t.league].push(t);
  });

  LEAGUE_ORDER.forEach(function(league) {
    var leagueTeams = byLeague[league];
    if (!leagueTeams || !leagueTeams.length) return;

    // League header (non-clickable)
    var header = document.createElement('li');
    header.style.cssText = 'padding:4px 12px 2px;font-size:10px;color:' + leagueColor(league) + ';text-transform:uppercase;letter-spacing:0.1em;font-weight:700;pointer-events:none;margin-top:6px;';
    header.textContent = league;
    opts.appendChild(header);

    leagueTeams.sort(function(a, b) { return a.team_name.localeCompare(b.team_name); });
    leagueTeams.forEach(function(team) {
      var li = document.createElement('li');
      li.style.cssText = DD_STYLE;
      li.addEventListener('mouseover', DD_HOVER_IN);
      li.addEventListener('mouseout', DD_HOVER_OUT);

      if (team.logo_url) {
        var img = document.createElement('img');
        img.src = team.logo_url;
        img.alt = team.team_name;
        img.style.cssText = 'height:18px;width:18px;object-fit:contain;flex-shrink:0;';
        img.onerror = function() { this.style.display = 'none'; };
        li.appendChild(img);
      }

      var span = document.createElement('span');
      span.textContent = team.team_name;
      span.style.fontSize = '13px';
      li.appendChild(span);

      li.addEventListener('click', function() {
        sportsActiveFilters.team   = team.team_name;
        sportsActiveFilters.league = null;
        setSportsFilterLabel('sports-team-button', team.team_name);
        setSportsFilterActive('sports-team-button', true);
        setSportsFilterLabel('sports-league-button', 'League');
        setSportsFilterActive('sports-league-button', false);
        document.getElementById('sports-team-dropdown').style.display = 'none';
        applySportsFilters();
      });

      opts.appendChild(li);
    });
  });
}

// Build team dropdown filtered to only selected league
function buildSportsTeamDropdownForLeague(allTeams, league) {
  var filtered = league ? allTeams.filter(function(t) { return t.league === league; }) : allTeams;
  buildSportsTeamDropdown(filtered);
}

// Build empty team dropdown (when no league is selected)
function clearSportsTeamDropdown() {
  var opts = document.getElementById('sports-team-options');
  if (!opts) return;
  opts.innerHTML = '';
  
  var msg = document.createElement('li');
  msg.style.cssText = 'padding:12px;color:#94a3b8;font-size:12px;text-align:center;font-style:italic;';
  msg.textContent = 'Select a league first';
  opts.appendChild(msg);
}

// ─── Populate league dropdown ─────────────────────────────────────────────────
function buildSportsLeagueDropdown() {
  var opts = document.getElementById('sports-league-options');
  if (!opts) return;

  // var LEAGUES = ['All', 'NFL', 'NBA', 'MLB', 'NHL', 'MLS', 'Premier League'];
  var LEAGUES = ['All', 'NFL', 'Premier League'];
  var DD_STYLE     = 'padding:7px 12px;cursor:pointer;color:#e2e8f0;display:flex;align-items:center;gap:8px;';
  var DD_HOVER_IN  = function() { this.style.background = 'rgba(255,255,255,0.08)'; };
  var DD_HOVER_OUT = function() { this.style.background = ''; };

  LEAGUES.forEach(function(league) {
    var li = document.createElement('li');
    li.style.cssText = DD_STYLE;
    li.addEventListener('mouseover', DD_HOVER_IN);
    li.addEventListener('mouseout', DD_HOVER_OUT);

    if (league !== 'All') {
      var dot = document.createElement('span');
      dot.style.cssText = 'width:10px;height:10px;border-radius:50%;background:' + leagueColor(league) + ';flex-shrink:0;';
      li.appendChild(dot);
    }

    var span = document.createElement('span');
    span.textContent = league;
    li.appendChild(span);

    li.addEventListener('click', function() {
      if (league === 'All') {
        sportsActiveFilters.league = null;
        setSportsFilterLabel('sports-league-button', 'League');
        setSportsFilterActive('sports-league-button', false);
        clearSportsTeamDropdown();
      } else {
        sportsActiveFilters.league = league;
        sportsActiveFilters.team   = null;
        setSportsFilterLabel('sports-league-button', league);
        setSportsFilterActive('sports-league-button', true);
        setSportsFilterLabel('sports-team-button', 'Team');
        setSportsFilterActive('sports-team-button', false);
        buildSportsTeamDropdownForLeague(sportsAllTeams, league);
      }
      document.getElementById('sports-league-dropdown').style.display = 'none';
      applySportsFilters();
    });

    opts.appendChild(li);
  });
}

// ─── Map search control ───────────────────────────────────────────────────────
function addSportsMapSearchControl() {
  var SportsSearchControl = L.Control.extend({
    options: { position: 'topleft' },
    onAdd: function() {
      var c = L.DomUtil.create('div', 'map-search-control');
      c.innerHTML = '<input type="text" id="sports-map-search-field" placeholder="Search bars\u2026" autocomplete="off" /><ul id="sports-map-search-list"></ul>';
      L.DomEvent.disableClickPropagation(c);
      L.DomEvent.disableScrollPropagation(c);
      return c;
    },
  });
  sportsMap.addControl(new SportsSearchControl());

  document.getElementById('sports-map-search-field').addEventListener('input', function() {
    var q    = this.value.trim().toLowerCase();
    var list = document.getElementById('sports-map-search-list');
    list.innerHTML = '';
    if (q.length < 2) return;
    sportsMarkers
      .filter(function(m) { return m.name && m.name.toLowerCase().includes(q); })
      .slice(0, 8)
      .forEach(function(m) {
        var li = document.createElement('li');
        li.textContent = m.name;
        li.addEventListener('click', function() {
          sportsMap.setView(m.getLatLng(), 16);
          m.openPopup();
          document.getElementById('sports-map-search-field').value = m.name;
          list.innerHTML = '';
        });
        list.appendChild(li);
      });
  });

  document.addEventListener('click', function(e) {
    var field = document.getElementById('sports-map-search-field');
    var list  = document.getElementById('sports-map-search-list');
    if (field && list && !field.contains(e.target) && !list.contains(e.target)) {
      list.innerHTML = '';
    }
  });
}

// ─── GeoJSON region + neighborhood filters ────────────────────────────────────
function loadSportsGeoJson() {
  fetch('assets/philadelphia-neighborhoods.geojson')
    .then(function(r) { return r.json(); })
    .then(function(geoJson) {
      sportsGeoJson = geoJson;
      var nhHasMarker     = {};
      var regionHasMarker = {};

      sportsMarkers.forEach(function(marker) {
        var pt = turf.point([marker.getLatLng().lng, marker.getLatLng().lat]);
        geoJson.features.forEach(function(feature) {
          try {
            if (turf.booleanPointInPolygon(pt, feature)) {
              var name   = feature.properties.LISTNAME;
              var region = (feature.properties.GENERAL_AREA || '').trim();
              marker.neighborhood = name;
              if (!nhHasMarker[name]) nhHasMarker[name] = feature;
              if (region) {
                if (!regionHasMarker[region]) regionHasMarker[region] = [];
                regionHasMarker[region].push(feature);
              }
            }
          } catch (e) {}
        });
      });

      function zoomToFeatures(features) {
        var bbox = turf.bbox(turf.featureCollection(features));
        sportsMap.fitBounds([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], { padding: [30, 30] });
      }

      var DD_STYLE     = 'padding:7px 12px;cursor:pointer;color:#e2e8f0;';
      var DD_HOVER_IN  = function() { this.style.background = 'rgba(255,255,255,0.08)'; };
      var DD_HOVER_OUT = function() { this.style.background = ''; };

      function makeLi(text, onClick) {
        var li = document.createElement('li');
        li.style.cssText = DD_STYLE;
        li.textContent   = text;
        li.addEventListener('mouseover', DD_HOVER_IN);
        li.addEventListener('mouseout',  DD_HOVER_OUT);
        li.addEventListener('click', onClick);
        return li;
      }

      // Region dropdown
      var regionOpts    = document.getElementById('sports-region-options');
      var sortedRegions = Object.keys(regionHasMarker).sort();

      regionOpts.appendChild(makeLi('All', function() {
        sportsActiveFilters.region       = null;
        sportsActiveFilters.neighborhood = null;
        setSportsFilterLabel('sports-region-button', 'Philly Region');
        setSportsFilterActive('sports-region-button', false);
        document.getElementById('sports-region-dropdown').style.display = 'none';
        buildSportsNeighborhoodList(nhHasMarker, null);
        applySportsFilters();
        sportsMap.setView([39.951, -75.163], 12);
      }));

      sortedRegions.forEach(function(region) {
        regionOpts.appendChild(makeLi(region, function() {
          sportsActiveFilters.region       = region;
          sportsActiveFilters.neighborhood = null;
          setSportsFilterLabel('sports-region-button', region);
          setSportsFilterActive('sports-region-button', true);
          document.getElementById('sports-region-dropdown').style.display = 'none';
          buildSportsNeighborhoodList(nhHasMarker, region);
          applySportsFilters();
          zoomToFeatures(regionHasMarker[region]);
        }));
      });

      setupSportsDropdown('sports-region-button', 'sports-region-dropdown');

      // Neighborhood dropdown
      function buildSportsNeighborhoodList(nhMap, filterRegion) {
        var opts = document.getElementById('sports-neighborhood-options');
        opts.innerHTML = '';

        opts.appendChild(makeLi('All', function() {
          sportsActiveFilters.neighborhood = null;
          setSportsFilterLabel('sports-neighborhood-button', 'Neighborhood');
          setSportsFilterActive('sports-neighborhood-button', false);
          document.getElementById('sports-neighborhood-dropdown').style.display = 'none';
          applySportsFilters();
        }));

        var names = Object.keys(nhMap).sort();
        if (filterRegion) {
          names = names.filter(function(n) {
            return (nhMap[n].properties.GENERAL_AREA || '').trim() === filterRegion;
          });
        }

        names.forEach(function(name) {
          var feature = nhMap[name];
          opts.appendChild(makeLi(name, function() {
            sportsActiveFilters.neighborhood = name;
            setSportsFilterLabel('sports-neighborhood-button', name);
            setSportsFilterActive('sports-neighborhood-button', true);
            document.getElementById('sports-neighborhood-dropdown').style.display = 'none';
            applySportsFilters();
            zoomToFeatures([feature]);
          }));
        });
      }

      buildSportsNeighborhoodList(nhHasMarker, null);
      setupSportsDropdown('sports-neighborhood-button', 'sports-neighborhood-dropdown');

      // Populate mobile neighborhood select
      var mobileNhSelect = document.getElementById('mobile-sports-neighborhood-select');
      if (mobileNhSelect) {
        Object.keys(nhHasMarker).sort().forEach(function(name) {
          var opt = document.createElement('option');
          opt.value = name;
          opt.textContent = name;
          mobileNhSelect.appendChild(opt);
        });
      }
    })
    .catch(function(e) { console.warn('[sports-geojson]', e.message); });
}

// ─── Dropdown toggle wiring ───────────────────────────────────────────────────
function setupSportsDropdown(buttonId, dropdownId) {
  var btn = document.getElementById(buttonId);
  var dd  = document.getElementById(dropdownId);
  if (!btn || !dd) return;

  btn.addEventListener('click', function() {
    var visible = dd.style.display === 'block';
    document.querySelectorAll('#sports-filters [id$="-dropdown"]').forEach(function(el) {
      el.style.display = 'none';
    });
    dd.style.display = visible ? 'none' : 'block';
  });

  document.addEventListener('click', function(e) {
    if (!btn.contains(e.target) && !dd.contains(e.target)) dd.style.display = 'none';
  });
}

// ─── Main data load ───────────────────────────────────────────────────────────
async function loadSportsData() {
  // Step 1: load teams for logo/league lookups and dropdown population
  try {
    var teamsRes = await fetch(SPORTS_API_BASE + '/api/sports-teams');
    var teams    = await teamsRes.json();
    sportsAllTeams = teams;
    teams.forEach(function(t) {
      sportsTeamLogoMap[t.team_name]   = t.logo_url;
      sportsTeamLeagueMap[t.team_name] = t.league;
    });
    clearSportsTeamDropdown();
  } catch (e) {
    console.warn('[sports] Failed to load teams:', e.message);
    clearSportsTeamDropdown();
  }

  buildSportsLeagueDropdown();

  // Step 2: load sports bars and build markers
  try {
    var barsRes = await fetch(SPORTS_API_BASE + '/api/sports-bars');
    var bars    = await barsRes.json();
    sportsAllData = bars;

    bars.forEach(function(row, i) {
      var lat = parseFloat(row.Latitude);
      var lng = parseFloat(row.Longitude);
      if (isNaN(lat) || isNaN(lng)) return;

      var { allTeams, leagues } = getBarTeamSets(row);
      var hasPhillyAffil = (row.philly_affiliates || []).length > 0;

      // For Premier League teams: use team_color and logo_url
      var markerColor = '#f59e0b';
      var markerLogo = null;
      if (row.premier_league_team) {
        var plTeam = sportsAllTeams.find(function(t) { 
          return t.team_name === row.premier_league_team && t.league === 'Premier League'; 
        });
        if (plTeam) {
          markerColor = plTeam.team_color || '#f59e0b';
          markerLogo = plTeam.logo_url;
        }
      } else {
        // Pick marker color: Philly bars get Eagles-navy, others by primary league
        var primaryLeague = Array.from(leagues)[0] || null;
        markerColor = hasPhillyAffil ? '#002d62'
          : primaryLeague ? leagueColor(primaryLeague)
          : '#f59e0b';
      }

      var popupContent = buildSportsPopup(row);
      var marker = L.marker([lat, lng], { icon: createSportsIcon(markerColor, markerLogo) })
        .bindPopup(popupContent, { maxWidth: 260 });

      marker.name          = row.Name;
      marker.rowIndex      = i;
      marker.allTeams      = allTeams;
      marker.leagues       = leagues;
      marker.hasPhillyAffil = hasPhillyAffil;
      marker.neighborhood  = row.Neighborhood || null;

      sportsMarkers.push(marker);
      marker.addTo(sportsMap);
    });

    populateSportsSidebar(bars);
    addSportsMapSearchControl();
    loadSportsGeoJson();

    if (window._sportsDrawerSetData) window._sportsDrawerSetData(bars);

  } catch (e) {
    console.error('[sports] Failed to load bars:', e.message);
  }
}

loadSportsData();

// ─── Philly-only toggle ───────────────────────────────────────────────────────
var sportsPhillyBtn = document.getElementById('sports-philly-button');
if (sportsPhillyBtn) {
  sportsPhillyBtn.addEventListener('click', function() {
    sportsActiveFilters.phillyOnly = !sportsActiveFilters.phillyOnly;
    setSportsFilterActive('sports-philly-button', sportsActiveFilters.phillyOnly);
    applySportsFilters();
  });
}

// ─── Reset button ─────────────────────────────────────────────────────────────
var sportsResetBtn = document.getElementById('sports-reset-button');
if (sportsResetBtn) {
  sportsResetBtn.addEventListener('click', function() {
    sportsActiveFilters.league       = null;
    sportsActiveFilters.team         = null;
    sportsActiveFilters.phillyOnly   = false;
    sportsActiveFilters.neighborhood = null;
    sportsActiveFilters.region       = null;
    setSportsFilterLabel('sports-league-button',       'League');
    setSportsFilterActive('sports-league-button',       false);
    setSportsFilterLabel('sports-team-button',          'Team');
    setSportsFilterActive('sports-team-button',         false);
    setSportsFilterActive('sports-philly-button',       false);
    setSportsFilterLabel('sports-region-button',        'Philly Region');
    setSportsFilterActive('sports-region-button',       false);
    setSportsFilterLabel('sports-neighborhood-button',  'Neighborhood');
    setSportsFilterActive('sports-neighborhood-button', false);
    clearSportsTeamDropdown();
    sportsMap.setView([39.951, -75.163], 12);
    applySportsFilters();
  });
}

// ─── Dropdown wiring (static dropdowns) ──────────────────────────────────────
setupSportsDropdown('sports-league-button', 'sports-league-dropdown');
setupSportsDropdown('sports-team-button',   'sports-team-dropdown');

// ─── Sidebar card search ──────────────────────────────────────────────────────
var sportsBarSearchInput = document.getElementById('sports-bar-search');
if (sportsBarSearchInput) {
  sportsBarSearchInput.addEventListener('input', function(e) {
    var q = e.target.value.toLowerCase();
    document.querySelectorAll('#sports-bar-list .bar-card').forEach(function(card) {
      card.style.display = card.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
}

// ─── Mobile filter modal ──────────────────────────────────────────────────────
(function() {
  var openBtn  = document.getElementById('sports-mobile-filter-btn');
  var modal    = document.getElementById('sports-mobile-filter-modal');
  var closeBtn = document.getElementById('sports-filter-close');
  var resetBtn = document.getElementById('sports-mobile-filter-reset');
  var applyBtn = document.getElementById('sports-mobile-filter-apply');

  if (!modal) return;

  // Mobile filter state (separate from main filters — applied on "Apply")
  var mobileFilters = { league: null, phillyOnly: false, neighborhood: null };

  function openSportsMobileModal() { modal.classList.add('open'); }
  function closeSportsMobileModal() { modal.classList.remove('open'); }

  if (openBtn)  openBtn.addEventListener('click', openSportsMobileModal);
  if (closeBtn) closeBtn.addEventListener('click', closeSportsMobileModal);

  // League pill buttons in mobile modal
  document.querySelectorAll('#mobile-sports-league-buttons .mobile-filter-btn-option').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('#mobile-sports-league-buttons .mobile-filter-btn-option').forEach(function(b) {
        b.classList.remove('active');
      });
      this.classList.add('active');
      mobileFilters.league = this.dataset.value === 'All' ? null : this.dataset.value;
    });
  });

  // Apply
  if (applyBtn) {
    applyBtn.addEventListener('click', function() {
      sportsActiveFilters.league = mobileFilters.league;
      sportsActiveFilters.phillyOnly = mobileFilters.phillyOnly;
      var nhVal = document.getElementById('mobile-sports-neighborhood-select');
      sportsActiveFilters.neighborhood = nhVal ? (nhVal.value || null) : null;
      setSportsFilterLabel('sports-league-button', sportsActiveFilters.league || 'League');
      setSportsFilterActive('sports-league-button', !!sportsActiveFilters.league);
      setSportsFilterActive('sports-philly-button', sportsActiveFilters.phillyOnly);
      applySportsFilters();
      closeSportsMobileModal();
    });
  }

  // Reset
  if (resetBtn) {
    resetBtn.addEventListener('click', function() {
      mobileFilters = { league: null, phillyOnly: false, neighborhood: null };
      document.querySelectorAll('#mobile-sports-league-buttons .mobile-filter-btn-option').forEach(function(b) {
        b.classList.toggle('active', b.dataset.value === 'All');
      });
      var nhVal = document.getElementById('mobile-sports-neighborhood-select');
      if (nhVal) nhVal.value = '';
    });
  }
})();

// ─── Mobile bottom drawer ─────────────────────────────────────────────────────
(function() {
  var drawerData = [];

  function openSportsDrawer() {
    document.getElementById('sports-drawer').classList.add('open');
    document.getElementById('sports-drawer-backdrop').classList.add('open');
    renderSportsDrawerCards(drawerData);
  }
  function closeSportsDrawer() {
    document.getElementById('sports-drawer').classList.remove('open');
    document.getElementById('sports-drawer-backdrop').classList.remove('open');
  }

  function renderSportsDrawerCards(data) {
    var row = document.getElementById('sports-drawer-cards');
    var q   = (document.getElementById('sports-drawer-search').value || '').toLowerCase();
    row.innerHTML = '';

    var filtered = data.filter(function(bar) {
      if (!bar.Name) return false;
      return !q || JSON.stringify(bar).toLowerCase().includes(q);
    });

    if (!filtered.length) {
      row.innerHTML = '<p style="color:#64748b;padding:20px;font-size:0.85rem;">No bars match.</p>';
      return;
    }

    filtered.forEach(function(bar) {
      var card = document.createElement('div');
      card.className = 'drawer-card';

      var placeholder = document.createElement('div');
      placeholder.className = 'drawer-card-thumb-placeholder';
      placeholder.innerHTML = '<i class="fa-solid fa-tv"></i>';

      var phillyTeams = (bar.philly_affiliates || []).filter(Boolean);
      var body = document.createElement('div');
      body.className = 'drawer-card-body';
      body.innerHTML =
        '<div class="drawer-card-name">' + (bar.Name || '') + '</div>' +
        (bar.Neighborhood ? '<div class="drawer-card-meta">' + bar.Neighborhood + '</div>' : '') +
        (phillyTeams.length ? '<div class="drawer-card-tags"><span class="drawer-card-tag">🦅 ' + phillyTeams.slice(0, 2).join(', ') + '</span></div>' : '');

      card.appendChild(placeholder);
      card.appendChild(body);

      card.addEventListener('click', function() {
        var marker = sportsMarkers.find(function(m) { return m.name === bar.Name; });
        if (marker) {
          closeSportsDrawer();
          sportsMap.setView(marker.getLatLng(), 16);
          marker.openPopup();
        }
      });

      row.appendChild(card);
    });
  }

  window._sportsDrawerSetData = function(data) { drawerData = data; };

  setTimeout(function() {
    var listBtn  = document.getElementById('sports-list-btn');
    var closeBtn = document.getElementById('sports-drawer-close');
    var backdrop = document.getElementById('sports-drawer-backdrop');
    var search   = document.getElementById('sports-drawer-search');
    var drawer   = document.getElementById('sports-drawer');

    if (listBtn)  listBtn.addEventListener('click', openSportsDrawer);
    if (closeBtn) closeBtn.addEventListener('click', function(e) { e.preventDefault(); closeSportsDrawer(); });
    if (backdrop) backdrop.addEventListener('click', closeSportsDrawer);
    if (search)   search.addEventListener('input', function() { renderSportsDrawerCards(drawerData); });
    if (drawer)   document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeSportsDrawer(); });
  }, 500);
})();
