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
const { Parser } = require('json2csv');
const path       = require('path');
const fs         = require('fs');

const app  = express();
const PORT = process.env.PORT || 3000;

app.use(cors({
  origin: [
    'http://localhost:3000',
    'http://127.0.0.1:5500',
    'https://www.philly-mappy-hour.com',
    'https://philly-mappy-hour.com',
  ]
}));
app.use(express.json());

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

// ─── Simple admin auth middleware ─────────────────────────────────────────────
function adminAuth(req, res, next) {
  const token = req.headers['x-admin-token'];
  if (token && token === process.env.ADMIN_PASSWORD) return next();
  res.status(401).json({ error: 'Unauthorized' });
}

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC ROUTES
// ═══════════════════════════════════════════════════════════════════════════════

// Live quizzo data (replaces CSV fetch in index.html)
app.get('/api/quizzo', async (req, res) => {
  try {
    const bars = await Quizzo.find({}, { __v: 0 }).lean();
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

// Get all pool bars
app.get('/admin/pool-bars', adminAuth, async (req, res) => {
  try {
    const bars = await PoolBar.find({}, { __v: 0 }).lean();
    res.json(bars);
  } catch (err) {
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
    const bars = await PoolBar.find({}, { __v: 0 }).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Pending Pool Bar schemas ─────────────────────────────────────────────────
const pendingPoolBarSchema = new mongoose.Schema({
  name:          { type: String, required: true },
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
    const { name } = req.body;
    if (!name) return res.status(400).json({ error: 'Bar name is required' });
    const sub = new PendingPoolBar({ ...req.body, name: name.trim() });
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
    const bar = new PoolBar({
      Name:            overrides.name          || sub.name,
      Address:         [overrides.streetAddress || sub.streetAddress,
                        overrides.city          || sub.city,
                        overrides.state         || sub.state].filter(Boolean).join(', '),
      Latitude:        sub.Latitude,
      Longitude:       sub.Longitude,
      Neighborhoods:   overrides.neighborhood  || sub.neighborhood,
      Number_of_Tables: overrides.numTables    || sub.numTables || null,
      Payment_Model:   overrides.paymentModel  || sub.paymentModel,
      Cost_Per_Game:   overrides.costPerGame   || sub.costPerGame || null,
      Cost_Per_Hour:   overrides.costPerHour   || sub.costPerHour || null,
      Notes:           sub.notes,
      Verified:        false,
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
      { __v: 0 }
    ).lean();
    res.json(bars);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => console.log(`Mappy Hour server running on port ${PORT}`));