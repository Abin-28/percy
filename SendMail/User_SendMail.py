import os
import smtplib
import sqlite3
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve credentials securely from environment
SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# Path Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def send_email_smtp(to_email: str, unique_link: str) -> bool:
    subject = "Your Unique Access Link"
    body = f"Hello,\n\nHere is your unique access link:\n{unique_link}\n\nBest regards,\nPercy AI Team"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())
        print(f"[SUCCESS] Link sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email to {to_email}: {e}")
        return False


def process_pending_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, mail_id, unique_link FROM website_user_data WHERE status = 'yes'"
    )
    pending_rows = cursor.fetchall()

    if not pending_rows:
        print("No pending emails to send.")
        conn.close()
        return

    print(f"Found {len(pending_rows)} row(s) to process.")

    for row_id, mail_id, unique_link in pending_rows:
        email_sent = send_email_smtp(mail_id, unique_link)
        if email_sent:
            cursor.execute(
                "UPDATE website_user_data SET status = 'completed' WHERE id = ?",
                (row_id,),
            )
            conn.commit()
            print(f"[UPDATED] Row ID {row_id} status changed to 'completed'.")

    conn.close()


if __name__ == "__main__":
    process_pending_users()