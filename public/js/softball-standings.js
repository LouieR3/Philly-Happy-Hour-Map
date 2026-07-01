// Architects' Softball League standings, parsed from WEEK07-ASL-2026.pdf.
// Records are W-L (forfeits count, rain-outs don't; no ties in the data) with the
// team's overall league rank out of 26. Keyed by the opponent names used in
// SOFTBALL_SCHEDULE (server.js) so they match game.opponent exactly.
// Update this file when a newer weekly standings PDF comes out.
window.OPPONENT_STANDINGS = {
  asOf: 'Week 7 · 6/29/2026',
  totalTeams: 26,
  teams: {
    'Voith & Mactavish':  { w: 4, l: 1, rank: 5 },
    'Friday and Friends': { w: 2, l: 4, rank: 18 },
    'Bats':               { w: 4, l: 1, rank: 6 },
    'Team Awesome':       { w: 4, l: 1, rank: 8 },
    'Trane':              { w: 3, l: 2, rank: 12 },
    'Bala Engineers':     { w: 1, l: 4, rank: 24 },
    'JWA':                { w: 2, l: 3, rank: 16 },
    'Perkins Eastman':    { w: 2, l: 3, rank: 13 },
    'Jacobs Engineering': { w: 3, l: 2, rank: 11 },
    'Team Meyer':         { w: 1, l: 4, rank: 20 },
    'Stantec':            { w: 1, l: 4, rank: 23 },
    'Red':                { w: 2, l: 3, rank: 17 },
  },
};
