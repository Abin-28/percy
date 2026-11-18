# add_sample_poll.py
import sqlite3
import json
from datetime import datetime, timedelta

conn = sqlite3.connect("percy.db")
cursor = conn.cursor()

now = datetime.now()
expires = now + timedelta(hours=48)

cursor.execute("""
    INSERT OR REPLACE INTO Polls (
        poll_id, professor_email, poll_link, proposed_slots, voter_responses, created_at, expires_at, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
""", (
    "POLL_2026_001",
    "prof.smith@thws.de",
    "https://percy-test.loca.lt/poll?poll_id=POLL_2026_001",
    json.dumps(["2026-11-10T10:00", "2026-11-10T14:00"]),
    json.dumps({"student1@thws.de": ["2026-11-10T10:00"]}),
    now.isoformat(),
    expires.isoformat()
))

conn.commit()
conn.close()
print("Sample poll inserted into 'Polls' table!")