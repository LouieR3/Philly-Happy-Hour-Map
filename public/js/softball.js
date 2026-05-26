// API_BASE is defined inline in softball.html

let isAdmin  = false;
let sortCol  = 'WAR';
let sortDir  = 'desc';
let seasonData = null;
let gamesData  = [];

const SEASON_COLS = [
  { key: 'name', label: 'Player', numeric: false },
  { key: 'AB',   label: 'AB',  numeric: true },
  { key: 'H',    label: 'H',   numeric: true },
  { key: '2B',   label: '2B',  numeric: true },
  { key: '3B',   label: '3B',  numeric: true },
  { key: 'HR',   label: 'HR',  numeric: true },
  { key: 'RBI',  label: 'RBI', numeric: true },
  { key: 'R',    label: 'R',   numeric: true },
  { key: 'TB',   label: 'TB',  numeric: true },
  { key: 'AVG',  label: 'AVG', numeric: true, fmt: v => v.toFixed(3) },
  { key: 'SLG',  label: 'SLG', numeric: true, fmt: v => v.toFixed(3) },
  { key: 'OPS',  label: 'OPS', numeric: true, fmt: v => v.toFixed(3) },
  { key: 'RC',   label: 'RC',  numeric: true, fmt: v => v.toFixed(2) },
  { key: 'WAR',  label: 'WAR', numeric: true, fmt: v => v != null ? v.toFixed(2) : '—' },
];

const GAME_COLS = [
  { key: 'name', label: 'Player' },
  { key: 'AB',   label: 'AB'  },
  { key: 'H',    label: 'H'   },
  { key: '2B',   label: '2B'  },
  { key: '3B',   label: '3B'  },
  { key: 'HR',   label: 'HR'  },
  { key: 'RBI',  label: 'RBI' },
  { key: 'R',    label: 'R'   },
  { key: 'TB',   label: 'TB'  },
  { key: 'AVG',  label: 'AVG', fmt: v => (v != null ? (+v).toFixed(3) : '.000') },
  { key: 'SLG',  label: 'SLG', fmt: v => (v != null ? (+v).toFixed(3) : '.000') },
  { key: 'OPS',  label: 'OPS', fmt: v => (v != null ? (+v).toFixed(3) : '.000') },
];

// ─── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  document.getElementById('tab-bar').addEventListener('click', e => {
    const tab = e.target.closest('.tab[data-panel]');
    if (tab) switchTab(tab.dataset.panel);
  });

  await checkAuth();
  await Promise.all([loadSeason(), loadGames()]);
}

async function checkAuth() {
  try {
    const res = await fetch(`${API_BASE}/admin/check-auth`, { credentials: 'include' });
    isAdmin = res.ok;
  } catch {
    isAdmin = false;
  }
}

// ─── Tab switching ────────────────────────────────────────────────────────────

function switchTab(panelKey) {
  const targetId = `panel-${panelKey}`;
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('active', t.dataset.panel === panelKey)
  );
  document.querySelectorAll('.panel').forEach(p =>
    p.classList.toggle('active', p.id === targetId)
  );
}

// ─── Season ───────────────────────────────────────────────────────────────────

async function loadSeason() {
  try {
    const res = await fetch(`${API_BASE}/api/softball/season`);
    if (!res.ok) throw new Error();
    seasonData = await res.json();
    renderSeasonBanner(seasonData);
    renderSeasonTable(seasonData.players);
  } catch {
    document.getElementById('panel-season').innerHTML =
      `<div class="empty-state"><i class="fa-solid fa-circle-exclamation"></i><p>Could not load season data.</p></div>`;
  }
}

function renderSeasonBanner({ record, run_diff }) {
  document.getElementById('season-record').textContent = `${record.W}-${record.L}-${record.T}`;
  const rdEl = document.getElementById('season-rundiff');
  const sign = run_diff > 0 ? '+' : '';
  rdEl.textContent = run_diff !== 0 ? `Run Diff: ${sign}${run_diff}` : '';
  rdEl.className   = 'run-diff' + (run_diff > 0 ? ' positive' : run_diff < 0 ? ' negative' : '');
}

function renderSeasonTable(players) {
  const panel = document.getElementById('panel-season');
  if (!players || !players.length) {
    panel.innerHTML = `<div class="empty-state"><i class="fa-solid fa-baseball"></i><p>No games recorded yet. Enter stats on a game tab to get started.</p></div>`;
    return;
  }

  const sorted = sortPlayers([...players]);

  const headerCells = SEASON_COLS.map(col => {
    const cls = col.key === sortCol
      ? (sortDir === 'asc' ? 'sort-asc' : 'sort-desc') : '';
    return `<th class="${cls}" onclick="setSort('${col.key}')">${col.label}</th>`;
  }).join('');

  const rows = sorted.map(p => {
    const cells = SEASON_COLS.map(col => {
      const val = p[col.key];
      let display;
      if (col.key === 'WAR') {
        display = val != null ? val.toFixed(2) : '—';
      } else if (col.fmt) {
        display = col.fmt(val != null ? val : 0);
      } else {
        display = val != null ? val : '—';
      }
      let warClass = '';
      if (col.key === 'WAR') {
        if      (val == null) warClass = 'war-null';
        else if (val > 0)     warClass = 'war-positive';
        else if (val < 0)     warClass = 'war-negative';
        else                  warClass = 'war-zero';
      }
      return `<td class="${warClass}">${display}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  panel.innerHTML = `
    <div class="stats-table-wrap">
      <table>
        <thead><tr>${headerCells}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function sortPlayers(players) {
  return players.sort((a, b) => {
    let av = a[sortCol], bv = b[sortCol];
    if (sortCol === 'name') {
      av = av || ''; bv = bv || '';
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    av = av != null ? av : -Infinity;
    bv = bv != null ? bv : -Infinity;
    return sortDir === 'asc' ? av - bv : bv - av;
  });
}

function setSort(col) {
  if (sortCol === col) {
    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    sortCol = col;
    sortDir = col === 'name' ? 'asc' : 'desc';
  }
  if (seasonData) renderSeasonTable(seasonData.players);
}

// ─── Games ────────────────────────────────────────────────────────────────────

async function loadGames() {
  try {
    const res = await fetch(`${API_BASE}/api/softball/games`);
    if (!res.ok) throw new Error();
    gamesData = await res.json();
    buildGameTabs(gamesData);
  } catch (err) {
    console.error('Failed to load games:', err);
  }
}

function buildGameTabs(games) {
  const tabBar  = document.getElementById('tab-bar');
  const content = document.getElementById('content');

  document.querySelectorAll('.game-tab, .game-panel').forEach(el => el.remove());

  games.forEach(game => {
    const isResolved = game.result && (
      (game.players && game.players.length > 0) ||
      game.result === 'WF' || game.result === 'RO'
    );

    // Tab
    const tab = document.createElement('div');
    tab.className = 'tab game-tab';
    tab.dataset.panel = `game-${game._id}`;
    if (isResolved) {
      tab.innerHTML = `<span style="font-size:0.75rem;margin-right:3px;" class="result-${game.result}">${game.result}</span> Game ${game.game_number}`;
    } else {
      tab.textContent = `Game ${game.game_number}`;
    }
    tabBar.appendChild(tab);

    // Panel
    const panel = document.createElement('div');
    panel.id = `panel-game-${game._id}`;
    panel.className = 'panel game-panel';
    panel.innerHTML = isResolved ? buildBoxScoreHTML(game) : buildStatsFormHTML(game);
    content.appendChild(panel);
    if (!isResolved) initDragDrop(document.getElementById(`sg-rows-${game._id}`));
  });
}

// ─── Box score view ───────────────────────────────────────────────────────────

function buildBoxScoreHTML(game) {
  const dateStr = game.date
    ? new Date(game.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '';

  if (game.result === 'WF' || game.result === 'RO') {
    const isWF    = game.result === 'WF';
    const title   = isWF ? 'Win by Forfeit' : 'Rain Out';
    const note    = isWF ? 'Pennoni wins 7–0 by forfeit. No player stats recorded.' : 'Game not played due to weather. No stats recorded.';
    const icon    = isWF ? 'fa-trophy' : 'fa-cloud-rain';
    const clearBtn = isAdmin
      ? `<button class="btn-clear-stats" onclick="clearStats('${game._id}')"><i class="fa-solid fa-xmark"></i> Clear</button>`
      : '';
    return `
      <div class="game-header">
        <div>
          <div class="game-matchup" style="font-size:1.1rem;">
            <span class="result-${game.result}">${title}</span>
            <span style="font-size:0.9rem;color:var(--sb-muted);">&nbsp;vs ${game.opponent}</span>
          </div>
          <div class="game-meta">${dateStr}${dateStr ? ' · ' : ''}Game ${game.game_number}</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">${clearBtn}</div>
      </div>
      <div class="empty-state" style="padding:40px 20px;">
        <i class="fa-solid ${icon}"></i>
        <p>${note}</p>
      </div>`;
  }

  const resultWord = { W: 'Win', L: 'Loss', T: 'Tie' }[game.result] || '';

  const headerCells = GAME_COLS.map(c => `<th>${c.label}</th>`).join('');
  const rows = (game.players || []).map(p => {
    const cells = GAME_COLS.map(col => {
      const val = p[col.key];
      const display = col.fmt ? col.fmt(val) : (val != null ? val : '—');
      return `<td>${display}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  const editBtn  = `<button class="btn-edit-stats" onclick="showStatsForm('${game._id}')"><i class="fa-solid fa-pen-to-square"></i> Edit Stats</button>`;
  const clearBtn = isAdmin
    ? `<button class="btn-clear-stats" onclick="clearStats('${game._id}')"><i class="fa-solid fa-xmark"></i> Clear</button>`
    : '';

  return `
    <div class="game-header">
      <div>
        <div class="game-matchup">
          Pennoni
          <span class="score result-${game.result}">${game.our_score}</span>
          &ndash;
          <span class="score">${game.opponent_score}</span>
          ${game.opponent}
          <span class="result-${game.result}" style="font-size:0.9rem">&nbsp;(${resultWord})</span>
        </div>
        <div class="game-meta">${dateStr}${dateStr ? ' · ' : ''}Game ${game.game_number}</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        ${editBtn}${clearBtn}
      </div>
    </div>
    <div class="stats-table-wrap">
      <table>
        <thead><tr>${headerCells}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ─── Stats entry form ─────────────────────────────────────────────────────────

function buildStatsFormHTML(game) {
  const dateStr = game.date
    ? new Date(game.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '';
  const hasExisting = game.players && game.players.length > 0;
  const playerRows  = hasExisting
    ? game.players.map(p => playerInputRowHTML(p)).join('')
    : [0, 1, 2].map(() => playerInputRowHTML()).join('');
  const prevGame = gamesData.find(g => g.game_number === game.game_number - 1);
  const copyBtn = prevGame
    ? `<button class="btn-load-prev" onclick="loadPreviousRoster('${game._id}')"><i class="fa-solid fa-rotate-left"></i> Copy Last Roster</button>`
    : '';

  return `
    <div class="game-header">
      <div>
        <div class="game-matchup" style="font-size:1.1rem;">
          Game ${game.game_number} &mdash; ${game.opponent}
        </div>
        <div class="game-meta">${dateStr}</div>
      </div>
      <span class="status-upcoming">No Stats Yet</span>
    </div>
    <div class="form-card">
      <div class="section-label">Score &amp; Result</div>
      <div class="form-row">
        <div class="form-group">
          <label>Our Score</label>
          <input type="number" id="sg-our-${game._id}" min="0"
            value="${game.our_score != null ? game.our_score : ''}" placeholder="0" />
        </div>
        <div class="form-group">
          <label>Opp. Score</label>
          <input type="number" id="sg-opp-${game._id}" min="0"
            value="${game.opponent_score != null ? game.opponent_score : ''}" placeholder="0" />
        </div>
        <div class="form-group">
          <label>Result</label>
          <select id="sg-result-${game._id}" onchange="handleResultChange('${game._id}')">
            <option value="">—</option>
            <option value="W"  ${game.result === 'W'  ? 'selected' : ''}>Win</option>
            <option value="L"  ${game.result === 'L'  ? 'selected' : ''}>Loss</option>
            <option value="T"  ${game.result === 'T'  ? 'selected' : ''}>Tie</option>
            <option value="WF" ${game.result === 'WF' ? 'selected' : ''}>Win by Forfeit</option>
            <option value="RO" ${game.result === 'RO' ? 'selected' : ''}>Rain Out</option>
          </select>
        </div>
      </div>

      <div id="sg-special-note-${game._id}" class="special-result-note" style="display:none;"></div>

      <div id="sg-player-section-${game._id}">
        <div class="section-label">Player Stats</div>
        <div class="player-table-wrap">
          <table class="player-table">
            <thead>
              <tr>
                <th style="width:20px;"></th>
                <th style="min-width:140px">Player</th>
                <th>AB</th><th>H</th><th>2B</th><th>3B</th><th>HR</th><th>RBI</th><th>R</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="sg-rows-${game._id}">${playerRows}</tbody>
          </table>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;">
          <button class="btn-add-player" style="margin-bottom:0;" onclick="addGamePlayerRow('${game._id}')">+ Add Player</button>
          ${copyBtn}
        </div>
      </div>
      <button class="btn-submit" onclick="submitStats('${game._id}')">Save Stats</button>
      <div class="form-status" id="sg-status-${game._id}"></div>
    </div>`;
}

function playerInputRowHTML(p = {}) {
  const v = (val) => val != null && val !== '' ? val : '';
  return `<tr draggable="true">
    <td class="drag-handle"><i class="fa-solid fa-grip-vertical"></i></td>
    <td><input type="text"   placeholder="Name" class="pr-name" value="${(p.name || '').replace(/"/g, '&quot;')}" /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-ab"  value="${v(p.AB)}"    /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-h"   value="${v(p.H)}"     /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-2b"  value="${v(p['2B'])}" /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-3b"  value="${v(p['3B'])}" /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-hr"  value="${v(p.HR)}"    /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-rbi" value="${v(p.RBI)}"   /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-r"   value="${v(p.R)}"     /></td>
    <td><button class="remove-row-btn" onclick="this.closest('tr').remove()" title="Remove">×</button></td>
  </tr>`;
}

function addGamePlayerRow(gameId) {
  const tbody = document.getElementById(`sg-rows-${gameId}`);
  if (tbody) tbody.insertAdjacentHTML('beforeend', playerInputRowHTML());
}

function handleResultChange(gameId) {
  const result      = document.getElementById(`sg-result-${gameId}`)?.value;
  const playerSec   = document.getElementById(`sg-player-section-${gameId}`);
  const noteEl      = document.getElementById(`sg-special-note-${gameId}`);
  const ourInput    = document.getElementById(`sg-our-${gameId}`);
  const oppInput    = document.getElementById(`sg-opp-${gameId}`);

  if (result === 'WF') {
    if (ourInput) ourInput.value = 7;
    if (oppInput) oppInput.value = 0;
    if (playerSec) playerSec.style.display = 'none';
    if (noteEl) { noteEl.textContent = 'Win by Forfeit — score recorded as 7–0, no player stats.'; noteEl.style.display = 'block'; }
  } else if (result === 'RO') {
    if (ourInput) ourInput.value = '';
    if (oppInput) oppInput.value = '';
    if (playerSec) playerSec.style.display = 'none';
    if (noteEl) { noteEl.textContent = 'Rain Out — game not played, no stats recorded.'; noteEl.style.display = 'block'; }
  } else {
    if (playerSec) playerSec.style.display = '';
    if (noteEl) { noteEl.textContent = ''; noteEl.style.display = 'none'; }
  }
}

function initDragDrop(tbody) {
  if (!tbody) return;
  let dragRow = null;

  tbody.addEventListener('dragstart', e => {
    dragRow = e.target.closest('tr');
    if (!dragRow) return;
    e.dataTransfer.effectAllowed = 'move';
    setTimeout(() => { if (dragRow) dragRow.classList.add('dragging'); }, 0);
  });

  tbody.addEventListener('dragend', () => {
    if (dragRow) dragRow.classList.remove('dragging');
    tbody.querySelectorAll('tr').forEach(r => r.classList.remove('drag-over'));
    dragRow = null;
  });

  tbody.addEventListener('dragover', e => {
    e.preventDefault();
    const tr = e.target.closest('tr');
    if (!tr || tr === dragRow) return;
    tbody.querySelectorAll('tr').forEach(r => r.classList.remove('drag-over'));
    tr.classList.add('drag-over');
  });

  tbody.addEventListener('drop', e => {
    e.preventDefault();
    const targetTr = e.target.closest('tr');
    if (!targetTr || targetTr === dragRow || !dragRow) return;
    const rows = [...tbody.querySelectorAll('tr')];
    const fromIdx = rows.indexOf(dragRow);
    const toIdx   = rows.indexOf(targetTr);
    if (fromIdx < toIdx) {
      tbody.insertBefore(dragRow, targetTr.nextSibling);
    } else {
      tbody.insertBefore(dragRow, targetTr);
    }
    tbody.querySelectorAll('tr').forEach(r => r.classList.remove('drag-over'));
  });
}

function loadPreviousRoster(gameId) {
  const game = gamesData.find(g => g._id === gameId);
  if (!game) return;
  const prev = gamesData.find(g => g.game_number === game.game_number - 1);
  if (!prev?.players?.length) {
    alert('No roster found from the previous game.');
    return;
  }
  const tbody = document.getElementById(`sg-rows-${gameId}`);
  if (!tbody) return;
  tbody.innerHTML = prev.players.map(p => playerInputRowHTML({ name: p.name })).join('');
  initDragDrop(tbody);
}

function showStatsForm(gameId) {
  const game = gamesData.find(g => g._id === gameId);
  if (!game) return;
  const panel = document.getElementById(`panel-game-${gameId}`);
  if (panel) {
    panel.innerHTML = buildStatsFormHTML(game);
    initDragDrop(document.getElementById(`sg-rows-${gameId}`));
    if (game.result === 'WF' || game.result === 'RO') handleResultChange(gameId);
  }
}

async function submitStats(gameId) {
  const statusEl = document.getElementById(`sg-status-${gameId}`);
  if (statusEl) { statusEl.textContent = ''; statusEl.className = 'form-status'; }

  const our_score = document.getElementById(`sg-our-${gameId}`)?.value;
  const opp_score = document.getElementById(`sg-opp-${gameId}`)?.value;
  const result    = document.getElementById(`sg-result-${gameId}`)?.value;

  if (!result) {
    if (statusEl) { statusEl.className = 'form-status error'; statusEl.textContent = 'Select a result.'; }
    return;
  }

  const isSpecial = result === 'WF' || result === 'RO';
  const players = [];

  if (!isSpecial) {
    for (const row of document.querySelectorAll(`#sg-rows-${gameId} tr`)) {
      const name = row.querySelector('.pr-name')?.value.trim();
      if (!name) continue;
      players.push({
        name,
        AB:    parseInt(row.querySelector('.pr-ab')?.value)  || 0,
        H:     parseInt(row.querySelector('.pr-h')?.value)   || 0,
        '2B':  parseInt(row.querySelector('.pr-2b')?.value)  || 0,
        '3B':  parseInt(row.querySelector('.pr-3b')?.value)  || 0,
        HR:    parseInt(row.querySelector('.pr-hr')?.value)  || 0,
        RBI:   parseInt(row.querySelector('.pr-rbi')?.value) || 0,
        R:     parseInt(row.querySelector('.pr-r')?.value)   || 0,
      });
    }
    if (!players.length) {
      if (statusEl) { statusEl.className = 'form-status error'; statusEl.textContent = 'Add at least one player.'; }
      return;
    }
  }

  const btn = document.querySelector(`#panel-game-${gameId} .btn-submit`);
  if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

  try {
    const res = await fetch(`${API_BASE}/api/softball/games/${gameId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        our_score:      result === 'WF' ? 7 : (result === 'RO' ? null : our_score),
        opponent_score: result === 'WF' ? 0 : (result === 'RO' ? null : opp_score),
        result,
        players,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Save failed');

    // Update local cache and swap to box score view
    const idx = gamesData.findIndex(g => g._id === gameId);
    if (idx !== -1) gamesData[idx] = data;

    const panel = document.getElementById(`panel-game-${gameId}`);
    if (panel) panel.innerHTML = buildBoxScoreHTML(data);

    const tab = document.querySelector(`[data-panel="game-${gameId}"]`);
    if (tab) tab.innerHTML = `<span style="font-size:0.75rem;margin-right:3px;" class="result-${data.result}">${data.result}</span> Game ${data.game_number}`;

    await loadSeason();
  } catch (err) {
    if (statusEl) { statusEl.className = 'form-status error'; statusEl.textContent = err.message || 'Failed to save.'; }
    if (btn) { btn.disabled = false; btn.textContent = 'Save Stats'; }
  }
}

async function clearStats(gameId) {
  if (!confirm('Clear all stats for this game?')) return;
  try {
    const res = await fetch(`${API_BASE}/api/softball/games/${gameId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ our_score: null, opponent_score: null, result: null, players: [] }),
    });
    if (!res.ok) throw new Error();
    const data = await res.json();

    const idx = gamesData.findIndex(g => g._id === gameId);
    if (idx !== -1) gamesData[idx] = data;

    const panel = document.getElementById(`panel-game-${gameId}`);
    if (panel) {
      panel.innerHTML = buildStatsFormHTML(data);
      initDragDrop(document.getElementById(`sg-rows-${gameId}`));
    }

    const tab = document.querySelector(`[data-panel="game-${gameId}"]`);
    if (tab) tab.textContent = `Game ${data.game_number}`;

    await loadSeason();
  } catch {
    alert('Failed to clear stats.');
  }
}

// ─── Start ────────────────────────────────────────────────────────────────────
init();
