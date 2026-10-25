import psycopg

conn = psycopg.connect("postgresql://postgres:@127.0.0.1:5432/postgres", autocommit=True)
res = conn.execute("select 1 from pg_database where datname = 'brightway'").fetchone()
if not res:
    conn.execute("create database brightway")
    print("Database 'brightway' created successfully.")
else:
    print("Database 'brightway' already exists.")
conn.close()
