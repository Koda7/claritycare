import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "oscar_guidelines.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            pdf_url TEXT UNIQUE NOT NULL,
            source_page_url TEXT NOT NULL,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER NOT NULL REFERENCES policies(id),
            stored_location TEXT,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            http_status INTEGER,
            error TEXT,
            UNIQUE(policy_id)
        );

        CREATE TABLE IF NOT EXISTS structured_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER NOT NULL REFERENCES policies(id),
            extracted_text TEXT,
            structured_json JSON,
            structured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            llm_model TEXT NOT NULL,
            llm_prompt_hash TEXT,
            validation_error TEXT,
            UNIQUE(policy_id)
        );
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("Database initialized successfully")
    print(f"Location: {DB_PATH}")
    print("=" * 50)
