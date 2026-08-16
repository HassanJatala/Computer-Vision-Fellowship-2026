import sqlite3
import os


def get_connection(db_path="database/events.db"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path="database/events.db"):
    conn = get_connection(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT,
            severity TEXT,
            track_id TEXT,
            object_class TEXT,
            zone_id TEXT,
            start_time REAL,
            end_time REAL,
            duration REAL,
            status TEXT,
            confidence REAL,
            evidence_path TEXT,
            evidence_crop_path TEXT,
            source_id TEXT
        )
    """)
    conn.commit()
    conn.close()