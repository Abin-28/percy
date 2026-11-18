"""Quick test: sort the fake sample mails with the local model, then write a digest.

Run from the project folder:   python test_llm.py
"""
import json
import time
from pathlib import Path

from src.config import MODEL
from src.llm import classify_email, summarize_emails


def main() -> None:
    path = Path(__file__).parent / "data" / "sample_emails.json"
    emails = json.loads(path.read_text(encoding="utf-8"))
    print(f"Model: {MODEL}  |  {len(emails)} fake mails\n")

    sorted_items = []
    for mail in emails:
        start = time.time()
        try:
            answer = classify_email(mail["subject"], mail["body"], mail["sender"])
        except RuntimeError as err:
            print(f"\nERROR: {err}")
            return
        seconds = time.time() - start
        flag = "OK  " if answer["label"] == mail["label"] else "DIFF"
        print(f"[{flag}] {seconds:5.1f}s  expected={mail['label']:<7} got={answer['label']:<7} | {mail['subject']}")
        sorted_items.append({"sender": mail["sender"], "subject": mail["subject"],
                             "label": answer["label"], "reason": answer["reason"]})

    print("\n--- Digest ---")
    try:
        print(summarize_emails(sorted_items))
    except RuntimeError as err:
        print(f"ERROR: {err}")


if __name__ == "__main__":
    main()
