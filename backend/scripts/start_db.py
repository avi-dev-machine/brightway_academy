"""Dedicated local PostgreSQL runner using pgserver."""
import atexit
import os
import signal
import sys
import time
from pathlib import Path

import pgserver
import psycopg

DATA_DIR = Path(__file__).resolve().parent.parent / ".local_pgdata"
DATA_DIR.mkdir(parents=True, exist_ok=True)

print(f"Starting local PostgreSQL in {DATA_DIR}...")
server = pgserver.get_server(DATA_DIR, cleanup_mode=None)
base_uri = server.get_uri()
print(f"PostgreSQL running at: {base_uri}")

# Create 'brightway' database
with psycopg.connect(base_uri, autocommit=True) as conn:
    exists = conn.execute("select 1 from pg_database where datname = 'brightway'").fetchone()
    if not exists:
        conn.execute("create database brightway")
        print("Created 'brightway' database.")
    else:
        print("'brightway' database ready.")

brightway_url = base_uri.rsplit("/", 1)[0] + "/brightway"
Path(".db_url").write_text(brightway_url, encoding="utf-8")
print(f"BRIGHTWAY_DATABASE_URL={brightway_url}", flush=True)

# Update backend/.env DATABASE_URL
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    lines = env_file.read_text(encoding="utf-8").splitlines()
    new_lines = []
    replaced = False
    for line in lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={brightway_url}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"DATABASE_URL={brightway_url}")
    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print("Updated backend/.env with DATABASE_URL.")

print("Postgres daemon is running. Press Ctrl+C to stop.", flush=True)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down PostgreSQL...")
    sys.exit(0)
