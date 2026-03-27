/**
 * migrate.js — run once to seed MongoDB from your existing quizzo_list.csv
 * 
 * Usage:
 *   node migrate.js path/to/quizzo_list.csv
 */

require('dotenv').config();
const mongoose = require('mongoose');
const fs       = require('fs');
const path     = require('path');
const { parse } = require('csv-parse/sync');

const csvPath = process.argv[2] || 'public/assets/quizzo_list.csv';

const quizzoSchema = new mongoose.Schema({
  BUSINESS: String, BUSINESS_TAGS: String, TIME: String, WEEKDAY: String,
  OCCURRENCE_TYPES: String, NEIGHBORHOOD: String,
  ADDRESS_STREET: String, ADDRESS_UNIT: String, ADDRESS_CITY: String,
  ADDRESS_STATE: String, ADDRESS_ZIP: String,
  PRIZE_1_TYPE: String, PRIZE_1_AMOUNT: Number,
  PRIZE_2_TYPE: String, PRIZE_2_AMOUNT: Number,
  PRIZE_3_TYPE: String, PRIZE_3_AMOUNT: Number,
  HOST: String, EVENT_TYPE: String, Full_Address: String,
  Latitude: Number, Longitude: Number,
}, { collection: 'Quizzo Bars' });

const Quizzo = mongoose.model('Quizzo', quizzoSchema);

async function migrate() {
  await mongoose.connect(process.env.MONGODB_URI);
  console.log('Connected to MongoDB');

  const csv  = fs.readFileSync(path.resolve(csvPath), 'utf8');
  const rows = parse(csv, { columns: true, skip_empty_lines: true });

  // Map CSV columns → schema fields (CSV uses 'Full Address' with a space)
  const docs = rows.map(r => ({
    ...r,
    Full_Address:   r['Full Address'] || r['Full_Address'],
    PRIZE_1_AMOUNT: parseFloat(r.PRIZE_1_AMOUNT) || null,
    PRIZE_2_AMOUNT: parseFloat(r.PRIZE_2_AMOUNT) || null,
    PRIZE_3_AMOUNT: parseFloat(r.PRIZE_3_AMOUNT) || null,
    Latitude:       parseFloat(r.Latitude)        || null,
    Longitude:      parseFloat(r.Longitude)       || null,
  }));

  await Quizzo.deleteMany({});   // wipe before re-seeding
  const result = await Quizzo.insertMany(docs, { ordered: false });
  console.log(`✓ Inserted ${result.length} bars into MongoDB`);

  await mongoose.disconnect();
}

migrate().catch(err => { console.error(err); process.exit(1); });