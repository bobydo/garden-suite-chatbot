#!/usr/bin/env python3
"""Batch send curated garden suite questions to the running FastAPI /chat endpoint.

Usage (basic):
  python scripts/run_api_batch.py               # uses default questions file
  python scripts/run_api_batch.py --limit 50    # only first 50 questions
  python scripts/run_api_batch.py --mode agent  # (future) reserved flag

The script produces two artifacts in batch_results/:
  - batch_<timestamp>.jsonl  (one JSON object per line)
  - summary_<timestamp>.json (aggregate stats)

Each JSONL record schema:
  {
    "idx": int,
    "category": str,
    "question": str,
    "answer": str,
    "status_code": int,
    "response_time_s": float,
    "error": str | null
  }

Environment variables:
  API_URL  (default: http://127.0.0.1:8000)
  QUESTIONS_FILE (override default questions path)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict

import requests

DEFAULT_QUESTIONS_FILE = os.getenv(
    "QUESTIONS_FILE", "train_questions/edmonton_garden_suite_questions.txt"
)
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT = f"{API_URL.rstrip('/')}/chat"


def load_questions(path: str) -> List[Dict[str, str]]:
    """Replicates loader logic from test_qdrant_questions.py (category headers start with ##)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Questions file not found: {path}")

    questions: List[Dict[str, str]] = []
    current_category = "General"
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("##"):
                current_category = line.replace("##", "").strip() or current_category
                continue
            if line.startswith("#"):
                # Comment line ignore
                continue
            questions.append({
                "category": current_category,
                "question": line,
            })
    return questions


def post_question(question: str):
    payload = {"question": question, "history": []}
    t0 = time.time()
    try:
        resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=90)
        dt = round(time.time() - t0, 3)
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "")
            return answer, resp.status_code, dt, None
        return "", resp.status_code, dt, f"Non-200 status: {resp.status_code}"
    except Exception as e:  # noqa: BLE001
        dt = round(time.time() - t0, 3)
        return "", 0, dt, str(e)


def summarize(records: List[Dict]):
    total = len(records)
    successes = sum(1 for r in records if r["status_code"] == 200 and not r["error"])
    avg_time = round(sum(r["response_time_s"] for r in records) / total, 3) if total else 0.0
    return {
        "total_questions": total,
        "successful": successes,
        "failed": total - successes,
        "success_rate": round((successes / total) * 100, 2) if total else 0.0,
        "average_latency_s": avg_time,
    }


def main():
    parser = argparse.ArgumentParser(description="Batch test /chat endpoint")
    parser.add_argument("--questions", default=DEFAULT_QUESTIONS_FILE, help="Path to questions file")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of questions (0 = all)")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between requests (seconds)")
    args = parser.parse_args()

    try:
        questions = load_questions(args.questions)
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] {e}")
        sys.exit(1)

    if args.limit > 0:
        questions = questions[: args.limit]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = "batch_results"
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, f"batch_{ts}.jsonl")
    summary_path = os.path.join(out_dir, f"summary_{ts}.json")

    print(f"API: {CHAT_ENDPOINT}")
    print(f"Questions: {len(questions)}")
    print(f"Output: {jsonl_path}")
    print("Starting...\n")

    records = []
    with open(jsonl_path, "w", encoding="utf-8") as out:
        for idx, q in enumerate(questions, 1):
            answer, status, latency, error = post_question(q["question"])
            rec = {
                "idx": idx,
                "category": q["category"],
                "question": q["question"],
                "answer": answer,
                "status_code": status,
                "response_time_s": latency,
                "error": error,
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records.append(rec)

            status_str = "OK" if status == 200 and not error else f"ERR({status})"
            print(f"{idx:03d}/{len(questions)} {status_str} {latency:0.2f}s - {q['question'][:70]}")
            if error:
                print(f"    Error: {error}")
            time.sleep(args.delay)

    summary = summarize(records)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\nSummary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\nWrote: {jsonl_path}\n       {summary_path}")


if __name__ == "__main__":
    main()
