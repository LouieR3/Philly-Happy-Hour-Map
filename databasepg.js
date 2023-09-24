// const {Client} = require('pg')

// const client = new Client({
//     host: "localhost",
//     user: "postgres",
//     port: 5432,
//     password: "P3NNON!G!S",
//     database: "postgres",
// })

// client.connect();

// client.query('SELECT * FROM USERS', (err, res)=>{
//     if (!err){
//         console.log(res.rows)
//     } else {
//         console.log(err.message)
//     }
//     client.end;
// })

const express = require('express');
const { Pool } = require('pg');
const app = express();

const pool = new Pool({
    host: "localhost",
    user: "postgres",
    port: 5432,
    password: "P3NNON!G!S",
    database: "postgres",
});

app.use(express.json());

// Define an endpoint to insert user data into the Users table
// app.post('/addUser', async (req, res) => {
//   try {
//     const { username, email, hashedPassword, first_name, last_name } = req.body;

//     const insertQuery = `
//       INSERT INTO Users (username, email, hashed_password, first_name, last_name)
//       VALUES ($1, $2, $3, $4, $5)
//       RETURNING user_id;
//     `;

//     const result = await pool.query(insertQuery, [username, email, hashedPassword, first_name, last_name]);

//     res.status(201).json({ message: 'User added successfully', userId: result.rows[0].user_id });
//   } catch (error) {
//     console.error('Error inserting user:', error);
//     res.status(500).json({ error: 'Internal Server Error' });
//   }
// });

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});