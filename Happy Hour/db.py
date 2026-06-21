"""
db.py — shared MongoDB connection for the Happy Hour pipeline.

Reads MONGODB_URI from the environment (or the repo-root .env, same convention
as the other Python tools) and returns the `mappy_hour` database. The repo's
URI points at the `quizzo_bars` DB; we swap to `mappy_hour` like server.js does.

Collections used by the pipeline:
  bars               (existing) — source of venues + Website / Yelp Alias
  happy_hours        (pass 1)   — one doc per bar: HH source link/pdf + times + raw menu text
  happy_hour_items   (pass 2)   — one doc per extracted+normalized drink/food item
"""

import os
import re


def _load_uri():
    uri = os.environ.get('MONGODB_URI')
    if not uri:
        # Fall back to repo-root .env (KEY=VALUE on one line).
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        try:
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    m = re.match(r'\s*MONGODB_URI\s*=\s*(.+)\s*$', line)
                    if m:
                        uri = m.group(1).strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass
    if not uri:
        raise RuntimeError('MONGODB_URI not set (env or ../.env)')
    return uri.replace('quizzo_bars', 'mappy_hour')


def get_db():
    from pymongo import MongoClient  # imported lazily so --help etc. work without pymongo
    client = MongoClient(_load_uri(), tls=True, tlsAllowInvalidCertificates=True,
                         serverSelectionTimeoutMS=20000)
    return client['mappy_hour']
