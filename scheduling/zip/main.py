import os
import json
import sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Project Percy Poll Backend")

# Enable CORS so localtunnel and browsers can talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "percy.db"

# --- Request Models ---
class CreatePollRequest(BaseModel):
    poll_id: str
    professor_email: str
    poll_link: str
    proposed_slots: list[str]

class VoteSubmission(BaseModel):
    voter_email: str
    selected_slots: list[str]

# --- 1. Endpoint: Percy Creates a New Poll ---
@app.post("/api/polls/create")
def create_poll(payload: CreatePollRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    now = datetime.now()
    expires = now + timedelta(hours=48)
    
    try:
        cursor.execute("""
            INSERT INTO Polls (
                poll_id, professor_email, poll_link, proposed_slots, voter_responses, created_at, expires_at, status
            ) VALUES (?, ?, ?, ?, '{}', ?, ?, 'ACTIVE')
        """, (
            payload.poll_id,
            payload.professor_email,
            payload.poll_link,
            json.dumps(payload.proposed_slots),
            now.isoformat(),
            expires.isoformat()
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Poll ID already exists.")
    
    conn.close()
    return {
        "status": "success",
        "poll_id": payload.poll_id,
        "expires_at": expires.isoformat(),
        "status": "ACTIVE"
    }

# --- 2. Endpoint: Serves poll.html to Users ---
@app.get("/poll")
def get_poll_page():
    if os.path.exists("poll.html"):
        return FileResponse("poll.html")
    raise HTTPException(status_code=404, detail="poll.html not found")

# --- 3. Endpoint: Saves User Votes to SQLite ---
@app.post("/api/polls/{poll_id}/vote")
def record_vote(poll_id: str, vote: VoteSubmission):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT voter_responses, expires_at, status FROM Polls WHERE poll_id = ?", (poll_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Poll ID not found in database.")

    voter_responses_json, expires_at_str, status = row
    expires_at = datetime.fromisoformat(expires_at_str)
    
    # Enforce 48-hour expiration
    if status != 'ACTIVE' or datetime.now() > expires_at:
        cursor.execute("UPDATE Polls SET status = 'CLOSED' WHERE poll_id = ?", (poll_id,))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=400, detail="This poll has expired (48-hour window closed).")

    # Update voting JSON
    responses_dict = json.loads(voter_responses_json)
    responses_dict[vote.voter_email] = vote.selected_slots

    cursor.execute("UPDATE Polls SET voter_responses = ? WHERE poll_id = ?", 
                   (json.dumps(responses_dict), poll_id))
    conn.commit()
    conn.close()

    return {"status": "success", "message": f"Vote recorded for {vote.voter_email}"}