import json
import os
import sqlite3
import uuid
from collections import Counter
from flask import Flask, render_template, request

# --- Server & Database Configuration ---
DB_FILENAME = "percy.db"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_FILENAME)


# --- 1. Database Table Setup ---
def init_scheduler_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduling_polls (
            unique_id TEXT PRIMARY KEY,
            sender_email TEXT NOT NULL,
            to_emails TEXT NOT NULL,            -- JSON list of required 'To' emails
            required_votes INTEGER NOT NULL,    -- Count of main 'To' recipients
            free_slots TEXT NOT NULL,           -- JSON list of time slots
            unique_link TEXT NOT NULL,
            votes TEXT NOT NULL DEFAULT '{}',   -- JSON dict: {voter_email: chosen_slot}
            winning_slot TEXT,                  -- Populated once all 'To' recipients vote
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# --- 2. Link Generator Function (Called by Percy) ---
def create_scheduling_link(
    sender_email: str, to_emails: list, free_slots: list
) -> str:
    """Stores the poll with the list/count of required 'To' recipients and returns ONLY the URL."""
    unique_id = str(uuid.uuid4())[:8]
    unique_link = f"http://{SERVER_HOST}:{SERVER_PORT}/vote/{unique_id}"

    # Clean and lowercase required 'To' emails for accurate matching
    clean_to_emails = [e.strip().lower() for e in to_emails if e.strip()]
    required_count = len(clean_to_emails)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scheduling_polls 
        (unique_id, sender_email, to_emails, required_votes, free_slots, unique_link, votes, status)
        VALUES (?, ?, ?, ?, ?, ?, '{}', 'pending')
        """,
        (
            unique_id,
            sender_email,
            json.dumps(clean_to_emails),
            required_count,
            json.dumps(free_slots),
            unique_link,
        ),
    )
    conn.commit()
    conn.close()

    return unique_link


# --- 3. Route to Display Dynamic HTML Page ---
@app.route("/vote/<unique_id>", methods=["GET"])
def show_voting_page(unique_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sender_email, free_slots, status, winning_slot, votes, required_votes, to_emails 
        FROM scheduling_polls WHERE unique_id = ?
        """,
        (unique_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "<h3>Invalid or expired scheduling link.</h3>", 404

    (
        sender_email,
        free_slots_json,
        status,
        winning_slot,
        votes_json,
        required_votes,
        to_emails_json,
    ) = row
    votes_dict = json.loads(votes_json)
    to_list = json.loads(to_emails_json)

    # Count how many required 'To' recipients have voted so far
    to_voted_count = sum(1 for email in to_list if email in votes_dict)

    return render_template(
        "vote.html",
        unique_id=unique_id,
        sender_email=sender_email,
        free_slots=json.loads(free_slots_json),
        status=status,
        winning_slot=winning_slot,
        to_voted_count=to_voted_count,
        required_votes=required_votes,
        just_voted=False,
    )


# --- 4. Route to Record Vote & Check if All 'To' Recipients Have Voted ---
@app.route("/vote/<unique_id>", methods=["POST"])
def submit_vote(unique_id):
    chosen_slot = request.form.get("chosen_slot")
    voter_email = request.form.get("voter_email", "").strip().lower()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sender_email, to_emails, required_votes, free_slots, votes 
        FROM scheduling_polls WHERE unique_id = ?
        """,
        (unique_id,),
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return "<h3>Invalid scheduling link.</h3>", 404

    sender_email, to_emails_json, required_votes, free_slots_json, votes_json = (
        row
    )
    to_list = json.loads(to_emails_json)
    votes_dict = json.loads(votes_json)

    # Record or update this person's vote (works for both 'To' and 'CC' voters)
    votes_dict[voter_email] = chosen_slot

    # Check how many of the required 'To' recipients have now voted
    to_voted_count = sum(1 for email in to_list if email in votes_dict)

    if to_voted_count >= required_votes:
        # All main 'To' people have voted! Pick the most voted slot
        slot_counts = Counter(votes_dict.values())
        winning_slot = slot_counts.most_common(1)[0][0]
        new_status = "ready_to_invite"
    else:
        winning_slot = None
        new_status = "pending"

    cursor.execute(
        """
        UPDATE scheduling_polls
        SET votes = ?, winning_slot = ?, status = ?
        WHERE unique_id = ?
        """,
        (json.dumps(votes_dict), winning_slot, new_status, unique_id),
    )
    conn.commit()
    conn.close()

    return render_template(
        "vote.html",
        unique_id=unique_id,
        sender_email=sender_email,
        free_slots=json.loads(free_slots_json),
        status=new_status,
        winning_slot=winning_slot,
        to_voted_count=to_voted_count,
        required_votes=required_votes,
        just_voted=True,
    )


if __name__ == "__main__":
    init_scheduler_db()
    app.run(debug=True, host=SERVER_HOST, port=SERVER_PORT)