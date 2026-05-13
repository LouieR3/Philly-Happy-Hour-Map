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
  // Wire tab clicks via delegation (handles dynamically-added tabs too)
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
  if (isAdmin) buildEnterGamePanel();
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
  const rdEl   = document.getElementById('season-rundiff');
  const sign   = run_diff > 0 ? '+' : '';
  rdEl.textContent = run_diff !== 0 ? `Run Diff: ${sign}${run_diff}` : '';
  rdEl.className   = 'run-diff' + (run_diff > 0 ? ' positive' : run_diff < 0 ? ' negative' : '');
}

function renderSeasonTable(players) {
  const panel = document.getElementById('panel-season');
  if (!players || !players.length) {
    panel.innerHTML = `<div class="empty-state"><i class="fa-solid fa-baseball"></i><p>No games recorded yet.</p></div>`;
    return;
  }

  const sorted = sortPlayers([...players]);

  const headerCells = SEASON_COLS.map(col => {
    const cls = col.key === sortCol
      ? (sortDir === 'asc' ? 'sort-asc' : 'sort-desc')
      : '';
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

  // Remove stale game tabs/panels and admin tab
  document.querySelectorAll('.game-tab, .game-panel').forEach(el => el.remove());
  document.getElementById('tab-enter-game')?.remove();

  games.forEach(game => {
    const tab = document.createElement('div');
    tab.className = 'tab game-tab';
    tab.dataset.panel = `game-${game._id}`;
    tab.innerHTML = `Game ${game.game_number} <span class="result-${game.result}" style="font-size:0.75rem;margin-left:4px">${game.result}</span>`;
    tabBar.appendChild(tab);

    const panel = document.createElement('div');
    panel.id = `panel-game-${game._id}`;
    panel.className = 'panel game-panel';
    panel.innerHTML = buildGamePanelHTML(game);
    content.appendChild(panel);
  });

  if (isAdmin) {
    const tab = document.createElement('div');
    tab.id = 'tab-enter-game';
    tab.className = 'tab admin-tab';
    tab.dataset.panel = 'enter-game';
    tab.textContent = '+ Enter Game';
    tabBar.appendChild(tab);
  }
}

function buildGamePanelHTML(game) {
  const dateStr = game.date
    ? new Date(game.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '';
  const resultWord = { W: 'Win', L: 'Loss', T: 'Tie' }[game.result] || '';

  const deleteBtnClass = `delete-game-btn${isAdmin ? ' admin-visible' : ''}`;

  const headerCells = GAME_COLS.map(c => `<th>${c.label}</th>`).join('');
  const rows = (game.players || []).map(p => {
    const cells = GAME_COLS.map(col => {
      const val = p[col.key];
      const display = col.fmt ? col.fmt(val) : (val != null ? val : '—');
      return `<td>${display}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

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
      <button class="${deleteBtnClass}" onclick="deleteGame('${game._id}')">
        <i class="fa-solid fa-trash-can"></i> Delete
      </button>
    </div>
    <div class="stats-table-wrap">
      <table>
        <thead><tr>${headerCells}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ─── Delete game ──────────────────────────────────────────────────────────────

async function deleteGame(id) {
  if (!confirm('Delete this game? Season stats will be recalculated.')) return;
  try {
    const res = await fetch(`${API_BASE}/admin/softball/games/${id}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    if (!res.ok) throw new Error();
    await Promise.all([loadSeason(), loadGames()]);
    switchTab('season');
  } catch {
    alert('Failed to delete game.');
  }
}

// ─── Enter Game Form ──────────────────────────────────────────────────────────

function buildEnterGamePanel() {
  const panel = document.getElementById('panel-enter-game');
  panel.innerHTML = `
    <div class="form-card">
      <div class="section-label">Game Details</div>
      <div class="form-row">
        <div class="form-group">
          <label>Date</label>
          <input type="date" id="fg-date" />
        </div>
        <div class="form-group">
          <label>Opponent</label>
          <input type="text" id="fg-opponent" placeholder="Team name" />
        </div>
        <div class="form-group">
          <label>Our Score</label>
          <input type="number" id="fg-our-score" min="0" placeholder="0" />
        </div>
        <div class="form-group">
          <label>Opp. Score</label>
          <input type="number" id="fg-opp-score" min="0" placeholder="0" />
        </div>
        <div class="form-group">
          <label>Result</label>
          <select id="fg-result">
            <option value="W">Win</option>
            <option value="L">Loss</option>
            <option value="T">Tie</option>
          </select>
        </div>
      </div>

      <div class="section-label">Player Stats</div>
      <div class="player-table-wrap">
        <table class="player-table">
          <thead>
            <tr>
              <th style="min-width:140px">Player</th>
              <th>AB</th>
              <th>H</th>
              <th>2B</th>
              <th>3B</th>
              <th>HR</th>
              <th>RBI</th>
              <th>R</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="player-rows"></tbody>
        </table>
      </div>

      <button class="btn-add-player" onclick="addPlayerRow()">+ Add Player</button>
      <br />
      <button class="btn-submit" onclick="submitGame()">Save Game</button>
      <div class="form-status" id="form-status"></div>
    </div>`;

  document.getElementById('fg-date').valueAsDate = new Date();
  for (let i = 0; i < 3; i++) addPlayerRow();
}

function addPlayerRow() {
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input type="text"   placeholder="Name"  class="pr-name" /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-ab"  /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-h"   /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-2b"  /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-3b"  /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-hr"  /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-rbi" /></td>
    <td><input type="number" placeholder="0" min="0" class="pr-r"   /></td>
    <td><button class="remove-row-btn" onclick="this.closest('tr').remove()" title="Remove">×</button></td>`;
  document.getElementById('player-rows').appendChild(tr);
}

async function submitGame() {
  const statusEl = document.getElementById('form-status');
  statusEl.className = 'form-status';
  statusEl.textContent = '';

  const date       = document.getElementById('fg-date').value;
  const opponent   = document.getElementById('fg-opponent').value.trim();
  const our_score  = document.getElementById('fg-our-score').value;
  const opp_score  = document.getElementById('fg-opp-score').value;
  const result     = document.getElementById('fg-result').value;

  if (!opponent) {
    statusEl.className = 'form-status error';
    statusEl.textContent = 'Opponent name is required.';
    return;
  }

  const players = [];
  for (const row of document.querySelectorAll('#player-rows tr')) {
    const name = row.querySelector('.pr-name').value.trim();
    if (!name) continue;
    players.push({
      name,
      AB:    parseInt(row.querySelector('.pr-ab').value)  || 0,
      H:     parseInt(row.querySelector('.pr-h').value)   || 0,
      '2B':  parseInt(row.querySelector('.pr-2b').value)  || 0,
      '3B':  parseInt(row.querySelector('.pr-3b').value)  || 0,
      HR:    parseInt(row.querySelector('.pr-hr').value)  || 0,
      RBI:   parseInt(row.querySelector('.pr-rbi').value) || 0,
      R:     parseInt(row.querySelector('.pr-r').value)   || 0,
    });
  }

  if (!players.length) {
    statusEl.className = 'form-status error';
    statusEl.textContent = 'Add at least one player.';
    return;
  }

  const btn = document.querySelector('.btn-submit');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    const res = await fetch(`${API_BASE}/admin/softball/games`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ date, opponent, our_score, opponent_score: opp_score, result, players }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Save failed');

    await Promise.all([loadSeason(), loadGames()]);

    // Reset form (panel still intact — just clear rows)
    document.getElementById('player-rows').innerHTML = '';
    for (let i = 0; i < 3; i++) addPlayerRow();
    document.getElementById('fg-opponent').value  = '';
    document.getElementById('fg-our-score').value = '';
    document.getElementById('fg-opp-score').value = '';
    document.getElementById('fg-date').valueAsDate = new Date();

    // Restore active state on enter-game tab (buildGameTabs re-adds it without active class)
    switchTab('enter-game');

    document.getElementById('form-status').className  = 'form-status success';
    document.getElementById('form-status').textContent = `Game ${data.game_number} saved!`;
  } catch (err) {
    statusEl.className  = 'form-status error';
    statusEl.textContent = err.message || 'Failed to save game.';
  } finally {
    const b = document.querySelector('.btn-submit');
    if (b) { b.disabled = false; b.textContent = 'Save Game'; }
  }
}

// ─── Start ────────────────────────────────────────────────────────────────────
init();
