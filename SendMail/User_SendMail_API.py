import os
import sqlite3
import msal
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve credentials securely from environment
TENANT_ID = os.getenv("MS_TENANT_ID")
CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("MS_SENDER_EMAIL")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# Path Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_graph_access_token() -> str:
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )
    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" in result:
        return result["access_token"]
    else:
        print(f"[ERROR] Could not obtain token: {result.get('error_description')}")
        return None


def send_email_ms_graph(token: str, to_email: str, unique_link: str) -> bool:
    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    email_data = {
        "message": {
            "subject": "Your Unique Access Link",
            "body": {
                "contentType": "Text",
                "content": f"Hello,\n\nHere is your unique access link:\n{unique_link}\n\nBest regards,\nPercy AI Team",
            },
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": "true",
    }

    response = requests.post(url, headers=headers, json=email_data)
    if response.status_code == 202:
        print(f"[SUCCESS] MS Graph sent link to {to_email}")
        return True
    else:
        print(f"[ERROR] Failed to send email ({response.status_code}): {response.text}")
        return False


def process_pending_users():
    access_token = get_graph_access_token()
    if not access_token:
        print("Aborting: Unable to authenticate with Microsoft Graph API.")
        return

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
        email_sent = send_email_ms_graph(access_token, mail_id, unique_link)
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