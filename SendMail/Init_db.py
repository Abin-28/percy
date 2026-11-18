import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Create table
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS website_user_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mail_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'yes',
    unique_link TEXT NOT NULL
)
"""
)

# Insert test row (Replace with a real recipient email you can check)
cursor.execute(
    """
INSERT INTO website_user_data (mail_id, unique_link, status)
VALUES (?, ?, ?)
""",
    (
        "anshitasurya@gmail.com",
        "https://yourwebsite.com/access?token=abc123unique",
        "yes",
    ),
)

conn.commit()
conn.close()
print("Database initialized and sample row inserted!")