/**
 * World Cup / Celtic / Stateside data migration  (mappy_hour DB)
 * ---------------------------------------------------------------
 * Run where a VALID MONGODB_URI is available (the value in .env was stale —
 * use the Railway value or a current local .env):
 *
 *     node worldcup-migration.js            # apply changes
 *     node worldcup-migration.js --dry-run  # report only, write nothing
 *
 * Idempotent: re-running is safe. It only sets flags / adds the Fan Fest /
 * renames Xfinity → Stateside, and reports exactly what it matched so you can
 * confirm nothing over-matched (some bar names are short, e.g. "Vita", "Lucy's").
 */
if (process.env.NODE_ENV !== 'production') { try { require('dotenv').config(); } catch (e) {} }
const mongoose = require('mongoose');

const DRY = process.argv.includes('--dry-run');
const URI = (process.env.MONGODB_URI || '').replace('quizzo_bars', 'mappy_hour');
if (!URI) { console.error('MONGODB_URI not set'); process.exit(1); }

const CELTIC_LOGO = 'https://www.clipartmax.com/png/middle/166-1667076_celtic-f-c-logo-glasgow-celtic-logo.png';

const FAN_FEST = {
  Name: 'FIFA World Cup Philly Fan Fest',
  Address: '1 Lemon Hill Drive, Philadelphia, PA 19130',
  Neighborhood: 'Fairmount Park',
  Latitude: 39.9726763213463,
  Longitude: -75.18875920079043,
  world_cup: true,
  is_fan_fest: true,
  register_url: 'https://www.eventim.com/artist/philadelphia-fifa-fan-festival/?affiliate=7FI',
};

// World Cup watch bars to flag. Matched case-insensitively against Name in
// sports_bars first, then bars (copied into sports_bars if only in bars).
const WORLD_CUP_NAMES = [
  'Brauhaus Schmitz', 'Vita', 'Lion Bar', "Sonny's Cocktail Joint", 'Mission Taqueria',
  'Southgate', 'Walnut Garden', 'Fado Irish Pub', "Con Murphy's", 'Tir Na Nog',
  'Misconduct Tavern', "McGillin's Olde Ale House", "Lucy's", "Cavanaugh's Rittenhouse",
  'Top Tomato', 'The Plough', 'Frankford Hall',
];

const rx = (s) => new RegExp('^\\s*' + s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');

// Fields copied when promoting a bars doc into sports_bars.
function toSportsDoc(b, extra) {
  return Object.assign({
    Name: b.Name, Address: b.Address, Latitude: b.Latitude, Longitude: b.Longitude,
    Phone: b.Phone, Website: b.Website, 'Yelp Rating': b['Yelp Rating'], 'Yelp Alias': b['Yelp Alias'],
    Price: b.Price, Categories: b.Categories, Neighborhood: b.Neighborhood, Photos: b.Photos,
    Monday: b.Monday, Tuesday: b.Tuesday, Wednesday: b.Wednesday, Thursday: b.Thursday,
    Friday: b.Friday, Saturday: b.Saturday, Sunday: b.Sunday,
    philly_affiliates: [], other_nhl_nba_mlb_nfl_teams: [], premier_league_team: null,
    other_soccer_teams: [], team_ids: [],
  }, extra || {});
}

(async () => {
  const conn = mongoose.createConnection(URI, { tls: true, tlsAllowInvalidCertificates: true, serverSelectionTimeoutMS: 20000 });
  await conn.asPromise();
  const sports = conn.db.collection('sports_bars');
  const bars   = conn.db.collection('bars');
  const log = (...a) => console.log((DRY ? '[dry] ' : ''), ...a);
  console.log(`\n=== World Cup migration ${DRY ? '(DRY RUN)' : ''} ===\n`);

  // 1) Xfinity Live! → Stateside Live! Philadelphia (+ world cup)
  const xf = await sports.find({ Name: /xfinity live/i }).toArray();
  if (xf.length) {
    for (const d of xf) {
      log(`rename "${d.Name}" → "Stateside Live! Philadelphia" + world_cup`);
      if (!DRY) await sports.updateOne({ _id: d._id }, { $set: { Name: 'Stateside Live! Philadelphia', world_cup: true } });
    }
  } else { log('Xfinity Live! not found in sports_bars (skip rename)'); }

  // 2) The Plough & the Stars → ensure in sports_bars with Celtic FC + logo + world cup
  let plough = await sports.findOne({ Name: rx('The Plough') });
  if (plough) {
    log(`Plough in sports_bars ("${plough.Name}") → add Celtic FC + logo + world_cup`);
    if (!DRY) await sports.updateOne({ _id: plough._id }, {
      $set: { world_cup: true, logo_url: CELTIC_LOGO },
      $addToSet: { other_soccer_teams: 'Celtic FC' },
    });
  } else {
    const pb = await bars.findOne({ Name: rx('The Plough') });
    if (pb) {
      log(`Plough found in bars ("${pb.Name}") → copy into sports_bars with Celtic FC + logo`);
      if (!DRY) await sports.insertOne(toSportsDoc(pb, { world_cup: true, logo_url: CELTIC_LOGO, other_soccer_teams: ['Celtic FC'] }));
    } else { log('!! Plough & the Stars not found in sports_bars OR bars'); }
  }

  // 3) Flag world cup watch bars (sports_bars first, else copy from bars)
  for (const name of WORLD_CUP_NAMES) {
    const inSports = await sports.find({ Name: rx(name) }).toArray();
    if (inSports.length) {
      for (const d of inSports) {
        log(`world_cup: sports_bars "${d.Name}"`);
        if (!DRY) await sports.updateOne({ _id: d._id }, { $set: { world_cup: true } });
      }
      continue;
    }
    const inBars = await bars.find({ Name: rx(name) }).toArray();
    if (inBars.length) {
      for (const b of inBars) {
        log(`world_cup: copy bars "${b.Name}" → sports_bars`);
        if (!DRY) await sports.insertOne(toSportsDoc(b, { world_cup: true }));
      }
      continue;
    }
    log(`!! not found anywhere: "${name}"`);
  }

  // 4) Fan Fest point (upsert by name)
  log(`upsert Fan Fest point "${FAN_FEST.Name}"`);
  if (!DRY) await sports.updateOne({ Name: FAN_FEST.Name }, { $set: FAN_FEST }, { upsert: true });

  console.log('\n=== done ===\n');
  await conn.close();
  process.exit(0);
})().catch(e => { console.error('MIGRATION ERROR:', e.message); process.exit(1); });
