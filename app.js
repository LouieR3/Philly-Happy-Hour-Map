const express = require('express');
const bodyParser = require('body-parser');
const cors = require("cors");
const pool = require('./databasepg');
const app = express();
const bcrypt = require('bcrypt');

app.use(bodyParser.json());

// API endpoint for checking email/username
app.get('/check-email-username', async (req, res) => {
  const { emailOrUsername } = req.body;

  // Perform a query using the 'pool' connection
  const query = {
    text: 'SELECT * FROM users WHERE email = $1 OR username = $1',
    values: [emailOrUsername],
  };

  try {
    const result = await pool.query(query);

    if (result.rows.length > 0) {
      res.status(200).json({ exists: true });
    } else {
      res.status(200).json({ exists: false });
    }
  } catch (error) {
    console.error('Error checking email/username:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});