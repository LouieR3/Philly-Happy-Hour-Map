// ── State ──────────────────────────────────────────────────────────────────
let liveData = [];

const WEEKDAYS = [
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
  "SUNDAY",
];
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:3000'
  : 'https://philly-happy-hour-map-production.up.railway.app';

// Check authentication on page load
document.addEventListener("DOMContentLoaded", async () => {
  try {
    // 1. Check if the user is already fully logged in
    const authRes = await fetch(API_BASE + '/admin/check-auth', {
      credentials: 'include'
    });
    const authData = await authRes.json();
    
    if (authData.authenticated) {
      // User is fully authenticated, proceed to load admin dashboard
      document.body.classList.add('auth-complete');
      initializeAdmin();
      return;
    }
    
    // 2. If not authenticated, send them to the unified login page
    // This page now handles both the Captcha and the Password stages.
    // console.log('Not authenticated, redirecting to admin-login');
    window.location.href = "admin-login.html";

  } catch (err) {
    // console.error('Auth check failed:', err);
    // On error, safe bet is to send back to the login/captcha entry point
    window.location.href = "admin-login.html";
  }
});

function adminFetch(url, method = "GET", body = null) {
  const opts = {
    method,
    credentials: 'include',  // Include cookies automatically
    headers: {
      "Content-Type": "application/json",
    },
  };
  if (body) opts.body = JSON.stringify(body);
  return fetch(API_BASE + url, opts);
}

// ── Initialize Admin (called after auth check) ─────────────────────────────
function initializeAdmin() {
  console.log("Initializing admin dashboard...");
  
  // Load initial data
  Promise.all([
    adminFetch("/admin/pending").then(r => r.json()),
    adminFetch("/admin/pending-pool-bars").then(r => r.json()),
  ])
    .then(([quizzoData, poolData]) => {
      console.log("Data loaded successfully");
      renderPending(quizzoData, poolData);
    })
    .catch(err => {
      console.error("Failed to load admin data:", err);
      toast("Failed to load admin data: " + err.message, "error");
    });

  // Setup tab switching
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      document
        .querySelectorAll(".panel")
        .forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById("panel-" + tab.dataset.tab).classList.add("active");

      // Load data for specific tabs
      if (tab.dataset.tab === "quizzo") loadQuizzoBars();
      if (tab.dataset.tab === "pool") loadPoolBars();
      if (tab.dataset.tab === "sports") {
        loadSportsTeams();
        loadSportsBars();
      }
      if (tab.dataset.tab === "allbars") loadAllBars();
      if (tab.dataset.tab === "photos") loadBarPhotos();
      if (tab.dataset.tab === "unmatched") loadUnmatched();
    });
  });

  // Setup Yelp search Enter key
  const yelpInput = document.getElementById("yelp-search-input");
  if (yelpInput) {
    yelpInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") yelpSearch();
    });
  }

  // Setup pool bar search
  setupPoolSearch();
}

// ── Auth ───────────────────────────────────────────────────────────────────
function handleLogout() {
  fetch(API_BASE + '/admin/logout', {
    method: 'POST',
    credentials: 'include'
  }).then(() => {
    window.location.href = "admin-login.html";
  }).catch(err => {
    console.error('Logout error:', err);
    window.location.href = "admin-login.html";
  });
}

// ── Render Pending ─────────────────────────────────────────────────────────
function renderPending({ submissions, edits }, poolPending = { submissions: [], edits: [] }) {
  const allSubs  = submissions.length + poolPending.submissions.length;
  const allEdits = edits.length + poolPending.edits.length;

  document.getElementById("badge-submissions").textContent = allSubs;
  document.getElementById("badge-edits").textContent = allEdits;
  document.getElementById("header-count").textContent =
    `${allSubs + allEdits} pending`;

  // New submissions — quizzo first, then pool
  const subList = document.getElementById("submissions-list");
  subList.innerHTML = "";
  if (allSubs === 0) {
    subList.innerHTML = emptyState("check-circle", "No pending submissions — all clear!");
  } else {
    submissions.forEach((s) => subList.appendChild(buildSubmissionCard(s, "quizzo")));
    poolPending.submissions.forEach((s) => subList.appendChild(buildSubmissionCard(s, "pool")));
  }

  // Edits — quizzo first, then pool
  const editList = document.getElementById("edits-list");
  editList.innerHTML = "";
  if (allEdits === 0) {
    editList.innerHTML = emptyState("check-circle", "No pending edits — all clear!");
  } else {
    edits.forEach((e) => editList.appendChild(buildEditCard(e, "quizzo")));
    poolPending.edits.forEach((e) => editList.appendChild(buildEditCard(e, "pool")));
  }
}

function emptyState(icon, msg) {
  return `<div class="empty"><i class="fa fa-${icon}"></i><p>${msg}</p></div>`;
}

// ── Submission Card ────────────────────────────────────────────────────────
function buildSubmissionCard(s, type = "quizzo") {
  const isPool = type === "pool";
  const card = document.createElement("div");
  card.className = `card card-${type}`;
  card.id = "card-" + s._id;

  const submitted = new Date(s.submittedAt).toLocaleString();
  const pillClass = isPool ? "pill-pool" : "pill-new";
  const pillLabel = isPool ? "NEW POOL BAR" : "NEW QUIZZO BAR";
  const name      = isPool ? (s.name || s.BUSINESS || "—") : (s.BUSINESS || "—");

  const overrideFields = isPool ? `
        ${editInput("name",          "Name",          s.name,         s._id)}
        ${editInput("streetAddress", "Street",        s.streetAddress,s._id)}
        ${editInput("city",          "City",          s.city,         s._id)}
        ${editInput("state",         "State",         s.state,        s._id)}
        ${editInput("neighborhood",  "Neighborhood",  s.neighborhood, s._id)}
        ${editInput("numTables",     "# Tables",      s.numTables,    s._id)}
        ${editInput("paymentModel",  "Payment Model", s.paymentModel, s._id)}
        ${editInput("costPerGame",   "Cost/Game ($)", s.costPerGame,  s._id)}
        ${editInput("costPerHour",   "Cost/Hour ($)", s.costPerHour,  s._id)}
  ` : `
        ${editInput("BUSINESS",      "Business Name", s.BUSINESS,     s._id)}
        ${editInput("ADDRESS_STREET","Street",        "",             s._id)}
        ${editInput("ADDRESS_UNIT",  "Unit",          "",             s._id)}
        ${editInput("ADDRESS_CITY",  "City",          "PHILADELPHIA", s._id)}
        ${editInput("ADDRESS_STATE", "State",         "PA",           s._id)}
        ${editInput("ADDRESS_ZIP",   "ZIP",           "",             s._id)}
        ${editSelect("WEEKDAY",      "Day", WEEKDAYS,  s.WEEKDAY,     s._id)}
        ${editInput("TIME",          "Time",          s.TIME,         s._id)}
        ${editInput("NEIGHBORHOOD",  "Neighborhood",  "",             s._id)}
        ${editInput("HOST",          "Host",          s.HOST,         s._id)}
        ${editInput("PRIZE_1_TYPE",  "Prize 1 Type",  s.PRIZE_1_TYPE, s._id)}
        ${editInput("PRIZE_1_AMOUNT","Prize 1 Amount",s.PRIZE_1_AMOUNT,s._id)}
  `;

  const infoFields = isPool ? `
        ${field("Address",       (s.streetAddress ? s.streetAddress + ", " : "") + (s.city || "") + (s.state ? ", " + s.state : ""))}
        ${field("Neighborhood",  s.neighborhood || "—")}
        ${field("# Tables",      s.numTables    || "—")}
        ${field("Payment Model", s.paymentModel || "—")}
        ${field("Cost/Game",     s.costPerGame  ? "$" + s.costPerGame  : "—")}
        ${field("Cost/Hour",     s.costPerHour  ? "$" + s.costPerHour  : "—")}
  ` : `
        ${field("Address",   s.ADDRESS     || "—")}
        ${field("Day",       s.WEEKDAY     || "—")}
        ${field("Time",      s.TIME        || "—")}
        ${field("Event Type",s.EVENT_TYPE  || "—")}
        ${field("Host",      s.HOST        || "—")}
        ${field("Prize 1",   s.PRIZE_1_TYPE ? `${s.PRIZE_1_TYPE} — ${s.PRIZE_1_AMOUNT || "?"}` : "—")}
        ${field("Prize 2",   s.PRIZE_2_TYPE ? `${s.PRIZE_2_TYPE} — ${s.PRIZE_2_AMOUNT || "?"}` : "—")}
  `;

  const approveHandler = isPool
    ? `approvePoolSubmission('${s._id}')`
    : `approve('${s._id}')`;
  const rejectHandler = isPool
    ? `rejectPoolSubmission('${s._id}')`
    : `reject('${s._id}')`;

  card.innerHTML = `
    <div class="card-header">
        <div>
        <div class="card-title">${name}</div>
        <div class="card-meta">Submitted ${submitted}</div>
        </div>
        <span class="pill ${pillClass}">${pillLabel}</span>
    </div>

    <div class="card-fields">${infoFields}</div>

    ${s.notes || s.NOTES ? `<div class="notes-box"><i class="fa fa-comment"></i> ${s.notes || s.NOTES}</div>` : ""}

    <details class="edit-section">
        <summary>Override fields before approving</summary>
        <div class="edit-grid">${overrideFields}</div>
    </details>

    <div class="card-actions" style="margin-top:16px;">
        <button class="btn-reject" onclick="${rejectHandler}">
          <i class="fa fa-times"></i> Reject
        </button>
        <button class="btn-approve" onclick="${approveHandler}">
          <i class="fa fa-check"></i> Approve & Add
        </button>
    </div>
    `;
  return card;
}

// ── Edit Card ──────────────────────────────────────────────────────────────
function buildEditCard(e, type = "quizzo") {
  const isPool = type === "pool";
  const card = document.createElement("div");
  card.className = `card card-${type} card-edit-type`;
  card.id = "card-edit-" + e._id;

  const submitted = new Date(e.submittedAt).toLocaleString();
  const changes   = e.changes || {};
  const pillLabel = isPool ? "POOL EDIT" : "QUIZZO EDIT";
  const pillClass = isPool ? "pill-pool-edit" : "pill-edit";

  const approveHandler = isPool ? `approvePoolEdit('${e._id}')` : `approveEdit('${e._id}')`;
  const rejectHandler  = isPool ? `rejectPoolEdit('${e._id}')`  : `rejectEdit('${e._id}')`;

  card.innerHTML = `
    <div class="card-header">
        <div>
        <div class="card-title">${e.originalBusiness || e.originalName || "—"}</div>
        <div class="card-meta">Edit submitted ${submitted}</div>
        </div>
        <span class="pill ${pillClass}">${pillLabel}</span>
    </div>

    <div class="card-fields">
        ${Object.entries(changes)
          .map(([k, v]) => `<div class="field"><label>${k}</label><span class="changed">${v}</span></div>`)
          .join("")}
    </div>

    ${e.notes || e.NOTES ? `<div class="notes-box"><i class="fa fa-comment"></i> ${e.notes || e.NOTES}</div>` : ""}

    <div class="card-actions">
        <button class="btn-reject"  onclick="${rejectHandler}">
          <i class="fa fa-times"></i> Reject
        </button>
        <button class="btn-approve" onclick="${approveHandler}">
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
        <input type="text" id="override-${id}-${name}" value="${value || ""}" placeholder="${label}" />
    </div>`;
}

function editSelect(name, label, options, selected, id) {
  const opts = options
    .map(
      (o) =>
        `<option value="${o}" ${o === selected ? "selected" : ""}>${o}</option>`,
    )
    .join("");
  return `
    <div>
        <div class="field-label">${label}</div>
        <select id="override-${id}-${name}">${opts}</select>
    </div>`;
}

// ── Collect override values from editable fields ───────────────────────────
function collectOverrides(id) {
  const overrideFields = [
    "BUSINESS",
    "ADDRESS_STREET",
    "ADDRESS_UNIT",
    "ADDRESS_CITY",
    "ADDRESS_STATE",
    "ADDRESS_ZIP",
    "WEEKDAY",
    "TIME",
    "NEIGHBORHOOD",
    "HOST",
    "PRIZE_1_TYPE",
    "PRIZE_1_AMOUNT",
  ];
  const overrides = {};
  overrideFields.forEach((f) => {
    const el = document.getElementById(`override-${id}-${f}`);
    if (el && el.value.trim()) overrides[f] = el.value.trim();
  });
  return overrides;
}

// ── API calls ──────────────────────────────────────────────────────────────
async function approve(id) {
  const overrides = collectOverrides(id);
  try {
    const res = await adminFetch(`/admin/approve/${id}`, "POST", overrides);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    removeCard("card-" + id);
    toast("Bar approved and added to live data ✓", "success");
    refreshBadge();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function reject(id) {
  if (!confirm("Reject this submission?")) return;
  try {
    const res = await adminFetch(`/admin/reject/${id}`, "POST");
    if (!res.ok) throw new Error((await res.json()).error);
    removeCard("card-" + id);
    toast("Submission rejected.", "success");
    refreshBadge();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function approveEdit(id) {
  try {
    const res = await adminFetch(`/admin/approve-edit/${id}`, "POST");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    removeCard("card-edit-" + id);
    toast("Edit applied ✓", "success");
    refreshBadge();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function rejectEdit(id) {
  if (!confirm("Reject this edit?")) return;
  try {
    const res = await adminFetch(`/admin/reject-edit/${id}`, "POST");
    if (!res.ok) throw new Error((await res.json()).error);
    removeCard("card-edit-" + id);
    toast("Edit rejected.", "success");
    refreshBadge();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function exportCsv() {
  try {
    const res = await adminFetch("/admin/export-csv", "POST");
    if (!res.ok) throw new Error((await res.json()).error);
    toast("CSV exported successfully ✓", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

// ─────────────────────────────────────────────────────────────────────────

function refreshBadge() {
  Promise.all([
    adminFetch("/admin/pending").then(r => r.json()),
    adminFetch("/admin/pending-pool-bars").then(r => r.json()),
  ]).then(([quizzo, poolPending]) => {
    const allSubs  = quizzo.submissions.length + poolPending.submissions.length;
    const allEdits = quizzo.edits.length + poolPending.edits.length;
    document.getElementById("badge-submissions").textContent = allSubs;
    document.getElementById("badge-edits").textContent = allEdits;
    document.getElementById("header-count").textContent = `${allSubs + allEdits} pending`;
  });
}



// ── Helpers ────────────────────────────────────────────────────────────────
function removeCard(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.opacity = "0";
    el.style.transform = "scale(0.97)";
    setTimeout(() => el.remove(), 250);
  }
}

let toastTimer;
function toast(msg, type = "success") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.className = "";
  }, 3500);
}

// ── Pool submission approval/rejection ────────────────────────────────────
async function approvePoolSubmission(id) {
  const card = document.getElementById("card-" + id);
  // Collect overrides from the edit grid
  const overrideFields = ["name","streetAddress","city","state","neighborhood",
    "numTables","paymentModel","costPerGame","costPerHour"];
  const overrides = {};
  overrideFields.forEach(f => {
    const el = document.getElementById(`override-${id}-${f}`);
    if (el && el.value.trim()) overrides[f] = el.value.trim();
  });
  try {
    const res  = await adminFetch(`/admin/approve-pool-submission/${id}`, "POST", overrides);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    removeCard("card-" + id);
    toast("Pool bar approved and added ✓", "success");
    refreshBadge();
    loadPoolBars();
  } catch (err) { toast(err.message, "error"); }
}

async function rejectPoolSubmission(id) {
  if (!confirm("Reject this pool bar submission?")) return;
  try {
    const res = await adminFetch(`/admin/reject-pool-submission/${id}`, "POST");
    if (!res.ok) throw new Error((await res.json()).error);
    removeCard("card-" + id);
    toast("Pool submission rejected.", "success");
    refreshBadge();
  } catch (err) { toast(err.message, "error"); }
}

async function approvePoolEdit(id) {
  try {
    const res  = await adminFetch(`/admin/approve-pool-edit/${id}`, "POST");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    removeCard("card-edit-" + id);
    toast("Pool bar edit applied ✓", "success");
    refreshBadge();
    loadPoolBars();
  } catch (err) { toast(err.message, "error"); }
}

async function rejectPoolEdit(id) {
  if (!confirm("Reject this pool bar edit?")) return;
  try {
    const res = await adminFetch(`/admin/reject-pool-edit/${id}`, "POST");
    if (!res.ok) throw new Error((await res.json()).error);
    removeCard("card-edit-" + id);
    toast("Pool edit rejected.", "success");
    refreshBadge();
  } catch (err) { toast(err.message, "error"); }
}

// ═══════════════════════════════════════════════════════════════════════════
// POOL BARS
// ═══════════════════════════════════════════════════════════════════════════

let poolData = []; // full list from API
let poolFiltered = [];

const POOL_BOOL_FIELDS = [
  "Has_Bar",
  "Has_Food",
  "Has_Happy_Hour",
  "Has_TV",
  "Outdoor_Seating",
  "Has_League",
  "Hosts_Tournaments",
  "Verified",
];

const POOL_TEXT_FIELDS = [
  "Name",
  "Yelp Alias",
  "Address",
  "Phone",
  "Website",
  "Yelp Rating",
  "Price",
  "Latitude",
  "Longitude",
  "Number_of_Tables",
  "Table_Brand",
  "Table_Size",
  "Table_Type",
  "Cost_Per_Game",
  "Cost_Per_Hour",
  "Min_Spend",
  "Payment_Model",
  "Vibe",
  "Noise_Level",
  "Crowd_Type",
  "Best_Nights",
  "Reservations",
  "Reservation_Link",
  "Happy_Hour_Details",
  "Has_Other_Games",
  "Parking",
  "League_Details",
  "Last_Verified",
  "Notes",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

// ── Load pool bars from API ────────────────────────────────────────────────
function loadPoolBars() {
  adminFetch("/admin/pool-bars")
    .then((r) => r.json())
    .then((data) => {
      poolData = data;
      poolFiltered = data;
      const badge = document.getElementById("badge-pool");
      if (badge) badge.textContent = data.length;
      renderPoolTable(data);
    })
    .catch((err) => toast("Failed to load pool bars: " + err.message, "error"));
}

// ── Render table ──────────────────────────────────────────────────────────
function renderPoolTable(data) {
  const tbody = document.getElementById("pool-tbody");
  tbody.innerHTML = "";
  if (!Array.isArray(data)) {
    console.error("Expected array but got:", data);
    return;
  }
  if (data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:40px;color:var(--muted);">No pool bars found</td></tr>`;
    return;
  }

  data.forEach((bar) => {
    const tr = document.createElement("tr");
    const cost =
      bar.Payment_Model === "per_hour"
        ? bar.Cost_Per_Hour
          ? `$${bar.Cost_Per_Hour}/hr`
          : "—"
        : bar.Cost_Per_Game
          ? `$${bar.Cost_Per_Game}/game`
          : "—";

    tr.innerHTML = `
      <td><strong>${bar.Name || "—"}</strong></td>
      <td style="font-size:0.82rem;color:var(--muted);">${bar.Address || "—"}</td>
      <td style="text-align:center;">${bar.Number_of_Tables ?? "—"}</td>
      <td>${bar.Payment_Model ? bar.Payment_Model.replace(/_/g, " ") : "—"}</td>
      <td>${cost}</td>
      <td>${bar.Vibe || "—"}</td>
      <td>${bar["Yelp Rating"] ?? "—"}</td>
      <td>
        <span class="verified-badge ${bar.Verified ? "verified-yes" : "verified-no"}">
          ${bar.Verified ? "Yes" : "No"}
        </span>
      </td>
      <td>
        <button class="btn-table-action btn-edit-pool" onclick="openPoolModal('${bar._id}')">
          <i class="fa fa-edit"></i> Edit
        </button>
        <button class="btn-table-action btn-delete-pool" onclick="deletePoolBar('${bar._id}', '${(bar.Name || "").replace(/'/g, "\\'")}')">
          <i class="fa fa-trash"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Filter ────────────────────────────────────────────────────────────────
function filterPool(q) {
  const verifiedFilter = document.getElementById("pool-verified-filter").value;
  let filtered = poolData;

  if (verifiedFilter !== "all") {
    const want = verifiedFilter === "true";
    filtered = filtered.filter((b) => !!b.Verified === want);
  }

  if (q.trim()) {
    const lower = q.toLowerCase();
    filtered = filtered.filter((b) =>
      JSON.stringify(b).toLowerCase().includes(lower),
    );
  }

  poolFiltered = filtered;
  renderPoolTable(filtered);
}

// ── Modal open ────────────────────────────────────────────────────────────
function openPoolModal(id = null) {
  const modal = document.getElementById("pool-modal-overlay");
  document.getElementById("modal-title").textContent = id
    ? "Edit Pool Bar"
    : "Add Pool Bar";
  document.getElementById("modal-pool-id").value = id || "";

  // Clear all fields first
  POOL_TEXT_FIELDS.forEach((f) => {
    let formId = f;
    // Handle special field ID mappings
    if (f === "Yelp Alias") formId = "yelp-alias";
    if (f === "Yelp Rating") formId = "yelp-rating";
    const el = document.getElementById("pool-" + formId);
    if (el) el.value = "";
  });
  POOL_BOOL_FIELDS.forEach((f) => {
    const el = document.getElementById("pool-" + f);
    if (el) el.checked = false;
  });

  // If editing, populate with existing data
  if (id) {
    const bar = poolData.find((b) => b._id === id);
    if (bar) {
      POOL_TEXT_FIELDS.forEach((f) => {
        let formId = f;
        // Handle special field ID mappings (form IDs that don't match POOL_TEXT_FIELDS names)
        if (f === "Yelp Alias") formId = "yelp-alias";
        if (f === "Yelp Rating") formId = "yelp-rating";
        const el = document.getElementById("pool-" + formId);
        if (el && bar[f] != null) el.value = bar[f];
      });
      POOL_BOOL_FIELDS.forEach((f) => {
        const el = document.getElementById("pool-" + f);
        if (el) el.checked = !!bar[f];
      });
    }
  }

  modal.classList.add("open");
}

function closePoolModal(e) {
  if (e && e.target !== document.getElementById("pool-modal-overlay")) return;
  document.getElementById("pool-modal-overlay").classList.remove("open");
}

// ── Pool bar search (prepopulate from bars collection) ────────────────────
function setupPoolSearch() {
  const searchInput = document.getElementById("pool-search-input");
  const searchResults = document.getElementById("pool-search-results");
  const searchResultsList = document.getElementById("pool-search-results-list");

  if (!searchInput) return; // Only setup if element exists

  searchInput.addEventListener("input", async (e) => {
    const q = e.target.value.trim();
    if (!q || q.length < 2) {
      searchResults.style.display = "none";
      return;
    }

    try {
      const res = await adminFetch(`/api/search-bars?q=${encodeURIComponent(q)}`);
      const bars = await res.json();

      searchResultsList.innerHTML = "";
      if (!bars.length) {
        const li = document.createElement("li");
        li.textContent = "No bars found";
        li.style.color = "var(--muted)";
        li.style.padding = "8px";
        searchResultsList.appendChild(li);
      } else {
        bars.forEach((bar) => {
          const li = document.createElement("li");
          li.style.padding = "8px";
          li.style.cursor = "pointer";
          li.style.borderRadius = "4px";
          li.style.marginBottom = "4px";
          li.style.background = "var(--hover)";
          li.textContent = bar.Name + (bar["Yelp Alias"] ? ` (${bar["Yelp Alias"]})` : "");
          li.addEventListener("mouseover", () => (li.style.opacity = "0.7"));
          li.addEventListener("mouseout", () => (li.style.opacity = "1"));
          li.addEventListener("click", () => {
            // Populate fields from selected bar
            document.getElementById("pool-Name").value = bar.Name || "";
            document.getElementById("pool-yelp-alias").value = bar["Yelp Alias"] || "";
            document.getElementById("pool-Address").value = bar.Address || "";
            // Auto-fill coordinates from the search result
            document.getElementById('pool-Latitude').value = bar.Latitude || '';
            document.getElementById('pool-Longitude').value = bar.Longitude || '';
            document.getElementById("pool-Website").value = bar.Website || "";

            if (bar["Sunday"]) document.getElementById("pool-Sunday").value = bar.Sunday;
            if (bar["Monday"]) document.getElementById("pool-Monday").value = bar.Monday;
            if (bar["Tuesday"]) document.getElementById("pool-Tuesday").value = bar.Tuesday;
            if (bar["Wednesday"]) document.getElementById("pool-Wednesday").value = bar.Wednesday;
            if (bar["Thursday"]) document.getElementById("pool-Thursday").value = bar.Thursday;
            if (bar["Friday"]) document.getElementById("pool-Friday").value = bar.Friday;
            if (bar["Saturday"]) document.getElementById("pool-Saturday").value = bar.Saturday;

            if (bar["Yelp Rating"]) document.getElementById("pool-yelp-rating").value = bar["Yelp Rating"];

            // Hide search results
            searchResults.style.display = "none";
            searchInput.value = "";
          });
          searchResultsList.appendChild(li);
        });
      }
      searchResults.style.display = "block";
    } catch (err) {
      console.error("Search failed:", err);
      searchResults.style.display = "none";
    }
  });

  // Close search results when clicking elsewhere
  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
      searchResults.style.display = "none";
    }
  });
}

// ── Save (create or update) ───────────────────────────────────────────────
async function savePoolBar() {
  // Use the ID retrieval method from your current script
  const id = document.getElementById("modal-pool-id").value; 

  const doc = {};

  // 1. Process Text and Numeric Fields
  POOL_TEXT_FIELDS.forEach((f) => {
    let formId = f;
    // Handle special field ID mappings (form IDs that don't match POOL_TEXT_FIELDS names)
    if (f === "Yelp Alias") formId = "yelp-alias";
    if (f === "Yelp Rating") formId = "yelp-rating";
    const el = document.getElementById("pool-" + formId);
    if (el && el.value.trim() !== "") {
      // Coerce numeric fields (including the new coordinates)
      if (
        [
          "Yelp Rating",
          "Number_of_Tables",
          "Cost_Per_Game",
          "Cost_Per_Hour",
          "Min_Spend",
          "Latitude",
          "Longitude"
        ].includes(f)
      ) {
        doc[f] = parseFloat(el.value) || null;
      } else {
        doc[f] = el.value.trim();
      }
    }
  });

  // 2. Geocoding Fallback Logic
  // If Latitude or Longitude are missing after the loop, try to fetch them
  if (!doc.Latitude || !doc.Longitude) {
    if (doc.Address) {
      try {
        console.log("Coordinates missing. Attempting to geocode address...");
        const geoRes = await fetch(`${API_BASE}/api/geocode?address=${encodeURIComponent(doc.Address)}`);
        const geoData = await geoRes.json();
        
        if (geoData.lat && geoData.lng) {
          doc.Latitude = geoData.lat;
          doc.Longitude = geoData.lng;
          // Update the UI fields too so the user sees it happened
          if(document.getElementById("pool-Latitude")) document.getElementById("pool-Latitude").value = geoData.lat;
          if(document.getElementById("pool-Longitude")) document.getElementById("pool-Longitude").value = geoData.lng;
        }
      } catch (err) {
        console.error("Geocoding failed:", err);
      }
    }
  }

  // 3. Process Boolean Fields
  POOL_BOOL_FIELDS.forEach((f) => {
    const el = document.getElementById("pool-" + f);
    if (el) doc[f] = el.checked;
  });

  // 4. Validation
  if (!doc["Name"]) {
    toast("Name is required", "error");
    return;
  }

  // 5. Save to Server
  try {
    const url = id ? `/admin/pool-bars/${id}` : "/admin/pool-bars";
    const method = id ? "PUT" : "POST";
    const res = await adminFetch(url, method, doc);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    document.getElementById("pool-modal-overlay").classList.remove("open");
    toast(id ? "Pool bar updated ✓" : "Pool bar added ✓", "success");
    loadPoolBars();
  } catch (err) {
    toast(err.message, "error");
  }
}

// ── Delete ────────────────────────────────────────────────────────────────
async function deletePoolBar(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  try {
    const res = await adminFetch(`/admin/pool-bars/${id}`, "DELETE");
    if (!res.ok) throw new Error((await res.json()).error);
    toast(`"${name}" deleted.`, "success");
    loadPoolBars();
  } catch (err) {
    toast(err.message, "error");
  }
}

document.getElementById("yelp-search-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") yelpSearch();
});

// ═══════════════════════════════════════════════════════════════════════════════
// QUIZZO BARS
// ═══════════════════════════════════════════════════════════════════════════════

let quizzoData = [];
let quizzoFiltered = [];

const QUIZZO_FIELDS = [
  "BUSINESS",
  "BUSINESS_TAGS",
  "TIME",
  "WEEKDAY",
  "OCCURRENCE_TYPES",
  "NEIGHBORHOOD",
  "ADDRESS_STREET",
  "ADDRESS_UNIT",
  "ADDRESS_CITY",
  "ADDRESS_STATE",
  "ADDRESS_ZIP",
  "PRIZE_1_TYPE",
  "PRIZE_1_AMOUNT",
  "PRIZE_2_TYPE",
  "PRIZE_2_AMOUNT",
  "PRIZE_3_TYPE",
  "PRIZE_3_AMOUNT",
  "HOST",
  "EVENT_TYPE",
  "Full_Address",
  "Latitude",
  "Longitude",
];

// ── Load quizzo bars from API ──────────────────────────────────────────────
function loadQuizzoBars() {
  adminFetch("/admin/quizzo")
    .then((r) => r.json())
    .then((data) => {
      quizzoData = data;
      renderQuizzoTable(data);
    })
    .catch((err) => toast("Failed to load quizzo bars: " + err.message, "error"));
}

// ── Render table ───────────────────────────────────────────────────────────
function renderQuizzoTable(data) {
  const tbody = document.getElementById("quizzo-tbody");
  tbody.innerHTML = "";
  if (!Array.isArray(data)) {
    tbody.innerHTML = "<tr><td colspan='8'>Error loading data</td></tr>";
    return;
  }
  if (data.length === 0) {
    tbody.innerHTML = "<tr><td colspan='8' style='text-align:center;padding:20px;'>No quizzo bars yet</td></tr>";
    return;
  }

  data.forEach((bar) => {
    const row = document.createElement("tr");
    const prize1 = bar.PRIZE_1_TYPE ? `${bar.PRIZE_1_TYPE} — ${bar.PRIZE_1_AMOUNT || "?"}` : "—";
    row.innerHTML = `
      <td><strong>${bar.BUSINESS || "—"}</strong></td>
      <td>${bar.WEEKDAY || "—"}</td>
      <td>${bar.TIME || "—"}</td>
      <td>${bar.NEIGHBORHOOD || "—"}</td>
      <td>${bar.ADDRESS_STREET || "—"}</td>
      <td>${bar.HOST || "—"}</td>
      <td>${prize1}</td>
      <td style="text-align:center;white-space:nowrap;">
        <button class="btn-icon" onclick="openQuizzoModal('${bar._id}')" title="Edit">
          <i class="fa fa-edit"></i>
        </button>
        <button class="btn-icon btn-danger" onclick="deleteQuizzoBar('${bar._id}', '${(bar.BUSINESS || 'Bar').replace(/'/g, "\\'")}')" title="Delete">
          <i class="fa fa-trash"></i>
        </button>
      </td>
    `;
    tbody.appendChild(row);
  });
}

// ── Filter ─────────────────────────────────────────────────────────────────
function filterQuizzo(q) {
  const filtered = quizzoData.filter((bar) =>
    JSON.stringify(bar).toLowerCase().includes(q.toLowerCase())
  );
  quizzoFiltered = filtered;
  renderQuizzoTable(filtered);
}

// ── Modal open ─────────────────────────────────────────────────────────────
function openQuizzoModal(id = null) {
  const modal = document.getElementById("quizzo-modal-overlay");
  document.getElementById("quizzo-modal-title").textContent = id
    ? "Edit Quizzo Bar"
    : "Add Quizzo Bar";
  document.getElementById("modal-quizzo-id").value = id || "";

  // Clear all fields first
  QUIZZO_FIELDS.forEach((f) => {
    const el = document.getElementById(`quizzo-${f}`);
    if (el) el.value = "";
  });

  // If editing, populate with existing data
  if (id) {
    const bar = quizzoData.find((b) => b._id === id);
    if (bar) {
      QUIZZO_FIELDS.forEach((f) => {
        const el = document.getElementById(`quizzo-${f}`);
        if (el && bar[f] !== undefined) {
          el.value = bar[f] || "";
        }
      });
    }
  }

  modal.classList.add("open");
}

function closeQuizzoModal(e) {
  if (e && e.target !== document.getElementById("quizzo-modal-overlay")) return;
  document.getElementById("quizzo-modal-overlay").classList.remove("open");
}

// ── Save (create or update) ────────────────────────────────────────────────
async function saveQuizzoBar() {
  const id = document.getElementById("modal-quizzo-id").value;

  const doc = {};

  QUIZZO_FIELDS.forEach((f) => {
    const el = document.getElementById(`quizzo-${f}`);
    if (el) {
      const val = el.value.trim();
      if (val) {
        // Try to parse as number if it looks numeric
        doc[f] = isNaN(val) ? val : parseFloat(val);
      }
    }
  });

  // Validation
  if (!doc["BUSINESS"]) {
    toast("Business name is required", "error");
    return;
  }
  if (!doc["WEEKDAY"]) {
    toast("Day is required", "error");
    return;
  }
  if (!doc["TIME"]) {
    toast("Time is required", "error");
    return;
  }

  // Save to Server
  try {
    const method = id ? "PUT" : "POST";
    const url = id ? `/admin/quizzo/${id}` : "/admin/quizzo";

    const res = await adminFetch(url, method, doc);
    const data = await res.json();

    if (!res.ok) {
      toast(data.error || "Error saving bar", "error");
      return;
    }

    toast(id ? "Bar updated ✓" : "Bar added ✓", "success");
    closeQuizzoModal();
    loadQuizzoBars();
  } catch (err) {
    toast(err.message, "error");
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────
async function deleteQuizzoBar(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  try {
    const res = await adminFetch(`/admin/quizzo/${id}`, "DELETE");
    const data = await res.json();

    if (!res.ok) {
      toast(data.error || "Error deleting bar", "error");
      return;
    }

    toast("Bar deleted ✓", "success");
    loadQuizzoBars();
  } catch (err) {
    toast(err.message, "error");
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// ALL BARS (mappy_hour bars collection — read-only view)
// ═══════════════════════════════════════════════════════════════════════════════

let allBarsData = [];
let allBarsFiltered = [];

function loadAllBars() {
  adminFetch("/admin/all-bars")
    .then((r) => r.json())
    .then((data) => {
      allBarsData = data;
      allBarsFiltered = data;
      const countEl = document.getElementById("allbars-count");
      if (countEl) countEl.textContent = `(${data.length.toLocaleString()} records)`;
      renderAllBarsTable(data);
    })
    .catch((err) => toast("Failed to load bars: " + err.message, "error"));
}

function renderAllBarsTable(data) {
  const tbody = document.getElementById("allbars-tbody");
  tbody.innerHTML = "";
  if (!Array.isArray(data)) {
    tbody.innerHTML = "<tr><td colspan='7'>Error loading data</td></tr>";
    return;
  }
  if (data.length === 0) {
    tbody.innerHTML = "<tr><td colspan='7' style='text-align:center;padding:20px;'>No bars found</td></tr>";
    return;
  }
  data.forEach((bar) => {
    const tr = document.createElement("tr");
    const website = bar.Website
      ? `<a href="${bar.Website}" target="_blank" style="color:var(--green);">Link</a>`
      : "—";
    tr.innerHTML = `
      <td><strong>${bar.Name || "—"}</strong></td>
      <td style="font-size:0.82rem;color:var(--muted);">${bar.Address || "—"}</td>
      <td>${bar.Neighborhood || bar.Neighborhoods || "—"}</td>
      <td>${bar.Phone || "—"}</td>
      <td>${bar["Yelp Rating"] ?? "—"}</td>
      <td>${bar.Price || "—"}</td>
      <td>${website}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// YELP IMPORT
// ═══════════════════════════════════════════════════════════════════════════════

let yelpCurrentBar = null; // holds the mapped doc ready to import

const DAY_MAP = { Monday: 0, Tuesday: 1, Wednesday: 2, Thursday: 3, Friday: 4, Saturday: 5, Sunday: 6 };

function _fmtHour(t) {
  if (!t || t.length !== 4) return t;
  const h = parseInt(t.slice(0, 2), 10), m = t.slice(2);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${m} ${ampm}`;
}

function _buildHoursMap(open) {
  const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const map = {};
  (open || []).forEach(slot => {
    const day = days[slot.day];
    const str = `${_fmtHour(slot.start)} - ${_fmtHour(slot.end)}`;
    map[day] = map[day] ? map[day] + ', ' + str : str;
  });
  return map;
}

async function yelpSearch() {
  const q   = document.getElementById('yelp-search-input').value.trim();
  const loc = document.getElementById('yelp-location-input').value.trim() || 'Philadelphia, PA';
  if (!q) return;
  const btn = document.getElementById('yelp-search-btn');
  btn.disabled = true; btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Searching…';
  document.getElementById('yelp-results').innerHTML = '';
  document.getElementById('yelp-detail-card').style.display = 'none';
  console.log(`[Yelp] Searching: "${q}" in "${loc}"`);
  try {
    const url = `/admin/yelp-search?q=${encodeURIComponent(q)}&location=${encodeURIComponent(loc)}`;
    console.log('[Yelp] Request URL:', API_BASE + url);
    const res  = await adminFetch(url);
    console.log('[Yelp] Response status:', res.status);
    const data = await res.json();
    console.log('[Yelp] Response data:', data);
    if (!res.ok) throw new Error(data.error);
    console.log(`[Yelp] Found ${(data.businesses || []).length} results`);
    renderYelpResults(data.businesses || []);
  } catch(err) {
    console.error('[Yelp] Search error:', err);
    toast('Yelp search failed: ' + err.message, 'error');
  }
  finally { btn.disabled = false; btn.innerHTML = '<i class="fa fa-search"></i> Search Yelp'; }
}

function renderYelpResults(businesses) {
  const el = document.getElementById('yelp-results');
  if (!businesses.length) { el.innerHTML = '<p style="color:var(--muted);">No results found.</p>'; return; }
  el.innerHTML = '';
  const ul = document.createElement('ul');
  ul.style.cssText = 'list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px;';
  businesses.forEach(biz => {
    const li = document.createElement('li');
    li.style.cssText = 'display:flex;align-items:center;justify-content:space-between;background:var(--card-bg);border:1px solid var(--border);border-radius:6px;padding:10px 14px;gap:12px;cursor:pointer;';
    li.innerHTML = `
      <div>
        <strong>${biz.name}</strong>
        <span style="color:var(--muted);font-size:0.82rem;margin-left:8px;">${(biz.location?.display_address || []).join(', ')}</span>
      </div>
      <div style="display:flex;align-items:center;gap:12px;flex-shrink:0;">
        <span style="color:var(--muted);font-size:0.82rem;">⭐ ${biz.rating ?? '—'}  ·  ${biz.price || '—'}  ·  ${biz.review_count ?? 0} reviews</span>
        <button class="btn-table-action btn-edit-pool" style="white-space:nowrap;">View Details</button>
      </div>`;
    li.querySelector('button').addEventListener('click', () => yelpLoadDetails(biz.alias, biz.name));
    ul.appendChild(li);
  });
  el.appendChild(ul);
}

async function yelpLoadDetails(alias, name) {
  document.getElementById('yelp-detail-card').style.display = 'none';
  document.getElementById('yelp-import-status').innerHTML = '';
  toast(`Loading details for ${name}…`, 'success');
  console.log(`[Yelp] Loading details for alias: "${alias}"`);
  try {
    const res  = await adminFetch(`/admin/yelp-details?alias=${encodeURIComponent(alias)}`);
    console.log('[Yelp] Details response status:', res.status);
    const biz  = await res.json();
    console.log('[Yelp] Details data:', biz);
    if (!res.ok) throw new Error(biz.error);

    const addr    = (biz.location?.display_address || []).join(', ');
    const lat     = biz.coordinates?.latitude;
    const lng     = biz.coordinates?.longitude;
    const cats    = (biz.categories || []).map(c => c.title).join(', ');
    const hoursMap = _buildHoursMap(biz.hours?.[0]?.open);
    const phone   = biz.display_phone || biz.phone || '';
    const website = biz.url || '';

    // Build the document that will be saved
    yelpCurrentBar = {
      Name:          biz.name,
      'Yelp Alias':  alias,
      Address:       addr,
      Latitude:      lat,
      Longitude:     lng,
      Phone:         phone,
      Website:       website,
      'Yelp Rating': biz.rating,
      Price:         biz.price || '',
      Categories:    cats,
      ...hoursMap,
    };

    // Render detail card
    document.getElementById('yelp-detail-name').textContent = biz.name;
    document.getElementById('yelp-detail-meta').textContent =
      `${addr}  ·  ${phone}  ·  ⭐ ${biz.rating}  ·  ${biz.price || '—'}  ·  ${cats}`;

    const grid = document.getElementById('yelp-detail-grid');
    grid.innerHTML = '';
    const fields = { 'Yelp Alias': alias, Address: addr, Latitude: lat, Longitude: lng,
      Phone: phone, Rating: biz.rating, Price: biz.price, Categories: cats,
      Website: website ? `<a href="${website}" target="_blank" style="color:var(--green);">Link</a>` : '—' };
    Object.entries(fields).forEach(([k, v]) => {
      grid.innerHTML += `<div style="font-size:0.82rem;"><span style="color:var(--muted);display:block;margin-bottom:2px;">${k}</span><strong>${v ?? '—'}</strong></div>`;
    });

    const hgrid = document.getElementById('yelp-hours-grid');
    hgrid.innerHTML = '';
    ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].forEach(day => {
      hgrid.innerHTML += `<div style="background:var(--hover);border-radius:4px;padding:6px 8px;">
        <div style="font-weight:600;margin-bottom:2px;">${day.slice(0,3)}</div>
        <div style="color:var(--muted);">${hoursMap[day] || '—'}</div></div>`;
    });

    document.getElementById('yelp-detail-card').style.display = 'block';
  } catch(err) { toast('Failed to load details: ' + err.message, 'error'); }
}

async function yelpImport() {
  if (!yelpCurrentBar) return;
  const btn = document.getElementById('yelp-import-btn');
  btn.disabled = true; btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Importing…';
  const statusEl = document.getElementById('yelp-import-status');
  try {
    const res  = await adminFetch('/admin/yelp-import', 'POST', yelpCurrentBar);
    const data = await res.json();
    if (res.status === 409) {
      statusEl.innerHTML = `<span style="color:#fbbf24;"><i class="fa fa-warning"></i> Already in collection (ID: ${data.id})</span>`;
      return;
    }
    if (!res.ok) throw new Error(data.error);
    
    const yelpAlias = yelpCurrentBar['Yelp Alias'];
    const barName = yelpCurrentBar.Name;
    
    // Now fetch photos for the newly imported bar
    statusEl.innerHTML = `<span style="color:var(--green);"><i class="fa fa-check"></i> Added successfully (ID: ${data.id})</span>`;
    toast(`${barName} added to bars collection ✓`, 'success');
    
    // Fetch photos in background
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Fetching photos…';
    try {
      const photoRes = await adminFetch('/admin/fetch-bar-photos', 'POST', { yelpAlias });
      const photoData = await photoRes.json();
      if (photoRes.ok && photoData.photosCount > 0) {
        statusEl.innerHTML += `<br><span style="color:var(--green);"><i class="fa fa-image"></i> ${photoData.photosCount} photo${photoData.photosCount !== 1 ? 's' : ''} added ✓</span>`;
        toast(`Photos added for ${barName} ✓`, 'success');
      } else if (photoRes.ok) {
        statusEl.innerHTML += `<br><span style="color:var(--muted);"><i class="fa fa-image"></i> No photos available on Yelp</span>`;
      }
    } catch(photoErr) {
      console.warn('Photo fetch background error:', photoErr);
      // Don't fail the import if photo fetch fails
      statusEl.innerHTML += `<br><span style="color:var(--muted);"><i class="fa fa-warning"></i> Could not fetch photos</span>`;
    }
    
    yelpCurrentBar = null;
  } catch(err) {
    statusEl.innerHTML = `<span style="color:#f87171;"><i class="fa fa-times"></i> ${err.message}</span>`;
    toast('Import failed: ' + err.message, 'error');
  } finally { btn.disabled = false; btn.innerHTML = '<i class="fa fa-plus"></i> Add to Bars Collection'; }
}

function filterAllBars(q) {
  const lower = q.trim().toLowerCase();
  allBarsFiltered = lower
    ? allBarsData.filter((b) => (b.Name || '').toLowerCase().includes(lower)
        || (b.Address || '').toLowerCase().includes(lower)
        || (b.Neighborhood || b.Neighborhoods || '').toLowerCase().includes(lower))
    : allBarsData;
  renderAllBarsTable(allBarsFiltered);
}

// ═══════════════════════════════════════════════════════════════════════════════
// BAR PHOTOS
// ═══════════════════════════════════════════════════════════════════════════════

let photosData = [];          // all bars (with or without photos)
let photosFiltered = [];      // currently visible subset
const selectedPhotos = new Map(); // barId → Set of URLs marked for deletion

async function loadBarPhotos() {
  document.getElementById('photos-grid').innerHTML =
    '<p style="color:var(--muted);grid-column:1/-1;">Loading…</p>';
  try {
    const res  = await adminFetch('/admin/all-bars');
    const data = await res.json();
    photosData     = data;
    photosFiltered = data;
    const countEl = document.getElementById('photos-count');
    const withPhotos = data.filter(b => b.Photos?.length).length;
    if (countEl) countEl.textContent = `(${withPhotos} with photos, ${data.length} total)`;
    renderPhotosGrid(photosFiltered);
  } catch (err) {
    toast('Failed to load photos: ' + err.message, 'error');
  }
}

function filterPhotos(q) {
  const lower = q.trim().toLowerCase();
  const hasPhotosOnly = document.getElementById('photos-has-photos-only').checked;
  photosFiltered = photosData.filter(b => {
    if (hasPhotosOnly && !b.Photos?.length) return false;
    if (lower && !(b.Name || '').toLowerCase().includes(lower)) return false;
    return true;
  });
  renderPhotosGrid(photosFiltered);
}

function renderPhotosGrid(data) {
  const grid = document.getElementById('photos-grid');
  grid.innerHTML = '';

  if (!data.length) {
    grid.innerHTML = '<p style="color:var(--muted);grid-column:1/-1;">No bars match.</p>';
    return;
  }

  data.forEach(bar => {
    const card = document.createElement('div');
    card.style.cssText =
      'background:var(--card-bg);border:1px solid var(--border);border-radius:8px;overflow:hidden;display:flex;flex-direction:column;';

    const nameBar = document.createElement('div');
    nameBar.style.cssText = 'padding:10px 12px;font-weight:600;font-size:0.88rem;border-bottom:1px solid var(--border);';
    nameBar.textContent = bar.Name || '—';
    card.appendChild(nameBar);

    const photos = bar.Photos || [];
    if (!photos.length) {
      const empty = document.createElement('div');
      empty.style.cssText = 'padding:24px;text-align:center;color:var(--muted);font-size:0.8rem;flex:1;';
      empty.textContent = 'No photos';
      card.appendChild(empty);
    } else {
      const photoWrap = document.createElement('div');
      photoWrap.style.cssText = 'display:flex;flex-direction:column;gap:0;';

      photos.forEach((url, idx) => {
        const row = document.createElement('label');
        row.style.cssText =
          'display:flex;align-items:center;gap:10px;padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--border);transition:background 0.1s;';
        row.addEventListener('mouseenter', () => row.style.background = 'rgba(255,255,255,0.04)');
        row.addEventListener('mouseleave', () => row.style.background = '');

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.style.cssText = 'width:16px;height:16px;flex-shrink:0;accent-color:#f87171;cursor:pointer;';
        cb.addEventListener('change', () => {
          if (!selectedPhotos.has(bar._id)) selectedPhotos.set(bar._id, new Set());
          const set = selectedPhotos.get(bar._id);
          cb.checked ? set.add(url) : set.delete(url);
          if (!set.size) selectedPhotos.delete(bar._id);
          updateDeleteBtn();
        });

        const img = document.createElement('img');
        img.src = url;
        img.alt = `Photo ${idx + 1}`;
        img.style.cssText = 'width:20vh;height:20vh;object-fit:cover;border-radius:4px;flex-shrink:0;';
        img.onerror = () => { img.style.display = 'none'; };

        const label = document.createElement('span');
        label.style.cssText = 'font-size:0.72rem;color:var(--muted);word-break:break-all;line-height:1.3;';
        label.textContent = `Photo ${idx + 1}`;

        row.appendChild(cb);
        row.appendChild(img);
        row.appendChild(label);
        photoWrap.appendChild(row);
      });

      card.appendChild(photoWrap);
    }

    grid.appendChild(card);
  });
}

function updateDeleteBtn() {
  let total = 0;
  selectedPhotos.forEach(set => { total += set.size; });
  const btn   = document.getElementById('photos-delete-btn');
  const count = document.getElementById('photos-selected-count');
  if (total > 0) {
    btn.style.display = '';
    count.textContent = total;
  } else {
    btn.style.display = 'none';
  }
}

async function deleteSelectedPhotos() {
  const total = [...selectedPhotos.values()].reduce((n, s) => n + s.size, 0);
  if (!total) return;
  if (!confirm(`Permanently delete ${total} photo URL${total !== 1 ? 's' : ''}? This cannot be undone.`)) return;

  const btn = document.getElementById('photos-delete-btn');
  btn.disabled = true;

  const promises = [...selectedPhotos.entries()].map(async ([barId, urlSet]) => {
    const res = await adminFetch(`/admin/bars/${barId}/photos`, 'PATCH', { removeUrls: [...urlSet] });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Delete failed');
    }
    return res.json();
  });

  try {
    await Promise.all(promises);
    toast(`${total} photo${total !== 1 ? 's' : ''} deleted.`, 'success');
    selectedPhotos.clear();
    updateDeleteBtn();
    // Reload to reflect changes
    photosData = [];
    loadBarPhotos();
  } catch (err) {
    toast('Error: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// UNMATCHED QUIZZO BARS
// ═══════════════════════════════════════════════════════════════════════════════

let unmatchedData = [];

async function loadUnmatched() {
  const tbody = document.getElementById('unmatched-tbody');
  tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--muted);">Loading…</td></tr>';
  try {
    const res  = await adminFetch('/admin/quizzo-unmatched');
    const data = await res.json();
    unmatchedData = data;
    const badge   = document.getElementById('badge-unmatched');
    const countEl = document.getElementById('unmatched-count');
    if (badge)   badge.textContent   = data.length;
    if (countEl) countEl.textContent = `(${data.length} bars)`;
    renderUnmatchedTable(data);
  } catch (err) {
    toast('Failed to load unmatched bars: ' + err.message, 'error');
  }
}

function filterUnmatched(q) {
  const lower = q.trim().toLowerCase();
  const filtered = lower
    ? unmatchedData.filter(b =>
        (b.BUSINESS || '').toLowerCase().includes(lower) ||
        (b.NEIGHBORHOOD || '').toLowerCase().includes(lower))
    : unmatchedData;
  renderUnmatchedTable(filtered);
}

function renderUnmatchedTable(data) {
  const tbody = document.getElementById('unmatched-tbody');
  tbody.innerHTML = '';

  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--muted);">All quizzo bars matched!</td></tr>';
    return;
  }

  data.forEach(bar => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${bar.BUSINESS || '—'}</strong></td>
      <td>${bar.NEIGHBORHOOD || '—'}</td>
      <td style="font-size:0.82rem;color:var(--muted);">${bar.ADDRESS_STREET || '—'}</td>
      <td>
        <button class="btn-table-action btn-approve"
          data-id="${bar._id}"
          data-name="${(bar.BUSINESS || '').replace(/"/g, '&quot;')}"
          onclick="addQuizzoToMasterBars(this.dataset.id, this.dataset.name)"
          title="Add to bars collection">
          <i class="fa fa-plus"></i> Add to Bars
        </button>
      </td>`;
    tbody.appendChild(tr);
  });
}

async function addQuizzoToMasterBars(id, name) {
  if (!confirm(`Add "${name}" to the bars collection as a new entry?`)) return;
  try {
    const res  = await adminFetch(`/admin/quizzo-to-bars/${id}`, 'POST');
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    toast(`"${name}" added to bars collection.`, 'success');
    // Remove from local list and re-render
    unmatchedData = unmatchedData.filter(b => b._id !== id);
    const badge = document.getElementById('badge-unmatched');
    if (badge) badge.textContent = unmatchedData.length;
    renderUnmatchedTable(unmatchedData);
  } catch (err) {
    toast('Failed: ' + err.message, 'error');
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// SPORTS BARS
// ═══════════════════════════════════════════════════════════════════════════════

let sportsData = [];
let sportsFiltered = [];
let sportsTeamsData = [];  // all teams from sports_teams collection

// ── Load sports bars from API ──────────────────────────────────────────────
async function loadSportsBars() {
  try {
    const res = await adminFetch("/admin/sports-bars");
    const data = await res.json();
    sportsData = data;
    sportsFiltered = data;
    renderSportsTable(data);
    document.getElementById("sports-count").textContent = `(${data.length})`;
  } catch (err) {
    toast("Failed to load sports bars: " + err.message, "error");
  }
}

// ── Load teams for modal dropdowns ─────────────────────────────────────────
async function loadSportsTeams() {
  try {
    const res = await adminFetch("/api/sports-teams");
    sportsTeamsData = await res.json();
  } catch (err) {
    console.warn("Failed to load sports teams:", err.message);
  }
}

// ── Render table ───────────────────────────────────────────────────────────
function renderSportsTable(data) {
  const tbody = document.getElementById("sports-tbody");
  tbody.innerHTML = "";
  if (!Array.isArray(data)) return;
  if (data.length === 0) {
    tbody.innerHTML = "<tr><td colspan='6' style='text-align:center;padding:24px;color:var(--muted);'>No sports bars found</td></tr>";
    return;
  }

  data.forEach((bar) => {
    const row = document.createElement("tr");
    const phillyTeams = (bar.philly_affiliates || []).filter(Boolean).join(", ");
    const otherTeams = [
      ...(bar.other_nhl_nba_mlb_nfl_teams || []),
      bar.premier_league_team,
      ...(bar.other_soccer_teams || []),
    ].filter(Boolean).join(", ");

    row.innerHTML = `
      <td>${bar.Name || "—"}</td>
      <td>${bar.Address || "—"}</td>
      <td>${bar.Neighborhood || "—"}</td>
      <td><small>${phillyTeams || "—"}</small></td>
      <td><small>${otherTeams || "—"}</small></td>
      <td>
        <button class="btn-icon" onclick="openSportsModal('${bar._id}')" title="Edit teams">
          <i class="fa fa-edit"></i>
        </button>
      </td>
    `;
    tbody.appendChild(row);
  });
}

// ── Filter ────────────────────────────────────────────────────────────────
function filterSports(q) {
  const lowerQ = q.trim().toLowerCase();
  sportsFiltered = sportsData.filter((bar) => {
    const name = (bar.Name || "").toLowerCase();
    const addr = (bar.Address || "").toLowerCase();
    const nh = (bar.Neighborhood || "").toLowerCase();
    return name.includes(lowerQ) || addr.includes(lowerQ) || nh.includes(lowerQ);
  });
  renderSportsTable(sportsFiltered);
}

// ── Modal open ─────────────────────────────────────────────────────────────
function openSportsModal(id) {
  const bar = sportsData.find((b) => b._id === id);
  if (!bar) return;

  document.getElementById("sports-modal-id").value = id;
  document.getElementById("sports-Name").value = bar.Name || "";
  document.getElementById("sports-Address").value = bar.Address || "";
  document.getElementById("sports-Neighborhood").value = bar.Neighborhood || "";

  // Build Philly teams checkboxes
  const phillyContainer = document.getElementById("sports-philly-teams-container");
  phillyContainer.innerHTML = "";

  // Philly teams: Eagles, Phillies, 76ers, Flyers, Union
  const phillyTeams = ["Philadelphia Eagles", "Philadelphia Phillies", "Philadelphia 76ers", "Philadelphia Flyers", "Philadelphia Union"];
  const currentPhilly = new Set(bar.philly_affiliates || []);

  phillyTeams.forEach((team) => {
    const label = document.createElement("label");
    label.className = "modal-check";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.className = "sports-philly-check";
    input.value = team;
    input.checked = currentPhilly.has(team);
    label.appendChild(input);
    const span = document.createElement("span");
    span.textContent = team.replace("Philadelphia ", "");
    label.appendChild(span);
    phillyContainer.appendChild(label);
  });

  // Build other teams multi-select by league
  const otherContainer = document.getElementById("sports-other-teams-container");
  otherContainer.innerHTML = "";

  const currentOther = new Set([
    ...(bar.other_nhl_nba_mlb_nfl_teams || []),
    ...(bar.other_soccer_teams || []),
  ]);

  // Group teams by league
  const LEAGUE_ORDER = ["NFL", "NBA", "MLB", "NHL", "MLS"];
  LEAGUE_ORDER.forEach((league) => {
    const leagueTeams = sportsTeamsData.filter((t) => t.league === league);
    if (leagueTeams.length === 0) return;

    const leagueDiv = document.createElement("div");
    leagueDiv.style.gridColumn = "span 9999";
    leagueDiv.style.fontSize = "0.85rem";
    leagueDiv.style.fontWeight = "700";
    leagueDiv.style.color = "var(--muted)";
    leagueDiv.style.marginTop = "8px";
    leagueDiv.textContent = league;
    otherContainer.appendChild(leagueDiv);

    leagueTeams.forEach((team) => {
      const label = document.createElement("label");
      label.className = "modal-check";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.className = "sports-other-check";
      input.value = team.team_name;
      input.checked = currentOther.has(team.team_name);
      label.appendChild(input);
      const span = document.createElement("span");
      span.textContent = team.team_name;
      label.appendChild(span);
      otherContainer.appendChild(label);
    });
  });

  // Populate Premier League dropdown
  const premierSelect = document.getElementById("sports-premier-league-team");
  premierSelect.innerHTML = "<option value=''>None</option>";
  const premierTeams = sportsTeamsData.filter((t) => t.league === "Premier League").sort((a, b) => a.team_name.localeCompare(b.team_name));
  premierTeams.forEach((team) => {
    const opt = document.createElement("option");
    opt.value = team.team_name;
    opt.textContent = team.team_name;
    opt.selected = bar.premier_league_team === team.team_name;
    premierSelect.appendChild(opt);
  });

  document.getElementById("sports-modal-overlay").classList.add("open");
}

function closeSportsModal(e) {
  if (e && e.target !== document.getElementById("sports-modal-overlay")) return;
  document.getElementById("sports-modal-overlay").classList.remove("open");
}

// ── Save ───────────────────────────────────────────────────────────────────
async function saveSportsBar() {
  const id = document.getElementById("sports-modal-id").value;
  if (!id) {
    toast("No bar selected", "error");
    return;
  }

  // Collect Philly teams
  const phillyTeams = [];
  document.querySelectorAll(".sports-philly-check:checked").forEach((el) => {
    phillyTeams.push(el.value);
  });

  // Collect other teams
  const otherTeams = [];
  document.querySelectorAll(".sports-other-check:checked").forEach((el) => {
    otherTeams.push(el.value);
  });

  // Get premier league team
  const premierLeagueTeam = document.getElementById("sports-premier-league-team").value || null;

  try {
    const res = await adminFetch(`/admin/sports-bars/${id}`, "PATCH", {
      philly_affiliates: phillyTeams,
      other_nhl_nba_mlb_nfl_teams: otherTeams,
      premier_league_team: premierLeagueTeam,
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    toast("Sports bar updated successfully");
    closeSportsModal();
    loadSportsBars();
  } catch (err) {
    toast("Failed to save: " + err.message, "error");
  }
}