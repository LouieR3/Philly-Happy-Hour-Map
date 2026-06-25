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

// Emails that are granted admin access purely by signing in with Firebase.
// Comma-separated env var overrides the default; matched case-insensitively.
const ADMIN_EMAILS = (process.env.ADMIN_EMAILS || 'lou3@lourodriguez.com')
  .split(',')
  .map(e => e.trim().toLowerCase())
  .filter(Boolean);

// Middleware: verify Firebase ID token sent as Authorization: Bearer <token>.
// admin.auth().verifyIdToken cryptographically validates the JWT signature
// against Google's public keys and rejects tampered or expired tokens, so a
// forged/expired token can never populate req.firebaseUser.
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

// Single source of truth for trusted browser origins — used both by CORS and by
// the admin CSRF origin guard below.
const ALLOWED_ORIGINS = [
  'http://localhost:3000',
  'http://127.0.0.1:5500',
  'https://www.philly-mappy-hour.com',
  'https://philly-mappy-hour.com',
  'https://philly-happy-hour-map-production.up.railway.app',
];

app.use(cors({
  // Reflect only allowlisted origins (instead of a permissive '*'); requests
  // from any other origin get no CORS headers and are blocked by the browser.
  origin: ALLOWED_ORIGINS,
  credentials: true  // Allow cookies in CORS requests
}));
app.use(express.json());
app.use(cookieParser());  // Parse cookies in requests

// ─── NoSQL injection sanitizer ───────────────────────────────────────────────
// VULN: Express/qs parses query strings and JSON bodies into nested objects, so
// a request like `?league[$ne]=x` or `{ "originalBusiness": { "$gt": "" } }`
// reaches Mongoose as a Mongo operator object instead of a plain string,
// letting an attacker bypass filters or match arbitrary documents.
// FIX: recursively strip any object key that begins with '$' or contains '.'
// (the two characters Mongo treats as operators / dotted paths) from every
// request body, query, and params object before any route/DB code runs. Values
// that are meant to be strings stay strings; only operator-shaped keys are removed.
const crypto = require('crypto');

function sanitizeMongo(value) {
  if (Array.isArray(value)) {
    value.forEach(sanitizeMongo);
  } else if (value && typeof value === 'object') {
    for (const key of Object.keys(value)) {
      if (key.startsWith('$') || key.includes('.')) {
        delete value[key];
      } else {
        sanitizeMongo(value[key]);
      }
    }
  }
  return value;
}

app.use((req, res, next) => {
  if (req.body)   sanitizeMongo(req.body);
  if (req.query)  sanitizeMongo(req.query);
  if (req.params) sanitizeMongo(req.params);
  next();
});

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
  submittedBy:    { uid: String, email: String }, // authenticated Firebase user
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
  submittedBy:  { uid: String, email: String }, // authenticated Firebase user
  submittedAt:  { type: Date, default: Date.now },
  status:       { type: String, default: 'pending' },
}, { collection: 'pending_edits' });

const Quizzo      = quizzoDb.model('Quizzo',      quizzoSchema);
const Pending     = quizzoDb.model('Pending',     pendingSchema);
const PendingEdit = quizzoDb.model('PendingEdit', pendingEditSchema);

// ─── Signed admin session tokens ─────────────────────────────────────────────
// VULN: the old scheme stored the literal ADMIN_PASSWORD as the cookie value and
// authorized any request whose `adminToken` cookie equaled the password. An
// attacker who learned (or guessed) the password could set the cookie by hand,
// and more importantly there was no integrity protection — the cookie was just a
// shared secret echoed back. There was also no real per-session expiry tied to
// the token itself.
// FIX: issue a stateless HMAC-signed session token of the form
// `<base64url(payload)>.<base64url(hmac)>`. The payload carries the role and an
// absolute expiry; the signature is computed with a server-only secret. A
// tampered payload or forged signature fails the timing-safe comparison, and an
// expired payload is rejected — so manually crafting a cookie cannot grant access.
const SESSION_SECRET = process.env.SESSION_SECRET
  || (process.env.ADMIN_PASSWORD ? 'mappy:' + process.env.ADMIN_PASSWORD : null)
  || crypto.randomBytes(32).toString('hex');
const ADMIN_SESSION_MS = 24 * 60 * 60 * 1000; // 24h

function signAdminSession(extra = {}) {
  const payload = { role: 'admin', exp: Date.now() + ADMIN_SESSION_MS, ...extra };
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig  = crypto.createHmac('sha256', SESSION_SECRET).update(body).digest('base64url');
  return `${body}.${sig}`;
}

function verifyAdminSession(token) {
  if (!token || typeof token !== 'string') return null;
  const dot = token.indexOf('.');
  if (dot < 1) return null;
  const body = token.slice(0, dot);
  const sig  = token.slice(dot + 1);
  const expected = crypto.createHmac('sha256', SESSION_SECRET).update(body).digest('base64url');
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  // Constant-time compare to avoid signature-timing leaks
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  let payload;
  try { payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf8')); }
  catch { return null; }
  if (payload.role !== 'admin' || !payload.exp || payload.exp < Date.now()) return null;
  return payload;
}

function adminCookieOptions() {
  const isProd = process.env.NODE_ENV === 'production';
  return {
    httpOnly: true,
    secure: isProd,
    sameSite: isProd ? 'None' : 'Lax',
    path: '/',
    maxAge: ADMIN_SESSION_MS,
  };
}

// ─── Admin auth middleware (verifies the signed HttpOnly session cookie) ─────
// CSRF DEFENSE: the admin cookie is SameSite=None in production (required for the
// static-host → Railway cross-origin setup), so the browser would attach it to
// cross-site requests. For state-changing methods we additionally require the
// Origin header — when present — to be in the allowlist, rejecting forged
// cross-site requests. (Cross-origin JSON requests are already preflighted and
// blocked by CORS; this is defense in depth for any non-preflighted method.)
function adminAuth(req, res, next) {
  const session = verifyAdminSession(req.cookies.adminToken);
  if (!session) return res.status(401).json({ error: 'Unauthorized' });

  const origin = req.headers.origin;
  if (req.method !== 'GET' && origin && !ALLOWED_ORIGINS.includes(origin)) {
    return res.status(403).json({ error: 'Cross-origin request blocked' });
  }

  req.admin = session;
  next();
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTHENTICATION ROUTES
// ═══════════════════════════════════════════════════════════════════════════════

// Admin login endpoint (password + captcha fallback path)
app.post('/admin/login', (req, res) => {
  const { password, captchaToken } = req.body;
  if (!password || typeof password !== 'string') return res.status(400).json({ error: 'Password required' });

  // Validate the captcha token issued by /api/verify-captcha
  const expiry = typeof captchaToken === 'string' ? _captchaTokens.get(captchaToken) : undefined;
  if (!captchaToken || expiry === undefined || expiry < Date.now()) {
    if (typeof captchaToken === 'string') _captchaTokens.delete(captchaToken);
    return res.status(401).json({ error: 'Must complete captcha first' });
  }

  // Timing-safe password comparison so login time doesn't leak the password.
  const expected = Buffer.from(process.env.ADMIN_PASSWORD || '');
  const provided = Buffer.from(password);
  const passwordOk = expected.length === provided.length && crypto.timingSafeEqual(expected, provided);
  if (!passwordOk) {
    return res.status(401).json({ error: 'Invalid password' });
  }

  // Consume the captcha token — single use
  _captchaTokens.delete(captchaToken);

  // Issue a signed session token (NOT the password) as an HttpOnly cookie.
  res.cookie('adminToken', signAdminSession({ via: 'password' }), adminCookieOptions());

  const isProd = process.env.NODE_ENV === 'production';
  console.log(`[Auth] Password login successful. Signed admin session issued (secure=${isProd}, hostname=${req.hostname})`);
  res.json({ success: true, message: 'Logged in successfully' });
});

// Admin login via Firebase identity (Google / email). Auto-grants admin to
// designated admin emails (SCOPE Phase 2) without the captcha+password flow.
// Requires a verified Firebase ID token whose email is in ADMIN_EMAILS.
app.post('/admin/firebase-login', verifyFirebaseToken, (req, res) => {
  const email = (req.firebaseUser.email || '').toLowerCase();
  const emailVerified = req.firebaseUser.email_verified;
  if (!email || !emailVerified || !ADMIN_EMAILS.includes(email)) {
    return res.status(403).json({ error: 'This account is not authorized for admin access' });
  }
  res.cookie('adminToken', signAdminSession({ via: 'firebase', email, uid: req.firebaseUser.uid }), adminCookieOptions());
  console.log(`[Auth] Firebase admin login: ${email}`);
  res.json({ success: true, message: 'Admin access granted' });
});

// Admin logout endpoint
app.post('/admin/logout', (req, res) => {
  res.clearCookie('adminToken', { ...adminCookieOptions(), maxAge: undefined });
  res.json({ success: true, message: 'Logged out' });
});

// Check if admin is authenticated (validates the signed session cookie)
app.get('/admin/check-auth', (req, res) => {
  const session = verifyAdminSession(req.cookies.adminToken);
  if (!session) {
    console.log(`[Auth] Check failed: no valid session. Cookies received: ${Object.keys(req.cookies).join(', ') || '(none)'}`);
  }
  res.status(session ? 200 : 401).json({ authenticated: !!session });
});

// Gate the admin login page: report whether a valid admin session already
// exists. (The captcha→password handshake itself is gated by the single-use,
// server-side captcha token, so no forgeable "captchaPassed" cookie is needed.)
app.get('/admin/check-captcha', (req, res) => {
  const session = verifyAdminSession(req.cookies.adminToken);
  if (session) return res.json({ authenticated: true });
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

// Coerce a request value to a trimmed string (defends downstream code against
// non-string inputs that survive sanitization, e.g. numbers/arrays).
function asString(v) {
  if (v === undefined || v === null) return '';
  return String(Array.isArray(v) ? v.join(' ') : v).trim();
}

// Submit a new bar — GATED: only authenticated users may contribute (SCOPE Phase 2)
app.post('/submit-bar', verifyFirebaseToken, async (req, res) => {
  try {
    const { businessName, streetAddress, city, state, zip, neighborhood,
            fullAddress, lat, lng, weekday, time,
            firstPrize, firstPrizeAmount, secondPrize, secondPrizeAmount,
            host, notes } = req.body;

    const name = asString(businessName);
    if (!name) return res.status(400).json({ error: 'Business name is required' });

    const submission = new Pending({
      BUSINESS:       name.toUpperCase(),
      ADDRESS:        asString(fullAddress) || asString(streetAddress),
      ADDRESS_STREET: asString(streetAddress),
      ADDRESS_CITY:   asString(city) || 'Philadelphia',
      ADDRESS_STATE:  asString(state) || 'PA',
      ADDRESS_ZIP:    asString(zip),
      NEIGHBORHOOD:   asString(neighborhood).toUpperCase(),
      Latitude:       lat != null ? Number(lat) : undefined,
      Longitude:      lng != null ? Number(lng) : undefined,
      WEEKDAY:        asString(weekday).toUpperCase(),
      TIME:           asString(time),
      PRIZE_1_TYPE:   asString(firstPrize),
      PRIZE_1_AMOUNT: asString(firstPrizeAmount),
      PRIZE_2_TYPE:   asString(secondPrize),
      PRIZE_2_AMOUNT: asString(secondPrizeAmount),
      HOST:           asString(host).toUpperCase(),
      NOTES:          asString(notes),
      submittedBy:    { uid: req.firebaseUser.uid, email: req.firebaseUser.email },
    });

    await submission.save();
    res.json({ success: true, message: 'Submission received — thanks!' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Submit an edit to an existing bar — GATED: only authenticated users (SCOPE Phase 2)
app.post('/submit-edit', verifyFirebaseToken, async (req, res) => {
  try {
    const { originalBusiness, originalId, changes, notes } = req.body;
    const business = asString(originalBusiness);
    if (!business) return res.status(400).json({ error: 'originalBusiness is required' });

    // `changes` keys are constrained by pendingEditSchema; the global sanitizer
    // already stripped any Mongo-operator keys from the payload.
    const edit = new PendingEdit({
      originalBusiness: business,
      originalId:       asString(originalId) || undefined,
      changes:          (changes && typeof changes === 'object' && !Array.isArray(changes)) ? changes : {},
      notes:            asString(notes),
      submittedBy:      { uid: req.firebaseUser.uid, email: req.firebaseUser.email },
    });
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
  submittedBy:   { uid: String, email: String }, // authenticated Firebase user
  submittedAt:   { type: Date, default: Date.now },
  status:        { type: String, default: 'pending' },
}, { collection: 'pending_pool_bars' });

const pendingPoolBarEditSchema = new mongoose.Schema({
  originalId:   mongoose.Schema.Types.ObjectId,
  originalName: { type: String, required: true },
  changes:      mongoose.Schema.Types.Mixed,
  notes:        String,
  submittedBy:  { uid: String, email: String }, // authenticated Firebase user
  submittedAt:  { type: Date, default: Date.now },
  status:       { type: String, default: 'pending' },
}, { collection: 'pending_pool_bar_edits' });

const PendingPoolBar     = mappyHourDb.model('PendingPoolBar',     pendingPoolBarSchema);
const PendingPoolBarEdit = mappyHourDb.model('PendingPoolBarEdit', pendingPoolBarEditSchema);

// GATED: only authenticated users may contribute (SCOPE Phase 2)
app.post('/submit-pool-bar', verifyFirebaseToken, async (req, res) => {
  try {
    const { name, yelpAlias } = req.body;
    if (!name || typeof name !== 'string') return res.status(400).json({ error: 'Bar name is required' });

    let enriched = { ...req.body, name: name.trim(),
      submittedBy: { uid: req.firebaseUser.uid, email: req.firebaseUser.email } };

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

// GATED: only authenticated users may contribute (SCOPE Phase 2)
app.post('/submit-pool-bar-edit', verifyFirebaseToken, async (req, res) => {
  try {
    const { originalId, originalName, changes, notes } = req.body;
    if (!originalName || typeof originalName !== 'string') return res.status(400).json({ error: 'originalName is required' });
    const edit = new PendingPoolBarEdit({
      originalId: asString(originalId) || undefined,
      originalName,
      changes: (changes && typeof changes === 'object' && !Array.isArray(changes)) ? changes : {},
      notes: asString(notes),
      submittedBy: { uid: req.firebaseUser.uid, email: req.firebaseUser.email },
    });
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

// ─── Happy Hour (Phase 5) ───────────────────────────────────────────────────
// Collections written by the Python pipeline in /Happy Hour:
//   happy_hours       — one doc per bar (source link/pdf + parsed HH times + raw text)
//   happy_hour_items  — one doc per extracted+normalized drink/food item
const HappyHour     = mappyHourDb.model('HappyHour',     new mongoose.Schema({}, { collection: 'happy_hours',      strict: false }));
const HappyHourItem = mappyHourDb.model('HappyHourItem', new mongoose.Schema({}, { collection: 'happy_hour_items', strict: false }));

// Philadelphia-proper bounding box — keeps the feed (and the map) scoped to the
// city instead of the whole metro, which also keeps the payload small.
const PHILLY_BBOX = { minLat: 39.86, maxLat: 40.14, minLng: -75.29, maxLng: -74.94 };

// Public Happy Hour feed: join happy_hours → bars (for lat/lng + neighborhood) →
// happy_hour_items (grouped per bar). Excludes bars whose only "source" is the
// homepage (no real menu/HH link) — those are filtered out until a later pass
// extracts a proper menu. Bars with a real source but no items yet still appear
// (source link + times), so the layer is useful before pass 2 runs.
app.get('/api/happy-hours', async (req, res) => {
  try {
    const [hhs, items, bars] = await Promise.all([
      HappyHour.find({ status: 'found' }).lean(),
      HappyHourItem.find({}, { __v: 0 }).lean(),
      // Fetch all geocoded bars and apply the Philly bbox in JS below. (A Mongo
      // $gte/$lte query here would silently miss rows where Latitude/Longitude
      // are stored as STRINGS — which is what collapsed the feed to one marker.)
      Bar.find(
        { Latitude: { $exists: true, $ne: null }, Longitude: { $exists: true, $ne: null } },
        { Name: 1, 'Yelp Alias': 1, Latitude: 1, Longitude: 1, Neighborhood: 1, _id: 0 }
      ).lean(),
    ]);

    // Index bars by lowercased Name and by Yelp Alias for the join.
    const barByName  = new Map();
    const barByAlias = new Map();
    bars.forEach(b => {
      if (b.Name) barByName.set(String(b.Name).toLowerCase(), b);
      if (b['Yelp Alias']) barByAlias.set(b['Yelp Alias'], b);
    });

    // Group items by bar_name.
    const itemsByBar = new Map();
    items.forEach(it => {
      const k = (it.bar_name || '').toLowerCase();
      if (!itemsByBar.has(k)) itemsByBar.set(k, []);
      itemsByBar.get(k).push({
        category:        it.category || 'other',
        normalized_item: it.normalized_item,
        raw_item:        it.raw_item,
        hh_price:        it.hh_price,
      });
    });

    const inBbox = (la, ln) =>
      la >= PHILLY_BBOX.minLat && la <= PHILLY_BBOX.maxLat &&
      ln >= PHILLY_BBOX.minLng && ln <= PHILLY_BBOX.maxLng;

    // Funnel counters so /api/happy-hours?debug=1 shows where rows drop off.
    const counts = { hhFound: hhs.length, bars: bars.length, afterSourceFilter: 0, joined: 0, inBbox: 0 };
    const unjoined = [];

    const out = [];
    for (const hh of hhs) {
      // Skip "homepage-only" results: no source link, the source IS the plain
      // website, or pass 1 flagged it homepage — none are real HH menus yet.
      if (hh.source_type === 'homepage' || !hh.source_url || hh.source_url === hh.website) continue;
      counts.afterSourceFilter++;

      const bar = (hh.yelp_alias && barByAlias.get(hh.yelp_alias))
        || barByName.get((hh.bar_name || '').toLowerCase());
      if (!bar) { if (unjoined.length < 10) unjoined.push(hh.bar_name); continue; }
      counts.joined++;

      const lat = parseFloat(bar.Latitude);
      const lng = parseFloat(bar.Longitude);
      if (isNaN(lat) || isNaN(lng) || !inBbox(lat, lng)) continue;
      counts.inBbox++;

      const barItems = itemsByBar.get((hh.bar_name || '').toLowerCase()) || [];
      out.push({
        name:          hh.bar_name,
        neighborhood:  bar.Neighborhood || null,
        lat, lng,                                    // numeric, ready for the map/turf
        website:       hh.website || null,
        source_url:    hh.source_url || null,
        source_type:   hh.source_type || null,
        hh_times_raw:  hh.hh_times_raw || null,
        hh_days:       hh.hh_days || null,
        hh_start:      hh.hh_start || null,
        hh_end:        hh.hh_end || null,
        categories:    [...new Set(barItems.map(i => i.category))],
        items:         barItems,
      });
    }

    if (req.query.debug) {
      return res.json({ counts, returned: out.length, unjoinedSample: unjoined, sample: out.slice(0, 3) });
    }
    res.json(out);
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
  if (cachedYelpKeys !== null && cachedYelpKeys.length > 0) return cachedYelpKeys;

  // 1) YELP_API_KEYS env var — one key or comma-separated list (Railway)
  if (process.env.YELP_API_KEYS) {
    const keys = process.env.YELP_API_KEYS.split(',').map(k => k.trim()).filter(Boolean);
    if (keys.length) {
      cachedYelpKeys = keys;
      console.log(`[Yelp] Loaded ${keys.length} key(s) from YELP_API_KEYS`);
      return cachedYelpKeys;
    }
  }

  // 2) YELP_API_KEY singular env var
  if (process.env.YELP_API_KEY) {
    cachedYelpKeys = [process.env.YELP_API_KEY];
    console.log('[Yelp] Loaded 1 key from YELP_API_KEY');
    return cachedYelpKeys;
  }

  // 3) Local .env file — Python list format: yelp_api_keys = ["key1", ...]
  //    or plain KEY=value: YELP_API_KEY=... / YELP_API_KEYS=...
  try {
    const raw = require('fs').readFileSync(require('path').join(__dirname, '.env'), 'utf8');

    const listMatch = raw.match(/yelp_api_keys\s*=\s*\[([\s\S]*?)\]/i);
    if (listMatch) {
      const keys = [...listMatch[1].matchAll(/"([^"]+)"/g)].map(r => r[1]).filter(Boolean);
      if (keys.length) {
        cachedYelpKeys = keys;
        console.log(`[Yelp] Loaded ${keys.length} key(s) from .env yelp_api_keys list`);
        return cachedYelpKeys;
      }
    }

    const kvMatch = raw.match(/^YELP_API_KEYS?\s*=\s*(.+)$/im);
    if (kvMatch) {
      const val = kvMatch[1].trim().replace(/^['"]|['"]$/g, '');
      const keys = val.split(',').map(k => k.trim()).filter(Boolean);
      if (keys.length) {
        cachedYelpKeys = keys;
        console.log(`[Yelp] Loaded ${keys.length} key(s) from .env YELP_API_KEY(S)`);
        return cachedYelpKeys;
      }
    }
  } catch (e) {
    console.error('[Yelp] Error reading .env:', e.message);
  }

  cachedYelpKeys = [];
  return cachedYelpKeys;
}

// Keys that returned 401/403 — revoked or not authorized for the endpoint.
// We skip these on subsequent requests so a single dead key in the pool can't
// keep poisoning ~1-in-N round-robin requests.
const _yelpBadKeys = new Set();

// Single HTTP attempt. Resolves with { status, json } (json is null if the body
// wasn't valid JSON) so the caller can branch on the real HTTP status.
function _yelpRequestOnce(path, key) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      { hostname: 'api.yelp.com', path, headers: { Authorization: `Bearer ${key}` } },
      (res) => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => {
          let json = null;
          try { json = JSON.parse(data); } catch (e) { /* non-JSON body */ }
          resolve({ status: res.statusCode, json });
        });
      }
    );
    req.on('error', reject);
  });
}

// Fetch from Yelp with automatic failover across the key pool.
// BUG FIXED: the old code round-robined ALL keys and ignored the HTTP status,
// so one revoked key (Yelp 401 UNAUTHORIZED_ACCESS_TOKEN) made roughly 1-in-N
// requests fail at random — the intermittent "Yelp Import breaks" symptom.
// Now we skip known-bad keys and retry the next key on 401/403/429.
async function yelpGet(path) {
  const allKeys = getYelpKeys().filter(k => k && k.length >= 100);
  if (!allKeys.length) {
    console.error('[Yelp] No valid API keys found in YELP_API_KEYS, YELP_API_KEY, or .env');
    throw new Error('Yelp API key not configured');
  }

  // Prefer keys not already flagged bad; if every key is flagged, reset and
  // retry them all (a previously-failing key may have been re-enabled).
  let candidates = allKeys.filter(k => !_yelpBadKeys.has(k));
  if (!candidates.length) { _yelpBadKeys.clear(); candidates = allKeys.slice(); }

  let lastError = null;
  for (let attempt = 0; attempt < candidates.length; attempt++) {
    const key = candidates[(yelpKeyIndex++) % candidates.length];
    let resp;
    try {
      resp = await _yelpRequestOnce(path, key);
    } catch (e) {
      lastError = e;                       // network error — try the next key
      continue;
    }

    if (resp.status === 401 || resp.status === 403) {
      _yelpBadKeys.add(key);               // revoked/unauthorized — don't use again
      lastError = new Error(
        (resp.json && resp.json.error && resp.json.error.description) ||
        `Yelp authorization failed (${resp.status})`
      );
      console.warn(`[Yelp] Key rejected (${resp.status}); failing over to next key`);
      continue;
    }
    if (resp.status === 429) {
      lastError = new Error('Yelp rate limit reached');
      continue;                            // a different key may have quota
    }

    // 2xx (or a non-auth API error body the caller inspects via data.error)
    if (resp.json) return resp.json;
    lastError = new Error(`Yelp returned a non-JSON response (status ${resp.status})`);
  }

  throw lastError || new Error('Yelp request failed');
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

// Returns the signed-in user's own contribution history (new bars + edits,
// across both quizzo and pool collections) for the profile page. Scoped to the
// caller's verified uid, so a user can only ever see their own submissions.
app.get('/api/my-submissions', verifyFirebaseToken, async (req, res) => {
  try {
    const uid = req.firebaseUser.uid;
    const by  = { 'submittedBy.uid': uid };
    const [bars, edits, poolBars, poolEdits] = await Promise.all([
      Pending.find(by).sort({ submittedAt: -1 }).lean(),
      PendingEdit.find(by).sort({ submittedAt: -1 }).lean(),
      PendingPoolBar.find(by).sort({ submittedAt: -1 }).lean(),
      PendingPoolBarEdit.find(by).sort({ submittedAt: -1 }).lean(),
    ]);
    const norm = (items, kind) => items.map(i => ({
      kind,                                                  // new-bar | edit | new-pool-bar | pool-edit
      name:        i.BUSINESS || i.name || i.originalBusiness || i.originalName || '—',
      status:      i.status || 'pending',
      submittedAt: i.submittedAt,
    }));
    const submissions = [
      ...norm(bars, 'new-bar'),
      ...norm(poolBars, 'new-pool-bar'),
      ...norm(edits, 'edit'),
      ...norm(poolEdits, 'pool-edit'),
    ].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt));
    res.json({ submissions });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── In-memory captcha token store (survives the captcha→password step) ─────
// `crypto` is required once near the top of the file.
const _captchaTokens = new Map(); // token -> expiry timestamp

// ─── Custom Captcha Validation ─────────────────────────────────────────────
app.post('/api/verify-captcha', (req, res) => {
  const { selectedIndices } = req.body;

  if (!selectedIndices || !Array.isArray(selectedIndices) || selectedIndices.length === 0) {
    return res.status(400).json({ error: 'No selection made' });
  }

  const correctAnswersRaw = process.env.CAPTCHA_ANSWER || '';
  if (!correctAnswersRaw) {
    return res.status(500).json({ error: 'Server configuration error' });
  }

  const correctAnswers = correctAnswersRaw.split(',').map(n => Number(n.trim()));
  const userAnswers = selectedIndices.map(Number);
  const isCorrect = JSON.stringify(correctAnswers) === JSON.stringify(userAnswers);

  if (isCorrect) {
    // Issue a short-lived server-side token instead of relying on a cookie
    const token = crypto.randomBytes(32).toString('hex');
    _captchaTokens.set(token, Date.now() + 30 * 60 * 1000);
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
    // Coerce query params to strings — the global sanitizer strips Mongo
    // operators, and asString guards against any residual non-string shape.
    const league = asString(req.query.league);
    const team   = asString(req.query.team);
    const philly = asString(req.query.philly);

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

// ─── Softball League ─────────────────────────────────────────────────────────

const playerStatSchema = new mongoose.Schema({
  name:  { type: String, required: true },
  AB:    { type: Number, default: 0 },
  H:     { type: Number, default: 0 },
  '1B':  { type: Number, default: 0 },
  '2B':  { type: Number, default: 0 },
  '3B':  { type: Number, default: 0 },
  HR:    { type: Number, default: 0 },
  RBI:   { type: Number, default: 0 },
  R:     { type: Number, default: 0 },
  TB:    { type: Number },
  AVG:   { type: Number },
  SLG:   { type: Number },
  OPS:   { type: Number },
}, { _id: false });

const softballGameSchema = new mongoose.Schema({
  game_number:    { type: Number },
  date:           { type: Date },
  opponent:       { type: String },
  our_score:      { type: Number },
  opponent_score: { type: Number },
  result:         { type: String },
  players:        [playerStatSchema],
}, { collection: 'softball_games' });

const SoftballGame = mappyHourDb.model('SoftballGame', softballGameSchema);

const SOFTBALL_SCHEDULE = [
  { game_number:  1, date: new Date('2026-05-13'), opponent: 'Voith & Mactavish'  },
  { game_number:  2, date: new Date('2026-05-20'), opponent: 'Friday and Friends'  },
  { game_number:  3, date: new Date('2026-05-27'), opponent: 'Bats'                },
  { game_number:  4, date: new Date('2026-06-03'), opponent: 'Team Awesome'        },
  { game_number:  5, date: new Date('2026-06-10'), opponent: 'Trane'               },
  { game_number:  6, date: new Date('2026-06-17'), opponent: 'Bala Engineers'      },
  { game_number:  7, date: new Date('2026-06-24'), opponent: 'JWA'                 },
  { game_number:  8, date: new Date('2026-07-01'), opponent: 'Perkins Eastman'     },
  { game_number:  9, date: new Date('2026-07-08'), opponent: 'Jacobs Engineering'  },
  { game_number: 10, date: new Date('2026-07-15'), opponent: 'Team Meyer'          },
  { game_number: 11, date: new Date('2026-07-22'), opponent: 'Stantec'             },
  { game_number: 12, date: new Date('2026-07-29'), opponent: 'Red'                 },
];

async function seedSoftballSchedule() {
  for (const game of SOFTBALL_SCHEDULE) {
    const exists = await SoftballGame.findOne({ game_number: game.game_number });
    if (!exists) {
      await new SoftballGame({
        game_number: game.game_number,
        date:        game.date,
        opponent:    game.opponent,
        players:     [],
      }).save();
    }
  }
  console.log('[Softball] Schedule ready');
}

mappyHourDb.once('open', () => seedSoftballSchedule().catch(console.error));

function calcPlayerStats(p) {
  const AB  = p.AB  || 0;
  const H   = p.H   || 0;
  const dbl = p['2B'] || 0;
  const tpl = p['3B'] || 0;
  const hr  = p.HR  || 0;
  const sgl = Math.max(0, H - dbl - tpl - hr);
  const TB  = sgl + 2 * dbl + 3 * tpl + 4 * hr;
  const AVG = AB > 0 ? parseFloat((H / AB).toFixed(3))  : 0;
  const SLG = AB > 0 ? parseFloat((TB / AB).toFixed(3)) : 0;
  const OPS = parseFloat((AVG + SLG).toFixed(3));
  return {
    name: p.name, AB, H,
    '1B': sgl, '2B': dbl, '3B': tpl, HR: hr,
    RBI: p.RBI || 0, R: p.R || 0,
    TB, AVG, SLG, OPS,
  };
}

app.get('/api/softball/games', async (req, res) => {
  try {
    const games = await SoftballGame.find({}).sort({ game_number: 1 }).lean();
    res.json(games);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// VULN: this /admin/ route was missing the adminAuth gate, so anyone could
// create softball games. FIX: require a valid admin session like the sibling
// delete route.
app.post('/admin/softball/games', adminAuth, async (req, res) => {
  try {
    const { date, opponent, our_score, opponent_score, result, players } = req.body;
    const count = await SoftballGame.countDocuments();
    const game = new SoftballGame({
      game_number:    count + 1,
      date:           date || new Date(),
      opponent:       opponent || 'TBD',
      our_score:      Number(our_score) || 0,
      opponent_score: Number(opponent_score) || 0,
      result:         result || 'W',
      players:        (players || []).map(calcPlayerStats),
    });
    const saved = await game.save();
    res.json(saved);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT — update stats for a pre-set game. Now admin-gated: only a valid signed
// admin session (minted via /admin/firebase-login for an ADMIN_EMAILS account,
// i.e. lou3@lourodriguez.com) may write. adminAuth also enforces the Origin
// check on this non-GET request.
app.put('/api/softball/games/:id', adminAuth, async (req, res) => {
  try {
    const { our_score, opponent_score, result, players } = req.body;
    const update = {
      our_score:      our_score      != null ? Number(our_score)      : null,
      opponent_score: opponent_score != null ? Number(opponent_score) : null,
      result:         result         || null,
      players:        (players || []).map(calcPlayerStats),
    };
    const updated = await SoftballGame.findByIdAndUpdate(req.params.id, update, { new: true }).lean();
    if (!updated) return res.status(404).json({ error: 'Game not found' });
    res.json(updated);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/softball/season', async (req, res) => {
  try {
    const games = await SoftballGame.find({}).lean();
    // Games with stats, plus WF (forfeit win) and RO (rain out)
    const resolved = games.filter(g => g.result && (
      (g.players && g.players.length > 0) || g.result === 'WF' || g.result === 'RO'
    ));
    if (!resolved.length) return res.json({ players: [], record: { W: 0, L: 0, T: 0 }, run_diff: 0 });

    // Only stat-bearing games count for player aggregation
    const played = resolved.filter(g => g.players && g.players.length > 0);

    const record = { W: 0, L: 0, T: 0 };
    let run_diff = 0;
    for (const g of resolved) {
      if (g.result === 'WF') { record.W++; run_diff += 7; continue; }
      if (g.result === 'RO') continue; // rain out: no record, no run diff
      if (g.result in record) record[g.result]++;
      run_diff += (g.our_score || 0) - (g.opponent_score || 0);
    }

    const playerMap = {};
    for (const g of played) {
      for (const p of g.players) {
        if (!playerMap[p.name]) {
          playerMap[p.name] = { name: p.name, G: 0, AB: 0, H: 0, '1B': 0, '2B': 0, '3B': 0, HR: 0, RBI: 0, R: 0 };
        }
        const pm = playerMap[p.name];
        pm.G     += 1;   // one roster row per game = one game played
        pm.AB    += p.AB    || 0;
        pm.H     += p.H     || 0;
        pm['1B'] += p['1B'] || 0;
        pm['2B'] += p['2B'] || 0;
        pm['3B'] += p['3B'] || 0;
        pm.HR    += p.HR    || 0;
        pm.RBI   += p.RBI   || 0;
        pm.R     += p.R     || 0;
      }
    }

    const players = Object.values(playerMap).map(p => {
      const TB  = p['1B'] + 2 * p['2B'] + 3 * p['3B'] + 4 * p.HR;
      const AVG = p.AB > 0 ? p.H / p.AB : 0;
      const SLG = p.AB > 0 ? TB / p.AB  : 0;
      const RC  = p.AB > 0 ? p.H * (TB / p.AB) : 0;
      return { ...p, TB, AVG, SLG, OPS: AVG + SLG, RC };
    });

    // WAR — exact logic from softball.py
    const MINIMUM_NUMBER_ABS = 6;
    const eligible = players.filter(p => p.AB >= MINIMUM_NUMBER_ABS);

    let replacement_rc_per_ab = 0;
    if (eligible.length >= 1) {
      const sorted = [...eligible].sort((a, b) => a.AVG - b.AVG);
      const pool   = sorted.slice(0, Math.min(5, sorted.length));
      const replacement_avg      = pool.reduce((s, p) => s + p.AVG, 0) / pool.length;
      const pool_total_tb        = pool.reduce((s, p) => s + p.TB,  0);
      const pool_total_ab        = pool.reduce((s, p) => s + p.AB,  0);
      const replacement_tb_per_ab = pool_total_ab > 0 ? pool_total_tb / pool_total_ab : 0;
      replacement_rc_per_ab       = replacement_avg * replacement_tb_per_ab;
    }

    const result_players = players.map(p => {
      const Replacement_RC = p.AB * replacement_rc_per_ab;
      const WAR = eligible.length >= 1
        ? parseFloat(((p.RC - Replacement_RC) / 12).toFixed(2))
        : null;
      return {
        name:  p.name,
        G:     p.G,
        AB:    p.AB,
        H:     p.H,
        '2B':  p['2B'],
        '3B':  p['3B'],
        HR:    p.HR,
        RBI:   p.RBI,
        R:     p.R,
        TB:    p.TB,
        AVG:   parseFloat(p.AVG.toFixed(3)),
        SLG:   parseFloat(p.SLG.toFixed(3)),
        OPS:   parseFloat((p.AVG + p.SLG).toFixed(3)),
        RC:    parseFloat(p.RC.toFixed(2)),
        WAR,
      };
    });

    res.json({ players: result_players, record, run_diff });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/admin/softball/games/:id', adminAuth, async (req, res) => {
  try {
    const deleted = await SoftballGame.findByIdAndDelete(req.params.id);
    if (!deleted) return res.status(404).json({ error: 'Game not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─────────────────────────────────────────────────────────────────────────────

app.listen(PORT, () => console.log(`Mappy Hour server running on port ${PORT}`));