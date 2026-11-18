# setup_db.py
import sqlite3

DB_FILE = "percy.db"

def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Single Table: 48-Hour Active Scheduling Polls
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Polls (
            poll_id TEXT PRIMARY KEY,
            professor_email TEXT NOT NULL,
            poll_link TEXT NOT NULL,
            proposed_slots TEXT NOT NULL,
            voter_responses TEXT DEFAULT '{}',
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database '{DB_FILE}' successfully initialized with 'Polls' table.")

if __name__ == "__main__":
    initialize_database()