/**
 * Mappy Hour - Express Backend
 * 
 * Collections:
 *   quizzo        — live data (mirrors your CSV; source of truth)
 *   pending       — new bar submissions awaiting approval
 *   pending_edits — edit requests for existing bars awaiting approval
 * 
 * Setup:
 *   npm install express mongoose cors dotenv json2csv
 *   Add MONGODB_URI and ADMIN_PASSWORD to .env
 */

if (process.env.NODE_ENV !== 'production') {
  require('dotenv').config();
}
const express    = require('express');
const mongoose   = require('mongoose');
const cors       = require('cors');
const cookieParser = require('cookie-parser');
const { Parser } = require('json2csv');
const path       = require('path');
const fs         = require('fs');

// ─── Firebase Admin SDK ───────────────────────────────────────────────────────
const admin = require('firebase-admin');
(() => {
  try {
    let credential;
    if (process.env.FIREBASE_SERVICE_ACCOUNT) {
      // Railway: set this env var to the raw JSON string of the service account key
      const sa = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
      credential = admin.credential.cert(sa);
    } else {
      // Local: place serviceAccountKey.json at repo root (never commit it)
      const keyPath = path.join(__dirname, 'serviceAccountKey.json');
      credential = admin.credential.cert(require(keyPath));
    }
    admin.initializeApp({ credential });
    console.log('[Firebase Admin] initialized');
  } catch (e) {
    console.warn('[Firebase Admin] not initialized — auth routes will be disabled:', e.message);
  }
})();

// Middleware: verify Firebase ID token sent as Authorization: Bearer <token>
async function verifyFirebaseToken(req, res, next) {
  const header = req.headers.authorization || '';
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) return res.status(401).json({ error: 'No token provided' });
  try {
    req.firebaseUser = await admin.auth().verifyIdToken(token);
    next();
  } catch (e) {
    res.status(401).json({ error: 'Invalid or expired token' });
  }
}

const app  = express();
const PORT = process.env.PORT || 3000;

app.use(cors({
  origin: [
    'http://localhost:3000',
    'http://127.0.0.1:5500',
    'https://www.philly-mappy-hour.com',
    'https://philly-mappy-hour.com',
    'https://philly-happy-hour-map-production.up.railway.app',
  ],
  credentials: true  // Allow cookies in CORS requests
}));
app.use(express.json());
app.use(cookieParser());  // Parse cookies in requests

// ─── Serve static files (your existing site) ────────────────────────────────
app.use(express.static(path.join(__dirname, 'public')));

// ─── MongoDB connection ──────────────────────────────────────────────────────
// mongoose.connect(process.env.MONGODB_URI)
//   .then(() => console.log('MongoDB connected'))
//   .catch(err => { console.error('MongoDB connection error:', err); process.exit(1); });

// mongoose.connect(process.env.MONGODB_URI, {
//   tls: true,
//   tlsAllowInvalidCertificates: true,  // temporary to test
//   serverSelectionTimeoutMS: 15000,
// })
//   .then(() => console.log('MongoDB connected'))
//   .catch(err => { console.error('MongoDB connection error:', err); process.exit(1); });

// ─── MongoDB Connections ──────────────────────────────────────────────────────
const connectionOptions = {
  tls: true,
  tlsAllowInvalidCertificates: true,
  serverSelectionTimeoutMS: 15000,
};

// Connection 1: Quizzo Bars
const quizzoDb = mongoose.createConnection(process.env.MONGODB_URI, connectionOptions);
quizzoDb.on('connected', () => console.log('Connected to Quizzo Bars DB'));
quizzoDb.on('error', (err) => console.error('Quizzo Bars connection error:', err));

console.log("Mappy Hour URI:", process.env.MONGODB_URI.replace('quizzo_bars', 'mappy_hour'));
// Connection 2: Mappy Hour
const mappyHourDb = mongoose.createConnection(process.env.MONGODB_URI.replace('quizzo_bars', 'mappy_hour'), connectionOptions);
mappyHourDb.on('connected', () => console.log('Connected to Mappy Hour DB'));
mappyHourDb.on('error', (err) => console.error('Mappy Hour connection error:', err));
// ─── Schemas ─────────────────────────────────────────────────────────────────
const quizzoSchema = new mongoose.Schema({
  BUSINESS:       String,
  BUSINESS_TAGS:  String,
  TIME:           String,
  WEEKDAY:        String,
  OCCURRENCE_TYPES: String,
  NEIGHBORHOOD:   String,
  ADDRESS_STREET: String,
  ADDRESS_UNIT:   String,
  ADDRESS_CITY:   String,
  ADDRESS_STATE:  String,
  ADDRESS_ZIP:    String,
  PRIZE_1_TYPE:   String,
  PRIZE_1_AMOUNT: Number,
  PRIZE_2_TYPE:   String,
  PRIZE_2_AMOUNT: Number,
  PRIZE_3_TYPE:   String,
  PRIZE_3_AMOUNT: Number,
  HOST:           String,
  EVENT_TYPE:     String,
  Full_Address:   String,
  Latitude:       Number,
  Longitude:      Number,
}, { collection: 'Quizzo Bars' });

// Pending new bar submission
const pendingSchema = new mongoose.Schema({
  BUSINESS:       { type: String, required: true },
  ADDRESS:        String,
  ADDRESS_STREET: String,
  ADDRESS_CITY:   String,
  ADDRESS_STATE:  String,
  ADDRESS_ZIP:    String,
  NEIGHBORHOOD:   String,
  Latitude:       Number,
  Longitude:      Number,
  WEEKDAY:        String,
  TIME:           String,
  PRIZE_1_TYPE:   String,
  PRIZE_1_AMOUNT: String,
  PRIZE_2_TYPE:   String,
  PRIZE_2_AMOUNT: String,
  HOST:           String,
  NOTES:          String,    // optional submitter notes
  submittedAt:    { type: Date, default: Date.now },
  status:         { type: String, default: 'pending' }, // pending | approved | rejected
}, { collection: 'pending' });

// Pending edit to an existing bar
const pendingEditSchema = new mongoose.Schema({
  originalBusiness: { type: String, required: true }, // name of bar being edited
  originalId:       mongoose.Schema.Types.ObjectId,   // _id of the quizzo doc
  changes: {                                          // only fields the user changed
    BUSINESS:       String,
    ADDRESS_STREET: String,
    ADDRESS_UNIT:   String,
    ADDRESS_CITY:   String,
    ADDRESS_STATE:  String,
    ADDRESS_ZIP:    String,
    WEEKDAY:        String,
    TIME:           String,
    EVENT_TYPE:     String,
    PRIZE_1_TYPE:   String,
    PRIZE_1_AMOUNT: String,
    PRIZE_2_TYPE:   String,
    PRIZE_2_AMOUNT: String,
    HOST:           String,
  },
  NOTES:        String,
  submittedAt:  { type: Date, default: Date.now },
  status:       { type: String, default: 'pending' },
}, { collection: 'pending_edits' });

const Quizzo      = quizzoDb.model('Quizzo',      quizzoSchema);
const Pending     = quizzoDb.model('Pending',     pendingSchema);
const PendingEdit = quizzoDb.model('PendingEdit', pendingEditSchema);

// ─── Simple admin auth middleware (read from HttpOnly cookie) ───────────────
function adminAuth(req, res, next) {
  const token = req.cookies.adminToken;  // Read from HttpOnly cookie
  if (token && token === process.env.ADMIN_PASSWORD) return next();
  res.status(401).json({ error: 'Unauthorized' });
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTHENTICATION ROUTES
// ═══════════════════════════════════════════════════════════════════════════════

// Admin login endpoint
app.post('/admin/login', (req, res) => {
  const { password, captchaToken } = req.body;
  if (!password) return res.status(400).json({ error: 'Password required' });

  // Validate the captcha token issued by /api/verify-captcha
  const expiry = _captchaTokens.get(captchaToken);
  if (!captchaToken || expiry === undefined || expiry < Date.now()) {
    _captchaTokens.delete(captchaToken);
    return res.status(401).json({ error: 'Must complete captcha first' });
  }

  if (password !== process.env.ADMIN_PASSWORD) {
    return res.status(401).json({ error: 'Invalid password' });
  }

  // Consume the token — single use
  _captchaTokens.delete(captchaToken);

  // Always use secure on HTTPS domains; for localhost use false
  const isSecure = req.hostname !== 'localhost' && req.hostname !== '127.0.0.1';
  res.cookie('adminToken', process.env.ADMIN_PASSWORD, {
    httpOnly: true,
    secure: isSecure,
    sameSite: 'Strict',
    path: '/',
    domain: undefined,  // Let Express use the request domain automatically
    maxAge: 24 * 60 * 60 * 1000
  });

  console.log(`[Auth] Login successful. Set adminToken cookie (secure=${isSecure}, domain=${req.hostname})`);
  res.json({ success: true, message: 'Logged in successfully' });
});

// Admin logout endpoint
app.post('/admin/logout', (req, res) => {
  const isSecure = req.hostname !== 'localhost' && req.hostname !== '127.0.0.1';
  res.clearCookie('adminToken', {
    httpOnly: true,
    secure: isSecure,
    sameSite: 'Strict',
    path: '/'
  });
  res.json({ success: true, message: 'Logged out' });
});

// Check if admin is authenticated
app.get('/admin/check-auth', (req, res) => {
  const token = req.cookies.adminToken;
  const isAuthenticated = token && token === process.env.ADMIN_PASSWORD;
  
  if (!isAuthenticated) {
    console.log(`[Auth] Check failed: no valid token. Cookies: ${Object.keys(req.cookies).join(', ') || 'none'}`);
  }
  
  res.status(isAuthenticated ? 200 : 401).json({ authenticated: isAuthenticated });
});

// Check if user passed captcha or has admin token (for gating admin pages)
app.get('/admin/check-captcha', (req, res) => {
  const hasAdminToken = req.cookies.adminToken && req.cookies.adminToken === process.env.ADMIN_PASSWORD;
  
  // Check if user has captcha cookie with correct value (server-side verification)
  // Note: The cookie value must match ADMIN_PASSWORD to prevent forged cookies
  const hasCaptchaPassed = req.cookies.captchaPassed && 
                           req.cookies.captchaPassed === process.env.ADMIN_PASSWORD;
  
  if (hasAdminToken || hasCaptchaPassed) {
    return res.json({ authenticated: true });
  }
  res.status(401).json({ authenticated: false });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC ROUTES
// ═══════════════════════════════════════════════════════════════════════════════

// Live quizzo data (replaces CSV fetch in index.html)

// ── Simple in-memory rate limiter for public endpoints ───────────────────────
// Limits each IP to 60 requests per minute on public search/data routes
const _rateLimitMap = new Map();
function rateLimit(maxPerMinute = 60) {
  return function(req, res, next) {
    const ip  = req.ip || req.connection.remoteAddress || 'unknown';
    const now = Date.now();
    const windowMs = 60_000;
    const entry = _rateLimitMap.get(ip) || { count: 0, start: now };

    if (now - entry.start > windowMs) {
      entry.count = 1;
      entry.start = now;
    } else {
      entry.count++;
    }
    _rateLimitMap.set(ip, entry);

    // Prune old entries every 5 minutes to avoid memory leak
    if (_rateLimitMap.size > 5000) {
      for (const [k, v] of _rateLimitMap) {
        if (now - v.start > windowMs * 5) _rateLimitMap.delete(k);
      }
    }

    if (entry.count > maxPerMinute) {
      return res.status(429).json({ error: 'Too many requests — please slow down.' });
    }
    next();
  };
}

// Stricter limit for the search endpoint (20/min per IP)
const searchRateLimit = rateLimit(20);

app.get('/api/quizzo', async (req, res) => {
  try {
    const bars = await Quizzo.find({}, {
      _id: 0, __v: 0,
      // exclude internal/admin-only fields
      Full_Address: 0,
      OCCURRENCE_TYPES: 0,
      BUSINESS_TAGS: 0,
    }).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Geocode an address via Nominatim
app.get('/api/geocode', async (req, res) => {
  const { address } = req.query;
  if (!address) return res.status(400).json({ error: 'address is required' });
  try {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}&format=json&limit=1`;
    const response = await fetch(url, { headers: { 'User-Agent': 'MappyHour/1.0' } });
    const data = await response.json();
    if (!data.length) return res.json({ lat: null, lng: null });
    res.json({ lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Submit a new bar
app.post('/submit-bar', async (req, res) => {
  try {
    const { businessName, streetAddress, city, state, zip, neighborhood,
            fullAddress, lat, lng, weekday, time,
            firstPrize, firstPrizeAmount, secondPrize, secondPrizeAmount,
            host, notes } = req.body;

    if (!businessName) return res.status(400).json({ error: 'Business name is required' });

    const submission = new Pending({
      BUSINESS:       businessName.trim().toUpperCase(),
      ADDRESS:        fullAddress || streetAddress,
      ADDRESS_STREET: streetAddress,
      ADDRESS_CITY:   city || 'Philadelphia',
      ADDRESS_STATE:  state || 'PA',
      ADDRESS_ZIP:    zip || '',
      NEIGHBORHOOD:   neighborhood?.toUpperCase(),
      Latitude:       lat,
      Longitude:      lng,
      WEEKDAY:        weekday?.toUpperCase(),
      TIME:           time,
      PRIZE_1_TYPE:   firstPrize,
      PRIZE_1_AMOUNT: firstPrizeAmount,
      PRIZE_2_TYPE:   secondPrize,
      PRIZE_2_AMOUNT: secondPrizeAmount,
      HOST:           host?.toUpperCase(),
      NOTES:          notes,
    });

    await submission.save();
    res.json({ success: true, message: 'Submission received — thanks!' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Submit an edit to an existing bar
app.post('/submit-edit', async (req, res) => {
  try {
    const { originalBusiness, originalId, changes, notes } = req.body;
    if (!originalBusiness) return res.status(400).json({ error: 'originalBusiness is required' });

    const edit = new PendingEdit({ originalBusiness, originalId, changes, notes });
    await edit.save();
    res.json({ success: true, message: 'Edit submitted for review — thanks!' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN ROUTES  (all require x-admin-token header)
// ═══════════════════════════════════════════════════════════════════════════════

// Get all pending submissions
app.get('/admin/pending', adminAuth, async (req, res) => {
  try {
    const [submissions, edits] = await Promise.all([
      Pending.find({ status: 'pending' }).lean(),
      PendingEdit.find({ status: 'pending' }).lean(),
    ]);
    res.json({ submissions, edits });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Approve a new bar submission
app.post('/admin/approve/:id', adminAuth, async (req, res) => {
  try {
    const submission = await Pending.findById(req.params.id);
    if (!submission) return res.status(404).json({ error: 'Submission not found' });

    // Optionally merge in any admin overrides from request body
    const overrides = req.body || {};

    const newBar = new Quizzo({
      BUSINESS:       overrides.BUSINESS       || submission.BUSINESS,
      TIME:           overrides.TIME           || submission.TIME,
      WEEKDAY:        overrides.WEEKDAY        || submission.WEEKDAY,
      EVENT_TYPE:     overrides.EVENT_TYPE     || submission.EVENT_TYPE,
      ADDRESS_STREET: overrides.ADDRESS_STREET || '',
      ADDRESS_CITY:   overrides.ADDRESS_CITY   || '',
      ADDRESS_STATE:  overrides.ADDRESS_STATE  || '',
      ADDRESS_ZIP:    overrides.ADDRESS_ZIP    || '',
      PRIZE_1_TYPE:   overrides.PRIZE_1_TYPE   || submission.PRIZE_1_TYPE,
      PRIZE_1_AMOUNT: overrides.PRIZE_1_AMOUNT || submission.PRIZE_1_AMOUNT,
      PRIZE_2_TYPE:   overrides.PRIZE_2_TYPE   || submission.PRIZE_2_TYPE,
      PRIZE_2_AMOUNT: overrides.PRIZE_2_AMOUNT || submission.PRIZE_2_AMOUNT,
      HOST:           overrides.HOST           || submission.HOST,
      Full_Address:   submission.ADDRESS,
      // Latitude/Longitude left blank — run geocode_addresses() after export
    });

    await newBar.save();
    submission.status = 'approved';
    await submission.save();

    await exportCsv(); // regenerate CSV so the map stays in sync
    res.json({ success: true, insertedId: newBar._id });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Reject a new bar submission
app.post('/admin/reject/:id', adminAuth, async (req, res) => {
  try {
    const submission = await Pending.findByIdAndUpdate(
      req.params.id,
      { status: 'rejected' },
      { new: true }
    );
    if (!submission) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Approve an edit
app.post('/admin/approve-edit/:id', adminAuth, async (req, res) => {
  try {
    const edit = await PendingEdit.findById(req.params.id);
    if (!edit) return res.status(404).json({ error: 'Edit not found' });

    // Find the bar by _id if we have it, otherwise by name
    const filter = edit.originalId
      ? { _id: edit.originalId }
      : { BUSINESS: edit.originalBusiness };

    const updated = await Quizzo.findOneAndUpdate(
      filter,
      { $set: edit.changes },
      { new: true }
    );
    if (!updated) return res.status(404).json({ error: 'Original bar not found in quizzo collection' });

    edit.status = 'approved';
    await edit.save();

    await exportCsv();
    res.json({ success: true, updated });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Reject an edit
app.post('/admin/reject-edit/:id', adminAuth, async (req, res) => {
  try {
    const edit = await PendingEdit.findByIdAndUpdate(
      req.params.id,
      { status: 'rejected' },
      { new: true }
    );
    if (!edit) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Manually trigger CSV export
app.post('/admin/export-csv', adminAuth, async (req, res) => {
  try {
    await exportCsv();
    res.json({ success: true, message: 'CSV exported to public/assets/quizzo_list.csv' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── CSV export helper ────────────────────────────────────────────────────────
async function exportCsv() {
  const bars = await Quizzo.find({}, { __v: 0, _id: 0 }).lean();
  const fields = [
    'BUSINESS','BUSINESS_TAGS','TIME','WEEKDAY','OCCURRENCE_TYPES','NEIGHBORHOOD',
    'ADDRESS_STREET','ADDRESS_UNIT','ADDRESS_CITY','ADDRESS_STATE','ADDRESS_ZIP',
    'PRIZE_1_TYPE','PRIZE_1_AMOUNT','PRIZE_2_TYPE','PRIZE_2_AMOUNT',
    'PRIZE_3_TYPE','PRIZE_3_AMOUNT','HOST','EVENT_TYPE','Full_Address',
    'Latitude','Longitude',
  ];
  const parser = new Parser({ fields });
  const csv    = parser.parse(bars);
  fs.writeFileSync(path.join(__dirname, 'public/assets/quizzo_list.csv'), csv);
}

 
// ═══════════════════════════════════════════════════════════════════════════════
// POOL BAR ROUTES
// ═══════════════════════════════════════════════════════════════════════════════

const poolBarSchema = new mongoose.Schema({
  Name:             String,
  'Yelp Alias':     String,
  Address:          String,
  Neighborhood:    String,
  Latitude:         Number,
  Longitude:        Number,
  Phone:            String,
  Website:          String,
  'Yelp Rating':    Number,
  'Review Count':   Number,
  Price:            String,
  Categories:       [String],
  Monday:           String,
  Tuesday:          String,
  Wednesday:        String,
  Thursday:         String,
  Friday:           String,
  Saturday:         String,
  Sunday:           String,
  Number_of_Tables:   Number,
  Table_Brand:        String,
  Table_Size:         String,
  Table_Type:         String,
  Cost_Per_Game:      Number,
  Cost_Per_Hour:      Number,
  Payment_Model:      String,
  Min_Spend:          Number,
  Reservations:       String,
  Reservation_Link:   String,
  Vibe:               String,
  Noise_Level:        String,
  Crowd_Type:         String,
  Best_Nights:        String,
  Has_Bar:            Boolean,
  Has_Food:           Boolean,
  Has_Happy_Hour:     Boolean,
  Happy_Hour_Details: String,
  Has_TV:             Boolean,
  Has_Other_Games:    String,
  Outdoor_Seating:    Boolean,
  Parking:            String,
  Has_League:         Boolean,
  League_Details:     String,
  Hosts_Tournaments:  Boolean,
  Verified:           { type: Boolean, default: false },
  Last_Verified:      String,
  Notes:              String,
}, { collection: 'pool_bars' });
 
const PoolBar = mappyHourDb.model('PoolBar', poolBarSchema);
 
app.get('/admin/pool-bars', adminAuth, async (req, res) => {
  try {
    const bars = await PoolBar.find({}, { __v: 0 }).lean();
    res.json(bars);
  } catch (err) {
    console.error("Pool Bar Fetch Error:", err); // ADD THIS LINE
    res.status(500).json({ error: err.message });
  }
});

 
// Create a pool bar
app.post('/admin/pool-bars', adminAuth, async (req, res) => {
  try {
    const bar = new PoolBar(req.body);
    await bar.save();
    res.json({ success: true, bar });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
 
// Update a pool bar
app.put('/admin/pool-bars/:id', adminAuth, async (req, res) => {
  try {
    const bar = await PoolBar.findByIdAndUpdate(
      req.params.id,
      { $set: req.body },
      { new: true }
    );
    if (!bar) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true, bar });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
 
// Delete a pool bar
app.delete('/admin/pool-bars/:id', adminAuth, async (req, res) => {
  try {
    const bar = await PoolBar.findByIdAndDelete(req.params.id);
    if (!bar) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
 
// ─── Public Pool Bars route ────────────────────────────────────────────
app.get('/api/pool-bars', async (req, res) => {
  try {
    const bars = await PoolBar.find({}, {
      _id: 0, __v: 0,
      // exclude admin/internal fields from public response
      Verified: 0,
      Last_Verified: 0,
      Notes: 0,
    }).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Pending Pool Bar schemas ─────────────────────────────────────────────────
const pendingPoolBarSchema = new mongoose.Schema({
  name:          { type: String, required: true },
  yelpAlias:     String,
  streetAddress: String,
  city:          String,
  state:         String,
  zip:           String,
  neighborhood:  String,
  Latitude:      Number,
  Longitude:     Number,
  numTables:     Number,
  paymentModel:  String,
  costPerGame:   Number,
  costPerHour:   Number,
  notes:         String,
  yelpData:      mongoose.Schema.Types.Mixed,
  submittedAt:   { type: Date, default: Date.now },
  status:        { type: String, default: 'pending' },
}, { collection: 'pending_pool_bars' });

const pendingPoolBarEditSchema = new mongoose.Schema({
  originalId:   mongoose.Schema.Types.ObjectId,
  originalName: { type: String, required: true },
  changes:      mongoose.Schema.Types.Mixed,
  notes:        String,
  submittedAt:  { type: Date, default: Date.now },
  status:       { type: String, default: 'pending' },
}, { collection: 'pending_pool_bar_edits' });

const PendingPoolBar     = mappyHourDb.model('PendingPoolBar',     pendingPoolBarSchema);
const PendingPoolBarEdit = mappyHourDb.model('PendingPoolBarEdit', pendingPoolBarEditSchema);

app.post('/submit-pool-bar', async (req, res) => {
  try {
    const { name, yelpAlias } = req.body;
    if (!name) return res.status(400).json({ error: 'Bar name is required' });

    let enriched = { ...req.body, name: name.trim() };

    // If no Yelp alias supplied, try to find it automatically
    if (!yelpAlias) {
      try {
        const location = [req.body.city || 'Philadelphia', req.body.state || 'PA'].filter(Boolean).join(', ');
        const searchData = await yelpGet(`/v3/businesses/search?term=${encodeURIComponent(name)}&location=${encodeURIComponent(location)}&categories=bars,restaurants&limit=3`);
        const biz = (searchData.businesses || [])[0];
        if (biz) {
          enriched.yelpAlias = biz.alias;
          // Fetch full details for hours, website, etc.
          const details = await yelpGet(`/v3/businesses/${encodeURIComponent(biz.alias)}`);
          const hoursOpen = details.hours?.[0]?.open || [];
          const dayNames = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
          const hoursMap = {};
          hoursOpen.forEach(slot => {
            const day = dayNames[slot.day];
            const fmt = h => { const hh = parseInt(h.slice(0,2),10); const mm = h.slice(2); return `${hh%12||12}:${mm} ${hh>=12?'PM':'AM'}`; };
            hoursMap[day] = (hoursMap[day] ? hoursMap[day] + ', ' : '') + `${fmt(slot.start)} - ${fmt(slot.end)}`;
          });
          enriched.yelpData = {
            'Yelp Alias':  biz.alias,
            'Yelp Rating': details.rating || biz.rating,
            Phone:         details.display_phone || details.phone || '',
            Website:       details.url || '',
            Price:         details.price || '',
            Categories:    (details.categories || []).map(c => c.title).join(', '),
            ...hoursMap,
          };
        }
      } catch (yelpErr) {
        console.warn('Yelp auto-lookup failed for submission:', yelpErr.message);
      }
    }

    const sub = new PendingPoolBar(enriched);
    await sub.save();
    res.json({ success: true, message: 'Pool bar submission received — thanks!' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/submit-pool-bar-edit', async (req, res) => {
  try {
    const { originalId, originalName, changes, notes } = req.body;
    if (!originalName) return res.status(400).json({ error: 'originalName is required' });
    const edit = new PendingPoolBarEdit({ originalId, originalName, changes, notes });
    await edit.save();
    res.json({ success: true, message: 'Pool bar edit submitted for review — thanks!' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/admin/pending-pool-bars', adminAuth, async (req, res) => {
  try {
    const [submissions, edits] = await Promise.all([
      PendingPoolBar.find({ status: 'pending' }).lean(),
      PendingPoolBarEdit.find({ status: 'pending' }).lean(),
    ]);
    res.json({ submissions, edits });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});


// ─── Pool submission approve/reject ────────────────────────────────────────
app.post('/admin/approve-pool-submission/:id', adminAuth, async (req, res) => {
  try {
    const sub = await PendingPoolBar.findById(req.params.id);
    if (!sub) return res.status(404).json({ error: 'Submission not found' });

    const overrides = req.body || {};
    const yd = sub.yelpData || {};
    const bar = new PoolBar({
      Name:             overrides.name          || sub.name,
      'Yelp Alias':     sub.yelpAlias           || yd['Yelp Alias'] || null,
      Address:          [overrides.streetAddress || sub.streetAddress,
                         overrides.city          || sub.city,
                         overrides.state         || sub.state].filter(Boolean).join(', '),
      Latitude:         sub.Latitude,
      Longitude:        sub.Longitude,
      Neighborhood:     overrides.neighborhood  || sub.neighborhood,
      Phone:            yd.Phone    || null,
      Website:          yd.Website  || null,
      'Yelp Rating':    yd['Yelp Rating'] || null,
      Price:            yd.Price    || null,
      Categories:       yd.Categories ? [yd.Categories] : [],
      Monday:    yd.Monday,    Tuesday:   yd.Tuesday,   Wednesday: yd.Wednesday,
      Thursday:  yd.Thursday,  Friday:    yd.Friday,    Saturday:  yd.Saturday,  Sunday: yd.Sunday,
      Number_of_Tables: overrides.numTables    || sub.numTables || null,
      Payment_Model:    overrides.paymentModel  || sub.paymentModel,
      Cost_Per_Game:    overrides.costPerGame   || sub.costPerGame || null,
      Cost_Per_Hour:    overrides.costPerHour   || sub.costPerHour || null,
      Notes:            sub.notes,
      Verified:         false,
    });
    await bar.save();
    sub.status = 'approved';
    await sub.save();
    res.json({ success: true, insertedId: bar._id });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/admin/reject-pool-submission/:id', adminAuth, async (req, res) => {
  try {
    const sub = await PendingPoolBar.findByIdAndUpdate(
      req.params.id, { status: 'rejected' }, { new: true }
    );
    if (!sub) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/admin/approve-pool-edit/:id', adminAuth, async (req, res) => {
  try {
    const edit = await PendingPoolBarEdit.findById(req.params.id);
    if (!edit) return res.status(404).json({ error: 'Edit not found' });

    const filter = edit.originalId
      ? { _id: edit.originalId }
      : { Name: edit.originalName };

    const updated = await PoolBar.findOneAndUpdate(
      filter, { $set: edit.changes }, { new: true }
    );
    if (!updated) return res.status(404).json({ error: 'Pool bar not found' });

    edit.status = 'approved';
    await edit.save();
    res.json({ success: true, updated });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/admin/reject-pool-edit/:id', adminAuth, async (req, res) => {
  try {
    const edit = await PendingPoolBarEdit.findByIdAndUpdate(
      req.params.id, { status: 'rejected' }, { new: true }
    );
    if (!edit) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Philly Bar Map — public bars route ────────────────────────────────────────────
const barSchema = new mongoose.Schema({
  Name:          String,
  Address:       String,
  Latitude:      Number,
  Longitude:     Number,
  Phone:         String,
  Website:       String,
  'Yelp Rating': Number,
  Price:         String,
  Categories:    mongoose.Schema.Types.Mixed,
  Neighborhood:  String,
  Monday: String, Tuesday: String, Wednesday: String,
  Thursday: String, Friday: String, Saturday: String, Sunday: String,
}, { collection: 'bars', strict: false });

const Bar = mappyHourDb.model('Bar', barSchema);

app.get('/api/bars', async (req, res) => {
  try {
    const bars = await Bar.find(
      { Latitude: { $exists: true, $ne: null }, Longitude: { $exists: true, $ne: null } },
      { _id: 0, __v: 0 }
    ).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Batch meta lookup by bar name — photos, rating, price
// ?names=Bar+One|Bar+Two  (pipe-separated, URI-encoded)
// Returns: { "Bar Name": { photos: [...], rating: 4.5, price: "$$" } }
app.get('/api/bar-photos', async (req, res) => {
  try {
    const names = decodeURIComponent(req.query.names || '')
      .split('|').map(n => n.trim()).filter(Boolean);
    if (!names.length) return res.json({});
    const bars = await Bar.find(
      { Name: { $in: names } },
      { Name: 1, Photos: 1, 'Yelp Rating': 1, Price: 1 }
    ).lean();
    const map = {};
    bars.forEach(b => {
      map[b.Name] = {
        photos: b.Photos || [],
        rating: b['Yelp Rating'] ?? null,
        price:  b.Price || null,
      };
    });
    res.json(map);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/search-bars', searchRateLimit, async (req, res) => {
  try {
    const raw = (req.query.q || '').trim();
    // Require at least 2 real word characters — blocks .* .+ and other regex patterns
    if (raw.length < 2) return res.json([]);
    // Escape all regex special chars so the query is always a literal string search
    const safe = raw.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&');
    const bars = await Bar.find(
      { Name: { $regex: safe, $options: 'i' } },
      {
        _id: 0,          // never expose internal Mongo IDs on public routes
        Name: 1,
        'Yelp Alias': 1,
        Address: 1,
        Latitude: 1,
        Longitude: 1,
        Website: 1,
        'Yelp Rating': 1,
        Neighborhood: 1,
        Neighborhoods: 1,
        Monday: 1, Tuesday: 1, Wednesday: 1,
        Thursday: 1, Friday: 1, Saturday: 1, Sunday: 1,
      }
    ).limit(10).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Yelp Fusion helpers ────────────────────────────────────────────────────
const https = require('https');

// Track current key index for cycling through multiple keys
let yelpKeyIndex = 0;
let cachedYelpKeys = null;

function getYelpKeys() {
  // Return cached keys if already loaded
  if (cachedYelpKeys !== null) return cachedYelpKeys;

  // 1) Comma-separated env var (Railway / production)
  if (process.env.YELP_API_KEYS && process.env.YELP_API_KEYS.includes(',')) {
    cachedYelpKeys = process.env.YELP_API_KEYS.split(',').map(k => k.trim()).filter(Boolean);
    console.log(`[Yelp] Loaded ${cachedYelpKeys.length} keys from YELP_API_KEYS`);
    return cachedYelpKeys;
  }
  
  // 2) Single-key env var
  if (process.env.YELP_API_KEY) {
    cachedYelpKeys = [process.env.YELP_API_KEY];
    console.log('[Yelp] Loaded 1 key from YELP_API_KEY');
    return cachedYelpKeys;
  }
  
  // 3) Local .env file with Python list format
  try {
    const raw = require('fs').readFileSync(require('path').join(__dirname, '.env'), 'utf8');
    const m = raw.match(/yelp_api_keys\s*=\s*\[([\s\S]*?)\]/);
    if (!m) {
      cachedYelpKeys = [];
      return cachedYelpKeys;
    }
    cachedYelpKeys = [...m[1].matchAll(/"([^"]+)"/g)].map(r => r[1]).filter(Boolean);
    console.log(`[Yelp] Loaded ${cachedYelpKeys.length} keys from .env yelp_api_keys`);
    return cachedYelpKeys;
  } catch (e) {
    console.error('[Yelp] Error reading .env:', e.message);
    cachedYelpKeys = [];
    return cachedYelpKeys;
  }
}

function yelpGet(path) {
  const keys = getYelpKeys();
  
  if (!keys.length) {
    console.error('[Yelp] No API keys found in YELP_API_KEYS, YELP_API_KEY, or .env');
    return Promise.reject(new Error('Yelp API key not configured'));
  }
  
  // Cycle through keys on each request
  const key = keys[yelpKeyIndex % keys.length];
  const keyNum = (yelpKeyIndex % keys.length) + 1;
  yelpKeyIndex++;
  
  // Debug: log key status (without exposing the full key)
  if (!key) {
    console.error('[Yelp] Selected key is empty');
    return Promise.reject(new Error('Yelp API key is empty'));
  }
  if (key.length < 100) {
    console.error(`[Yelp] API key ${keyNum} appears invalid (${key.length} chars, expected ~128)`);
    return Promise.reject(new Error(`Yelp API key invalid length: ${key.length} chars`));
  }
  
  console.log(`[Yelp] Using key ${keyNum}/${keys.length}`);
  
  return new Promise((resolve, reject) => {
    const req = https.get(
      { hostname: 'api.yelp.com', path, headers: { Authorization: `Bearer ${key}` } },
      (res) => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => {
          try { resolve(JSON.parse(data)); }
          catch (e) { reject(e); }
        });
      }
    );
    req.on('error', reject);
  });
}

// Yelp search — returns up to 10 matches
app.get('/admin/yelp-search', adminAuth, async (req, res) => {
  try {
    const term     = (req.query.q || '').trim();
    const location = (req.query.location || 'Philadelphia, PA').trim();
    if (!term) return res.json({ businesses: [] });
    const path = `/v3/businesses/search?term=${encodeURIComponent(term)}&location=${encodeURIComponent(location)}&limit=10`;
    console.log('[Yelp search]', path);
    const data = await yelpGet(path);
    if (data.error) {
      console.error('[Yelp search] API error:', data.error);
      return res.status(502).json({ error: data.error.description || JSON.stringify(data.error) });
    }
    console.log(`[Yelp search] ${data.total ?? '?'} total, returning ${(data.businesses || []).length}`);
    res.json(data);
  } catch (err) {
    console.error('[Yelp search] exception:', err.message);
    res.status(500).json({ error: `Yelp search failed: ${err.message}` });
  }
});

// Yelp details by alias
app.get('/admin/yelp-details', adminAuth, async (req, res) => {
  try {
    const alias = (req.query.alias || '').trim();
    if (!alias) return res.status(400).json({ error: 'alias required' });
    const data = await yelpGet(`/v3/businesses/${encodeURIComponent(alias)}`);
    res.json(data);
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// Import Yelp bar into bars collection
app.post('/admin/yelp-import', adminAuth, async (req, res) => {
  try {
    const d = req.body;
    const existing = await Bar.findOne({ 'Yelp Alias': d['Yelp Alias'] });
    if (existing) return res.status(409).json({ error: 'Bar with this Yelp alias already exists', id: existing._id });
    const bar = new Bar(d);
    await bar.save();
    res.json({ success: true, id: bar._id });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// Fetch and store photos for a bar by Yelp Alias
app.post('/admin/fetch-bar-photos', adminAuth, async (req, res) => {
  try {
    const { yelpAlias } = req.body;
    if (!yelpAlias) return res.status(400).json({ error: 'yelpAlias required' });
    
    // Fetch business details from Yelp
    const data = await yelpGet(`/v3/businesses/${encodeURIComponent(yelpAlias)}`);
    const photos = (data.photos || []).slice(0, 3); // Get up to 3 photo URLs
    
    if (!photos.length) {
      return res.json({ success: true, photosCount: 0, message: 'No photos available on Yelp' });
    }
    
    // Update the bar document with photos
    const result = await Bar.findOneAndUpdate(
      { 'Yelp Alias': yelpAlias },
      { Photos: photos },
      { new: true }
    );
    
    if (!result) {
      return res.status(404).json({ error: 'Bar not found' });
    }
    
    res.json({ success: true, photosCount: photos.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Admin — all bars from mappy_hour bars collection (read-only)
app.get('/admin/all-bars', adminAuth, async (req, res) => {
  try {
    const bars = await Bar.find({}, { __v: 0 }).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete photos from a bar document (removes specific URLs from Photos array)
app.patch('/admin/bars/:id/photos', adminAuth, async (req, res) => {
  try {
    const { removeUrls } = req.body; // array of photo URLs to remove
    if (!Array.isArray(removeUrls) || !removeUrls.length) {
      return res.status(400).json({ error: 'removeUrls array required' });
    }
    const bar = await Bar.findByIdAndUpdate(
      req.params.id,
      { $pull: { Photos: { $in: removeUrls } } },
      { new: true }
    );
    if (!bar) return res.status(404).json({ error: 'Bar not found' });
    res.json({ success: true, Photos: bar.Photos });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get quizzo bars that have no fuzzy match in mappy_hour.bars
// Uses simple server-side comparison; client can also call this
app.get('/admin/quizzo-unmatched', adminAuth, async (req, res) => {
  try {
    const [quizzoBars, allBars] = await Promise.all([
      Quizzo.find({}, { BUSINESS: 1, NEIGHBORHOOD: 1, ADDRESS_STREET: 1 }).lean(),
      Bar.find({}, { Name: 1 }).lean(),
    ]);
    const barNames = allBars.map(b => (b.Name || '').toLowerCase().trim());
    // Simple exact-or-contains match; normalise scripts do fuzzy — this is fast
    const unmatched = quizzoBars.filter(q => {
      const name = (q.BUSINESS || '').toLowerCase().trim();
      if (!name) return false;
      return !barNames.some(b => b === name || b.includes(name) || name.includes(b));
    });
    res.json(unmatched);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Add a quizzo bar to the mappy_hour bars collection
app.post('/admin/quizzo-to-bars/:id', adminAuth, async (req, res) => {
  try {
    const qBar = await Quizzo.findById(req.params.id).lean();
    if (!qBar) return res.status(404).json({ error: 'Quizzo bar not found' });
    const existing = await Bar.findOne({ Name: qBar.BUSINESS });
    if (existing) return res.status(409).json({ error: `"${qBar.BUSINESS}" already exists in bars` });
    const address = [qBar.ADDRESS_STREET, qBar.ADDRESS_CITY, qBar.ADDRESS_STATE, qBar.ADDRESS_ZIP]
      .filter(Boolean).join(', ');
    const doc = {
      Name:      qBar.BUSINESS,
      Address:   address || qBar.Full_Address || '',
      Latitude:  qBar.Latitude,
      Longitude: qBar.Longitude,
      Neighborhood: qBar.NEIGHBORHOOD || '',
    };
    const bar = new Bar(doc);
    await bar.save();
    res.json({ success: true, bar });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// QUIZZO BAR ADMIN ROUTES (CRUD)
// ═══════════════════════════════════════════════════════════════════════════════

// Get all quizzo bars (for admin management)
app.get('/admin/quizzo', adminAuth, async (req, res) => {
  try {
    const bars = await Quizzo.find({}, { __v: 0 }).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Create a new quizzo bar
app.post('/admin/quizzo', adminAuth, async (req, res) => {
  try {
    const bar = new Quizzo(req.body);
    await bar.save();
    await exportCsv();
    res.json({ success: true, bar });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update a quizzo bar
app.put('/admin/quizzo/:id', adminAuth, async (req, res) => {
  try {
    const bar = await Quizzo.findByIdAndUpdate(
      req.params.id,
      { $set: req.body },
      { new: true }
    );
    if (!bar) return res.status(404).json({ error: 'Bar not found' });
    await exportCsv();
    res.json({ success: true, bar });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete a quizzo bar
app.delete('/admin/quizzo/:id', adminAuth, async (req, res) => {
  try {
    const bar = await Quizzo.findByIdAndDelete(req.params.id);
    if (!bar) return res.status(404).json({ error: 'Bar not found' });
    await exportCsv();
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// USER AUTH ROUTES
// ═══════════════════════════════════════════════════════════════════════════════

// Returns the authenticated user's profile (decoded token info)
// Front-end calls this after sign-in to confirm the token works server-side
app.get('/api/me', verifyFirebaseToken, (req, res) => {
  const { uid, email, name, picture } = req.firebaseUser;
  res.json({ uid, email, name, picture });
});

// ─── In-memory captcha token store (survives the captcha→password step) ─────
const crypto = require('crypto');
const _captchaTokens = new Map(); // token -> expiry timestamp

// ─── Custom Captcha Validation ─────────────────────────────────────────────
app.post('/api/verify-captcha', (req, res) => {
  const { selectedIndices } = req.body;

  if (!selectedIndices || !Array.isArray(selectedIndices) || selectedIndices.length === 0) {
    console.log('[Captcha] Validation failed: no selection');
    return res.status(400).json({ error: 'No selection made' });
  }

  const correctAnswersRaw = process.env.CAPTCHA_ANSWER || '';
  if (!correctAnswersRaw) {
    console.log('[Captcha] Error: CAPTCHA_ANSWER not configured');
    return res.status(500).json({ error: 'Server configuration error' });
  }

  const correctAnswers = correctAnswersRaw.split(',').map(n => Number(n.trim()));
  const userAnswers = selectedIndices.map(Number);
  const isCorrect = JSON.stringify(correctAnswers) === JSON.stringify(userAnswers);

  if (isCorrect) {
    // Issue a short-lived server-side token instead of relying on a cookie
    const token = crypto.randomBytes(32).toString('hex');
    _captchaTokens.set(token, Date.now() + 30 * 60 * 1000);
    console.log(`[Captcha] ✓ Passed. Issued token (${_captchaTokens.size} tokens in memory)`);
    res.json({ token });
  } else {
    console.log(`[Captcha] ✗ Failed. Expected ${correctAnswers.join(',')}, got ${userAnswers.join(',')}`);
    res.status(401).json({ error: 'Incorrect selection or wrong order. Try again.' });
  }
    // Prune expired tokens
    for (const [t, exp] of _captchaTokens) {
      if (exp < Date.now()) _captchaTokens.delete(t);
    }
    return res.json({ success: true, token });
  }

  res.status(401).json({ error: 'Incorrect selection or wrong order. Try again.' });
});
// ═══════════════════════════════════════════════════════════════════════════════
// SPORTS BARS ROUTES
// ═══════════════════════════════════════════════════════════════════════════════

const sportsTeamSchema = new mongoose.Schema({
  team_name:    String,
  league:       String,   // "NFL" | "NBA" | "MLB" | "NHL" | "MLS" | "Premier League"
  city:         String,
  abbreviation: String,
  logo_url:     String,
  sportsdb_id:  String,
}, { collection: 'sports_teams' });

const sportsBarSchema = new mongoose.Schema({
  Name:          String,
  Address:       String,
  Latitude:      Number,
  Longitude:     Number,
  Phone:         String,
  Website:       String,
  'Yelp Rating': Number,
  'Yelp Alias':  String,
  Price:         String,
  Categories:    mongoose.Schema.Types.Mixed,
  Neighborhood:  String,
  Photos:        [String],
  Monday: String, Tuesday: String, Wednesday: String,
  Thursday: String, Friday: String, Saturday: String, Sunday: String,
  // Sports-specific fields
  philly_affiliates:             [String],
  other_nhl_nba_mlb_nfl_teams:   [String],
  premier_league_team:           String,
  other_soccer_teams:            [String],
  team_ids:                      [mongoose.Schema.Types.ObjectId],
}, { collection: 'sports_bars', strict: false });

const SportsTeam = mappyHourDb.model('SportsTeam', sportsTeamSchema);
const SportsBar  = mappyHourDb.model('SportsBar',  sportsBarSchema);

// GET /api/sports-teams — populate filter dropdowns (optional ?league= filter)
app.get('/api/sports-teams', async (req, res) => {
  try {
    const filter = req.query.league ? { league: req.query.league } : {};
    const teams  = await SportsTeam.find(filter, { _id: 0, __v: 0 }).lean();
    res.json(teams);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/sports-bars — public sports bars endpoint
// Optional query params: ?league=NFL  ?team=Eagles  ?philly=true
app.get('/api/sports-bars', async (req, res) => {
  try {
    const { league, team, philly } = req.query;

    const dbFilter = {
      Latitude:  { $exists: true, $ne: null },
      Longitude: { $exists: true, $ne: null },
    };

    let bars = await SportsBar.find(dbFilter, { __v: 0 }).lean();

    // Post-fetch filtering (team names span multiple array fields)
    if (philly === 'true') {
      bars = bars.filter(b => (b.philly_affiliates || []).length > 0);
    }

    if (team) {
      const q = team.toLowerCase();
      bars = bars.filter(b => {
        const allTeams = [
          ...(b.philly_affiliates || []),
          ...(b.other_nhl_nba_mlb_nfl_teams || []),
          b.premier_league_team,
          ...(b.other_soccer_teams || []),
        ].filter(Boolean);
        return allTeams.some(t => t.toLowerCase().includes(q));
      });
    }

    if (league) {
      // Resolve which team names belong to this league, then filter bars that
      // support at least one of those teams
      const leagueTeams = await SportsTeam.find({ league }, { team_name: 1 }).lean();
      const leagueTeamNames = new Set(leagueTeams.map(t => t.team_name));
      bars = bars.filter(b => {
        const allTeams = [
          ...(b.philly_affiliates || []),
          ...(b.other_nhl_nba_mlb_nfl_teams || []),
          b.premier_league_team,
          ...(b.other_soccer_teams || []),
        ].filter(Boolean);
        return allTeams.some(t => leagueTeamNames.has(t));
      });
    }

    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Admin: CRUD for sports bars
app.get('/admin/sports-bars', adminAuth, async (req, res) => {
  try {
    const bars = await SportsBar.find({}, { __v: 0 }).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.patch('/admin/sports-bars/:id', adminAuth, async (req, res) => {
  try {
    const bar = await SportsBar.findByIdAndUpdate(
      req.params.id, { $set: req.body }, { new: true }
    );
    if (!bar) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true, bar });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Remove a sports bar
app.delete('/admin/sports-bars/:id', adminAuth, async (req, res) => {
  try {
    await SportsBar.findByIdAndDelete(req.params.id);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get all bars that are NOT in sports_bars
app.get('/admin/non-sports-bars', adminAuth, async (req, res) => {
  try {
    const sportsBarIds = await SportsBar.find({}, { _id: 1 }).lean();
    const sportsBarIdSet = new Set(sportsBarIds.map(b => b._id.toString()));
    
    const allBars = await Bar.find({}).lean();
    const filtered = allBars.filter(b => !sportsBarIdSet.has(b._id.toString()));
    
    res.json(filtered);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Add a bar to sports_bars from general bars collection
app.post('/admin/add-sports-bar/:id', adminAuth, async (req, res) => {
  try {
    const bar = await Bar.findById(req.params.id).lean();
    if (!bar) return res.status(404).json({ error: 'Bar not found' });
    
    const newSportsBar = new SportsBar({
      ...bar,
      philly_affiliates:           [],
      other_nhl_nba_mlb_nfl_teams: [],
      premier_league_team:         null,
      other_soccer_teams:          [],
      team_ids:                    [],
    });
    
    const saved = await newSportsBar.save();
    res.json(saved);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────

app.listen(PORT, () => console.log(`Mappy Hour server running on port ${PORT}`));