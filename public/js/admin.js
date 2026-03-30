// ── State ──────────────────────────────────────────────────────────────────
let adminToken = '';
let liveData   = [];

const WEEKDAYS = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY'];

const API_BASE = 'https://philly-happy-hour-map-production.up.railway.app';

function adminFetch(url, method = 'GET', body = null) {
    const opts = {
    method,
    headers: { 'x-admin-token': adminToken, 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    return fetch(API_BASE + url, opts);
}

// ── Auth ───────────────────────────────────────────────────────────────────
function login() {
    const pw = document.getElementById('admin-password').value.trim();
    if (!pw) return;
    adminToken = pw;
    // Test the token immediately
    fetch(`${API_BASE}/admin/pending`, { headers: { 'x-admin-token': adminToken } })
    .then(r => {
        if (r.status === 401) throw new Error('bad');
        return r.json();
    })
    .then(data => {
        document.getElementById('login-screen').style.display = 'none';
        document.getElementById('app').style.display = 'block';
        renderPending(data);
        loadLiveData();
    })
    .catch(() => {
        document.getElementById('login-error').style.display = 'block';
        adminToken = '';
    });
}

document.getElementById('admin-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') login();
});

function logout() {
    adminToken = '';
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('app').style.display = 'none';
    document.getElementById('admin-password').value = '';
}

// ── Tabs ───────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    });
});

// ── Render Pending ─────────────────────────────────────────────────────────
function renderPending({ submissions, edits }) {
    // Update badges
    document.getElementById('badge-submissions').textContent = submissions.length;
    document.getElementById('badge-edits').textContent       = edits.length;
    document.getElementById('header-count').textContent =
    `${submissions.length + edits.length} pending`;

    // New submissions
    const subList = document.getElementById('submissions-list');
    subList.innerHTML = '';
    if (submissions.length === 0) {
    subList.innerHTML = emptyState('check-circle', 'No pending submissions — all clear!');
    } else {
    submissions.forEach(s => subList.appendChild(buildSubmissionCard(s)));
    }

    // Edits
    const editList = document.getElementById('edits-list');
    editList.innerHTML = '';
    if (edits.length === 0) {
    editList.innerHTML = emptyState('check-circle', 'No pending edits — all clear!');
    } else {
    edits.forEach(e => editList.appendChild(buildEditCard(e)));
    }
}

function emptyState(icon, msg) {
    return `<div class="empty"><i class="fa fa-${icon}"></i><p>${msg}</p></div>`;
}

// ── Submission Card ────────────────────────────────────────────────────────
function buildSubmissionCard(s) {
    const card = document.createElement('div');
    card.className = 'card';
    card.id = 'card-' + s._id;

    const submitted = new Date(s.submittedAt).toLocaleString();

    card.innerHTML = `
    <div class="card-header">
        <div>
        <div class="card-title">${s.BUSINESS}</div>
        <div class="card-meta">Submitted ${submitted}</div>
        </div>
        <span class="pill pill-new">NEW BAR</span>
    </div>

    <div class="card-fields">
        ${field('Address', s.ADDRESS || '—')}
        ${field('Day', s.WEEKDAY || '—')}
        ${field('Time', s.TIME || '—')}
        ${field('Event Type', s.EVENT_TYPE || '—')}
        ${field('Host', s.HOST || '—')}
        ${field('Prize 1', s.PRIZE_1_TYPE ? `${s.PRIZE_1_TYPE} — ${s.PRIZE_1_AMOUNT || '?'}` : '—')}
        ${field('Prize 2', s.PRIZE_2_TYPE ? `${s.PRIZE_2_TYPE} — ${s.PRIZE_2_AMOUNT || '?'}` : '—')}
    </div>

    ${s.NOTES ? `<div class="notes-box"><i class="fa fa-comment"></i> ${s.NOTES}</div>` : ''}

    <!-- Admin can tweak fields before approving -->
    <details class="edit-section">
        <summary>Override fields before approving</summary>
        <div class="edit-grid">
        ${editInput('BUSINESS',       'Business Name',  s.BUSINESS,   s._id)}
        ${editInput('ADDRESS_STREET', 'Street',         '',           s._id)}
        ${editInput('ADDRESS_UNIT',   'Unit',           '',           s._id)}
        ${editInput('ADDRESS_CITY',   'City',           'PHILADELPHIA', s._id)}
        ${editInput('ADDRESS_STATE',  'State',          'PA',         s._id)}
        ${editInput('ADDRESS_ZIP',    'ZIP',            '',           s._id)}
        ${editSelect('WEEKDAY',       'Day', WEEKDAYS,   s.WEEKDAY,   s._id)}
        ${editInput('TIME',           'Time',           s.TIME,       s._id)}
        ${editInput('NEIGHBORHOOD',   'Neighborhood',   '',           s._id)}
        ${editInput('HOST',           'Host',           s.HOST,       s._id)}
        ${editInput('PRIZE_1_TYPE',   'Prize 1 Type',  s.PRIZE_1_TYPE, s._id)}
        ${editInput('PRIZE_1_AMOUNT', 'Prize 1 Amount',s.PRIZE_1_AMOUNT, s._id)}
        </div>
    </details>

    <div class="card-actions" style="margin-top:16px;">
        <button class="btn-reject"  onclick="reject('${s._id}')">
        <i class="fa fa-times"></i> Reject
        </button>
        <button class="btn-approve" onclick="approve('${s._id}')">
        <i class="fa fa-check"></i> Approve & Add
        </button>
    </div>
    `;
    return card;
}

// ── Edit Card ──────────────────────────────────────────────────────────────
function buildEditCard(e) {
    const card = document.createElement('div');
    card.className = 'card';
    card.id = 'card-edit-' + e._id;

    const submitted = new Date(e.submittedAt).toLocaleString();
    const changes   = e.changes || {};

    card.innerHTML = `
    <div class="card-header">
        <div>
        <div class="card-title">${e.originalBusiness}</div>
        <div class="card-meta">Edit submitted ${submitted}</div>
        </div>
        <span class="pill pill-edit">EDIT</span>
    </div>

    <div class="card-fields">
        ${Object.entries(changes).map(([k, v]) =>
        `<div class="field"><label>${k}</label><span class="changed">${v}</span></div>`
        ).join('')}
    </div>

    ${e.NOTES ? `<div class="notes-box"><i class="fa fa-comment"></i> ${e.NOTES}</div>` : ''}

    <div class="card-actions">
        <button class="btn-reject"  onclick="rejectEdit('${e._id}')">
        <i class="fa fa-times"></i> Reject
        </button>
        <button class="btn-approve" onclick="approveEdit('${e._id}')">
        <i class="fa fa-check"></i> Apply Edit
        </button>
    </div>
    `;
    return card;
}

// ── Field helpers ──────────────────────────────────────────────────────────
function field(label, value) {
    return `<div class="field"><label>${label}</label><span>${value}</span></div>`;
}

function editInput(name, label, value, id) {
    return `
    <div>
        <div class="field-label">${label}</div>
        <input type="text" id="override-${id}-${name}" value="${value || ''}" placeholder="${label}" />
    </div>`;
}

function editSelect(name, label, options, selected, id) {
    const opts = options.map(o =>
    `<option value="${o}" ${o === selected ? 'selected' : ''}>${o}</option>`
    ).join('');
    return `
    <div>
        <div class="field-label">${label}</div>
        <select id="override-${id}-${name}">${opts}</select>
    </div>`;
}

// ── Collect override values from editable fields ───────────────────────────
function collectOverrides(id) {
    const overrideFields = [
    'BUSINESS','ADDRESS_STREET','ADDRESS_UNIT','ADDRESS_CITY',
    'ADDRESS_STATE','ADDRESS_ZIP','WEEKDAY','TIME','NEIGHBORHOOD',
    'HOST','PRIZE_1_TYPE','PRIZE_1_AMOUNT'
    ];
    const overrides = {};
    overrideFields.forEach(f => {
    const el = document.getElementById(`override-${id}-${f}`);
    if (el && el.value.trim()) overrides[f] = el.value.trim();
    });
    return overrides;
}

// ── API calls ──────────────────────────────────────────────────────────────
async function approve(id) {
    const overrides = collectOverrides(id);
    try {
    const res  = await adminFetch(`/admin/approve/${id}`, 'POST', overrides);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    removeCard('card-' + id);
    toast('Bar approved and added to live data ✓', 'success');
    refreshBadge();
    loadLiveData();
    } catch (err) { toast(err.message, 'error'); }
}

async function reject(id) {
    if (!confirm('Reject this submission?')) return;
    try {
    const res = await adminFetch(`/admin/reject/${id}`, 'POST');
    if (!res.ok) throw new Error((await res.json()).error);
    removeCard('card-' + id);
    toast('Submission rejected.', 'success');
    refreshBadge();
    } catch (err) { toast(err.message, 'error'); }
}

async function approveEdit(id) {
    try {
    const res  = await adminFetch(`/admin/approve-edit/${id}`, 'POST');
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    removeCard('card-edit-' + id);
    toast('Edit applied ✓', 'success');
    refreshBadge();
    loadLiveData();
    } catch (err) { toast(err.message, 'error'); }
}

async function rejectEdit(id) {
    if (!confirm('Reject this edit?')) return;
    try {
    const res = await adminFetch(`/admin/reject-edit/${id}`, 'POST');
    if (!res.ok) throw new Error((await res.json()).error);
    removeCard('card-edit-' + id);
    toast('Edit rejected.', 'success');
    refreshBadge();
    } catch (err) { toast(err.message, 'error'); }
}

async function exportCsv() {
    try {
    const res = await adminFetch('/admin/export-csv', 'POST');
    if (!res.ok) throw new Error((await res.json()).error);
    toast('CSV exported successfully ✓', 'success');
    } catch (err) { toast(err.message, 'error'); }
}

function adminFetch(url, method = 'GET', body = null) {
    const opts = {
    method,
    headers: { 'x-admin-token': adminToken, 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    return fetch(API_BASE + url, opts);
}

function refreshBadge() {
    adminFetch('/admin/pending')
    .then(r => r.json())
    .then(data => {
        document.getElementById('badge-submissions').textContent = data.submissions.length;
        document.getElementById('badge-edits').textContent       = data.edits.length;
        document.getElementById('header-count').textContent =
        `${data.submissions.length + data.edits.length} pending`;
    });
}

// ── Live Data Table ────────────────────────────────────────────────────────
function loadLiveData() {
    fetch(`${API_BASE}/api/quizzo`)
    .then(r => r.json())
    .then(data => {
        liveData = data;
        renderLiveTable(data);
    });
}

function renderLiveTable(data) {
    const tbody = document.getElementById('live-tbody');
    tbody.innerHTML = '';
    data.forEach(bar => {
    const tr = document.createElement('tr');
    const addr = [bar.ADDRESS_STREET, bar.ADDRESS_CITY, bar.ADDRESS_STATE]
        .filter(Boolean).join(', ');
    tr.innerHTML = `
        <td><strong>${bar.BUSINESS}</strong></td>
        <td>${bar.NEIGHBORHOOD || '—'}</td>
        <td>${addr || '—'}</td>
        <td>${bar.WEEKDAY || '—'}</td>
        <td>${bar.TIME || '—'}</td>
        <td>${bar.HOST || '—'}</td>
        <td>${bar.PRIZE_1_TYPE || '—'}</td>
    `;
    tbody.appendChild(tr);
    });
}

function filterLive(q) {
    const filtered = liveData.filter(bar =>
    JSON.stringify(bar).toLowerCase().includes(q.toLowerCase())
    );
    renderLiveTable(filtered);
}

// ── Helpers ────────────────────────────────────────────────────────────────
function removeCard(id) {
    const el = document.getElementById(id);
    if (el) { el.style.opacity = '0'; el.style.transform = 'scale(0.97)';
    setTimeout(() => el.remove(), 250); }
}

let toastTimer;
function toast(msg, type = 'success') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className   = `show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.className = ''; }, 3500);
}
// ═══════════════════════════════════════════════════════════════════════════
// POOL BARS
// ═══════════════════════════════════════════════════════════════════════════

let poolData = [];   // full list from API
let poolFiltered = [];

const POOL_BOOL_FIELDS = [
  'Has_Bar','Has_Food','Has_Happy_Hour','Has_TV',
  'Outdoor_Seating','Has_League','Hosts_Tournaments','Verified',
];

const POOL_TEXT_FIELDS = [
  'Name','Yelp Alias','Address','Phone','Website',
  'Yelp Rating','Price','Number_of_Tables','Table_Brand',
  'Table_Size','Table_Type','Cost_Per_Game','Cost_Per_Hour',
  'Min_Spend','Payment_Model','Vibe','Noise_Level','Crowd_Type',
  'Best_Nights','Reservations','Reservation_Link',
  'Happy_Hour_Details','Has_Other_Games','Parking',
  'League_Details','Last_Verified','Notes',
];

// ── Load pool bars from API ────────────────────────────────────────────────
function loadPoolBars() {
  adminFetch('/admin/pool-bars')
    .then(r => r.json())
    .then(data => {
      poolData = data;
      poolFiltered = data;
      document.getElementById('badge-pool').textContent = data.length;
      renderPoolTable(data);
    })
    .catch(err => toast('Failed to load pool bars: ' + err.message, 'error'));
}

// ── Render table ──────────────────────────────────────────────────────────
function renderPoolTable(data) {
  const tbody = document.getElementById('pool-tbody');
  tbody.innerHTML = '';

  if (data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:40px;color:var(--muted);">No pool bars found</td></tr>`;
    return;
  }

  data.forEach(bar => {
    const tr = document.createElement('tr');
    const cost = bar.Payment_Model === 'per_hour'
      ? (bar.Cost_Per_Hour ? `$${bar.Cost_Per_Hour}/hr` : '—')
      : (bar.Cost_Per_Game ? `$${bar.Cost_Per_Game}/game` : '—');

    tr.innerHTML = `
      <td><strong>${bar.Name || '—'}</strong></td>
      <td style="font-size:0.82rem;color:var(--muted);">${bar.Address || '—'}</td>
      <td style="text-align:center;">${bar.Number_of_Tables ?? '—'}</td>
      <td>${bar.Payment_Model ? bar.Payment_Model.replace(/_/g,' ') : '—'}</td>
      <td>${cost}</td>
      <td>${bar.Vibe || '—'}</td>
      <td>${bar['Yelp Rating'] ?? '—'}</td>
      <td>
        <span class="verified-badge ${bar.Verified ? 'verified-yes' : 'verified-no'}">
          ${bar.Verified ? 'Yes' : 'No'}
        </span>
      </td>
      <td>
        <button class="btn-table-action btn-edit-pool" onclick="openPoolModal('${bar._id}')">
          <i class="fa fa-edit"></i> Edit
        </button>
        <button class="btn-table-action btn-delete-pool" onclick="deletePoolBar('${bar._id}', '${(bar.Name||'').replace(/'/g,"\\'")}')">
          <i class="fa fa-trash"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Filter ────────────────────────────────────────────────────────────────
function filterPool(q) {
  const verifiedFilter = document.getElementById('pool-verified-filter').value;
  let filtered = poolData;

  if (verifiedFilter !== 'all') {
    const want = verifiedFilter === 'true';
    filtered = filtered.filter(b => !!b.Verified === want);
  }

  if (q.trim()) {
    const lower = q.toLowerCase();
    filtered = filtered.filter(b =>
      JSON.stringify(b).toLowerCase().includes(lower)
    );
  }

  poolFiltered = filtered;
  renderPoolTable(filtered);
}

// ── Modal open ────────────────────────────────────────────────────────────
function openPoolModal(id = null) {
  const modal = document.getElementById('pool-modal-overlay');
  document.getElementById('modal-title').textContent = id ? 'Edit Pool Bar' : 'Add Pool Bar';
  document.getElementById('modal-pool-id').value = id || '';

  // Clear all fields first
  POOL_TEXT_FIELDS.forEach(f => {
    const el = document.getElementById('pool-' + f);
    if (el) el.value = '';
  });
  POOL_BOOL_FIELDS.forEach(f => {
    const el = document.getElementById('pool-' + f);
    if (el) el.checked = false;
  });

  // If editing, populate with existing data
  if (id) {
    const bar = poolData.find(b => b._id === id);
    if (bar) {
      POOL_TEXT_FIELDS.forEach(f => {
        const el = document.getElementById('pool-' + f);
        if (el && bar[f] != null) el.value = bar[f];
      });
      POOL_BOOL_FIELDS.forEach(f => {
        const el = document.getElementById('pool-' + f);
        if (el) el.checked = !!bar[f];
      });
    }
  }

  modal.classList.add('open');
}

function closePoolModal(e) {
  if (e && e.target !== document.getElementById('pool-modal-overlay')) return;
  document.getElementById('pool-modal-overlay').classList.remove('open');
}

// ── Save (create or update) ───────────────────────────────────────────────
async function savePoolBar() {
  const id = document.getElementById('modal-pool-id').value;

  const doc = {};
  POOL_TEXT_FIELDS.forEach(f => {
    const el = document.getElementById('pool-' + f);
    if (el && el.value.trim() !== '') {
      // Coerce numeric fields
      if (['Yelp Rating','Number_of_Tables','Cost_Per_Game','Cost_Per_Hour','Min_Spend'].includes(f)) {
        doc[f] = parseFloat(el.value) || null;
      } else {
        doc[f] = el.value.trim();
      }
    }
  });
  POOL_BOOL_FIELDS.forEach(f => {
    const el = document.getElementById('pool-' + f);
    if (el) doc[f] = el.checked;
  });

  if (!doc['Name']) {
    toast('Name is required', 'error');
    return;
  }

  try {
    const url    = id ? `/admin/pool-bars/${id}` : '/admin/pool-bars';
    const method = id ? 'PUT' : 'POST';
    const res    = await adminFetch(url, method, doc);
    const data   = await res.json();
    if (!res.ok) throw new Error(data.error);

    document.getElementById('pool-modal-overlay').classList.remove('open');
    toast(id ? 'Pool bar updated ✓' : 'Pool bar added ✓', 'success');
    loadPoolBars();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ── Delete ────────────────────────────────────────────────────────────────
async function deletePoolBar(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  try {
    const res = await adminFetch(`/admin/pool-bars/${id}`, 'DELETE');
    if (!res.ok) throw new Error((await res.json()).error);
    toast(`"${name}" deleted.`, 'success');
    loadPoolBars();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ── Hook into tab click to load data ─────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    if (tab.dataset.tab === 'pool' && poolData.length === 0) {
      loadPoolBars();
    }
  });
});