"""Measure how good the model is: precision, recall and F1 per label.

Run from the project folder:
    python evaluate.py
    python evaluate.py --model qwen3:4b      (compare another model)

Results are also saved as a JSON file in the results/ folder.
"""
import argparse
import json
import time
from pathlib import Path

from src.config import LABELS, MODEL
from src.llm import classify_email
from src.metrics import accuracy, precision_recall


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL, help="model name as in `ollama list`")
    parser.add_argument("--data", default="data/sample_emails.json", help="labelled mails (JSON)")
    args = parser.parse_args()

    root = Path(__file__).parent
    emails = json.loads((root / args.data).read_text(encoding="utf-8"))
    print(f"Model: {args.model}  |  {len(emails)} mails\n")

    truth, predicted, seconds_list, rows = [], [], [], []
    for mail in emails:
        start = time.time()
        try:
            answer = classify_email(mail["subject"], mail["body"], mail["sender"], model=args.model)
        except RuntimeError as err:
            print(f"ERROR: {err}")
            return
        seconds = time.time() - start
        truth.append(mail["label"])
        predicted.append(answer["label"])
        seconds_list.append(seconds)
        rows.append({"id": mail.get("id"), "expected": mail["label"], "got": answer["label"],
                     "reason": answer["reason"], "seconds": round(seconds, 2)})
        print(f"  {mail.get('id', '?'):>3}  expected={mail['label']:<7} got={answer['label']:<7} {seconds:5.1f}s")

    scores = precision_recall(truth, predicted, LABELS)
    acc = accuracy(truth, predicted)
    avg = sum(seconds_list) / len(seconds_list)

    print(f"\n{'label':<8}{'precision':>10}{'recall':>9}{'f1':>7}{'mails':>7}")
    for lab in LABELS:
        s = scores[lab]
        print(f"{lab:<8}{s['precision']:>10.2f}{s['recall']:>9.2f}{s['f1']:>7.2f}{s['support']:>7}")
    print(f"\nAccuracy: {acc:.2f}   |   average time per mail: {avg:.1f}s")
    unknown = predicted.count("unknown")
    if unknown:
        print(f"Note: {unknown} answer(s) could not be read (counted as wrong).")

    out_dir = root / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"eval_{args.model.replace(':', '_').replace('/', '_')}.json"
    out_file.write_text(json.dumps({"model": args.model, "accuracy": acc, "avg_seconds": avg,
                                    "scores": scores, "rows": rows}, indent=2), encoding="utf-8")
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()
