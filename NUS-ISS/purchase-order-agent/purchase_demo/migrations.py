def migrate(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, status TEXT, payload TEXT, reviewed_at TEXT)')
    columns={r[1] for r in connection.execute('PRAGMA table_info(batches)')}
    if 'reviewed_role' not in columns:
        connection.execute('ALTER TABLE batches ADD COLUMN reviewed_role TEXT')
    connection.commit()
