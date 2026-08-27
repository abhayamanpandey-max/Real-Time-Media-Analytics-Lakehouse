"""
validation/genie_validator.py

Genie Validation Harness.

Runs business questions against the Databricks Genie API and compares
results to expected answers. Logs pass/fail and actual SQL to an
append-only accuracy log.

Honest framing: The goal is NOT 100% accuracy. The goal is to measure
accuracy as a number that can improve over time. Each run appends to
validation/accuracy_log.csv so accuracy trends are visible.

Usage:
  # Run all questions
  python validation/genie_validator.py --target dev

  # Run a specific question
  python validation/genie_validator.py --question-id Q001 --target dev

  # Dry run (load questions, validate JSON, don't call Genie API)
  python validation/genie_validator.py --dry-run

Requires:
  DATABRICKS_HOST env var
  DATABRICKS_TOKEN env var
  GENIE_SPACE_ID env var (find in Genie space URL)

Outputs:
  - Console: per-question PASS/FAIL/SKIP with reason
  - Console: final accuracy summary (N passed / M total = X%)
  - validation/accuracy_log.csv: appended with results of this run
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class GenieClient:
    def __init__(self, host: str, token: str, space_id: str):
        self.host = host.rstrip('/')
        self.token = token
        self.space_id = space_id
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def ask(self, question: str, timeout_seconds: int = 60) -> dict:
        url = f"{self.host}/api/2.0/genie/spaces/{self.space_id}/start-conversation"
        payload = {"content": question}
        
        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            conv_id = data.get("conversation_id")
            msg_id = data.get("message_id")
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            return {"status": "error", "answer_text": "", "generated_sql": ""}

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            poll_url = f"{self.host}/api/2.0/genie/spaces/{self.space_id}/conversations/{conv_id}/messages/{msg_id}"
            try:
                poll_resp = requests.get(poll_url, headers=self.headers, timeout=10)
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()
                
                status = poll_data.get("status")
                if status == "COMPLETED":
                    sql = ""
                    for attachment in poll_data.get("attachments", []):
                        if attachment.get("type") == "QUERY":
                            sql = attachment.get("query", "")
                            break
                    return {
                        "status": "success",
                        "answer_text": poll_data.get("content", ""),
                        "generated_sql": sql
                    }
                elif status == "FAILED":
                    return {"status": "error", "answer_text": "Genie failed to answer", "generated_sql": ""}
                
                time.sleep(2)
            except Exception as e:
                logger.error(f"Failed polling message: {e}")
                return {"status": "error", "answer_text": "", "generated_sql": ""}
                
        return {"status": "timeout", "answer_text": "", "generated_sql": ""}

    def get_sql_result(self, sql: str) -> list[dict]:
        # Optional implementation for statement execution
        return []


@dataclass
class ValidationResult:
    question_id: str
    question_text: str
    expected_asset: str
    genie_answer: str
    generated_sql: str
    status: str  # 'PASS' | 'FAIL' | 'SKIP' | 'ERROR'
    notes: str
    duration_seconds: float


def run_validation(questions: list[dict], client: GenieClient, dry_run: bool = False) -> list[ValidationResult]:
    results = []
    
    for q in questions:
        logger.info(f"Processing question {q['id']}")
        start_time = time.time()
        
        if dry_run:
            duration = time.time() - start_time
            results.append(ValidationResult(
                question_id=q["id"],
                question_text=q["canonical"],
                expected_asset=q["expected_asset"],
                genie_answer="",
                generated_sql="",
                status="SKIP",
                notes="Dry run",
                duration_seconds=round(duration, 2)
            ))
            logger.info(f"Question {q['id']} SKIPPED (dry run)")
            continue
            
        ans = client.ask(q["canonical"])
        duration = time.time() - start_time
        
        if ans["status"] in ("error", "timeout"):
            status = "ERROR"
            notes = f"API {ans['status']}"
        else:
            sql = ans.get("generated_sql", "")
            expected_keywords = q.get("expected_sql_contains", [])
            
            missing_keywords = [kw for kw in expected_keywords if kw.lower() not in sql.lower()]
            
            if not missing_keywords:
                status = "PASS"
                notes = "All keywords found"
            else:
                status = "FAIL"
                notes = f"Missing keywords: {', '.join(missing_keywords)}"
                
        res = ValidationResult(
            question_id=q["id"],
            question_text=q["canonical"],
            expected_asset=q["expected_asset"],
            genie_answer=ans.get("answer_text", ""),
            generated_sql=ans.get("generated_sql", ""),
            status=status,
            notes=notes,
            duration_seconds=round(duration, 2)
        )
        results.append(res)
        logger.info(f"Question {q['id']} {status}: {notes}")
        
    return results


def append_to_accuracy_log(results: list[ValidationResult], log_path: Path) -> None:
    file_exists = log_path.exists()
    
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["run_timestamp", "question_id", "question_text", "expected_asset", "status", "generated_sql", "notes", "duration_seconds"])
            
        ts = datetime.now(timezone.utc).isoformat()
        for r in results:
            writer.writerow([
                ts,
                r.question_id,
                r.question_text,
                r.expected_asset,
                r.status,
                r.generated_sql,
                r.notes,
                r.duration_seconds
            ])


def print_summary(results: list[ValidationResult]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    errors = sum(1 for r in results if r.status == "ERROR")
    skipped = sum(1 for r in results if r.status == "SKIP")
    
    logger.info("=== Validation Summary ===")
    logger.info(f"Total: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Skipped: {skipped}")
    
    valid_total = passed + failed
    if valid_total > 0:
        accuracy = (passed / valid_total) * 100
        logger.info(f"Accuracy: {accuracy:.1f}%")
    else:
        logger.info("Accuracy: N/A (no valid results)")
        
    assets = {}
    for r in results:
        if r.status in ("PASS", "FAIL"):
            if r.expected_asset not in assets:
                assets[r.expected_asset] = {"pass": 0, "fail": 0}
            if r.status == "PASS":
                assets[r.expected_asset]["pass"] += 1
            else:
                assets[r.expected_asset]["fail"] += 1
                
    logger.info("=== Asset Breakdown ===")
    for asset, stats in assets.items():
        ast_total = stats["pass"] + stats["fail"]
        ast_acc = (stats["pass"] / ast_total) * 100 if ast_total > 0 else 0
        logger.info(f"{asset}: {stats['pass']}/{ast_total} ({ast_acc:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Genie Validation Harness")
    parser.add_argument("--target", type=str, help="Target environment", default="dev")
    parser.add_argument("--question-id", type=str, help="Specific question ID to run")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    suite_path = base_dir / "genie_question_suite.json"
    log_path = base_dir / "accuracy_log.csv"

    if not suite_path.exists():
        logger.error(f"Suite file not found: {suite_path}")
        sys.exit(1)

    with open(suite_path, 'r', encoding='utf-8') as f:
        suite = json.load(f)

    questions = suite.get("questions", [])
    if args.question_id:
        questions = [q for q in questions if q["id"] == args.question_id]
        if not questions:
            logger.error(f"Question ID {args.question_id} not found")
            sys.exit(1)

    client = None
    if not args.dry_run:
        host = os.environ.get("DATABRICKS_HOST")
        token = os.environ.get("DATABRICKS_TOKEN")
        space_id = os.environ.get("GENIE_SPACE_ID")
        
        if not all([host, token, space_id]):
            logger.error("Missing required env vars: DATABRICKS_HOST, DATABRICKS_TOKEN, GENIE_SPACE_ID")
            sys.exit(1)
            
        client = GenieClient(host, token, space_id)

    results = run_validation(questions, client, args.dry_run)
    
    append_to_accuracy_log(results, log_path)
    
    print_summary(results)

if __name__ == "__main__":
    main()
