from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import re
import smtplib
import sqlite3
import uuid
from dotenv import load_dotenv

# --- Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "percy.db")
ENV_PATH = os.path.join(BASE_DIR, "creds.env")

# --- Load Gmail App Password Credentials ---
load_dotenv(dotenv_path=ENV_PATH)
GMAIL_USER = os.getenv("GMAIL_SENDER_EMAIL")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")


def parse_slot_to_datetimes(slot_str: str):
    """Converts slot strings into (dt_start, dt_end) datetime objects.

    Supports both:
      - 'Monday, Nov 16 • 10:00 AM - 10:30 AM'
      - '2026-11-16 10:00 - 10:30'
    """
    current_year = datetime.now().year

    # Format A: "Monday, Nov 16 • 10:00 AM - 10:30 AM"
    if "•" in slot_str:
        date_part, time_part = [p.strip() for p in slot_str.split("•", 1)]
        # Strip weekday if present (e.g., "Monday, Nov 16" -> "Nov 16")
        if "," in date_part:
            date_part = date_part.split(",", 1)[1].strip()
        start_str, end_str = [t.strip() for t in time_part.split("-")]

        dt_start = datetime.strptime(
            f"{date_part} {current_year} {start_str}", "%b %d %Y %I:%M %p"
        )
        dt_end = datetime.strptime(
            f"{date_part} {current_year} {end_str}", "%b %d %Y %I:%M %p"
        )
        return dt_start, dt_end

    # Format B: "2026-11-16 10:00 - 10:30"
    date_part, time_part = slot_str.strip().split(" ", 1)
    start_str, end_str = [t.strip() for t in time_part.split("-")]
    dt_start = datetime.strptime(f"{date_part} {start_str}", "%Y-%m-%d %H:%M")
    dt_end = datetime.strptime(f"{date_part} {end_str}", "%Y-%m-%d %H:%M")
    return dt_start, dt_end


def build_ics_file(
    organizer_email: str, attendees: list, winning_slot: str
) -> str:
    """Generates RFC 5545 .ics calendar invitation text for all participants."""
    dt_start, dt_end = parse_slot_to_datetimes(winning_slot)

    ics_start = dt_start.strftime("%Y%m%dT%H%M%S")
    ics_end = dt_end.strftime("%Y%m%dT%H%M%S")
    ics_now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    event_uid = f"{uuid.uuid4()}@percy.scheduler"

    attendee_lines = "\n".join(
        f"ATTENDEE;RSVP=TRUE;ROLE=REQ-PARTICIPANT:mailto:{email}"
        for email in attendees
        if email.lower() != organizer_email.lower()
    )

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Percy AI Assistant//Meeting Scheduler//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:{event_uid}
DTSTAMP:{ics_now}
DTSTART:{ics_start}
DTEND:{ics_end}
SUMMARY:Confirmed Meeting (Scheduled via Percy)
DESCRIPTION:All required participants have voted. Confirmed time: {winning_slot}
ORGANIZER;CN=Organizer:mailto:{organizer_email}
{attendee_lines}
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR"""
    return ics_content


def send_ics_via_gmail(
    organizer_email: str, all_recipients: list, winning_slot: str
) -> bool:
    """Sends the .ics calendar invite via Gmail SMTP using your App Password."""
    if not GMAIL_USER or not GMAIL_PASS:
        print(
            "[ERROR] Missing GMAIL_SENDER_EMAIL or GMAIL_APP_PASSWORD in .env file."
        )
        return False

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Calendar Invite: Meeting Confirmed ({winning_slot})"
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join(all_recipients)

    body_text = (
        f"Hello,\n\n"
        f"All required participants have submitted their availability.\n"
        f"Your meeting is confirmed for:\n\n"
        f"📅 {winning_slot}\n\n"
        f"Please accept the attached calendar invitation (.ics) to add it to your calendar.\n\n"
        f"Best regards,\n"
        f"Percy AI Assistant"
    )
    msg.attach(MIMEText(body_text, "plain"))

    # Create and attach the .ics invite
    ics_payload = build_ics_file(organizer_email, all_recipients, winning_slot)
    ics_part = MIMEBase("text", "calendar", method="REQUEST", name="invite.ics")
    ics_part.set_payload(ics_payload.encode("utf-8"))
    encoders.encode_base64(ics_part)
    ics_part.add_header(
        "Content-Disposition", 'attachment; filename="invite.ics"'
    )
    msg.attach(ics_part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, all_recipients, msg.as_string())
        print(f"[SENT] .ics invite dispatched to: {all_recipients}")
        return True
    except Exception as e:
        print(f"[SMTP ERROR] Could not send invite: {e}")
        return False


def check_and_send_invites():
    """Checks percy.db for polls with status='ready_to_invite' and sends .ics invites."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT unique_id, sender_email, to_emails, votes, winning_slot
        FROM scheduling_polls
        WHERE status = 'ready_to_invite'
    """)
    ready_polls = cursor.fetchall()

    if not ready_polls:
        print("No polls ready for calendar invites (status='ready_to_invite').")
        conn.close()
        return

    for unique_id, sender_email, to_emails_json, votes_json, winning_slot in (
        ready_polls
    ):
        to_list = json.loads(to_emails_json)
        votes_dict = json.loads(votes_json)

        # Combine organizer + required 'To' recipients + any 'CC' voters (deduplicated)
        recipient_set = {sender_email.strip().lower()}
        recipient_set.update(e.strip().lower() for e in to_list)
        recipient_set.update(e.strip().lower() for e in votes_dict.keys())
        all_recipients = sorted(recipient_set)

        print(f"Processing poll {unique_id} | Winning Slot: {winning_slot}")
        success = send_ics_via_gmail(
            sender_email, all_recipients, winning_slot
        )

        if success:
            cursor.execute(
                "UPDATE scheduling_polls SET status = 'completed' WHERE unique_id = ?",
                (unique_id,),
            )
            conn.commit()
            print(f"[COMPLETED] Poll {unique_id} updated to 'completed'.")

    conn.close()


if __name__ == "__main__":
    check_and_send_invites()