#!/usr/bin/env python3
"""External JMeter runner example for Automation Platform.

This script is intended to run on a trusted CI agent or tester machine that has
JMeter installed. It reads one platform task config, executes the configured
JMX file, uploads performance metrics, and optionally uploads the HTML report.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from uuid import uuid4


def request_json(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    """Call a platform JSON API with the external automation token."""
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Automation-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {detail}") from exc


def upload_file(url: str, token: str, file_path: Path, fields: dict[str, str]) -> dict:
    """Upload one multipart/form-data file using only the Python standard library."""
    boundary = f"----automation-platform-{uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode("utf-8"),
            b"\r\n",
        ])
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode(),
        b"Content-Type: application/octet-stream\r\n\r\n",
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    request = urllib.request.Request(
        url,
        data=b"".join(chunks),
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Automation-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} uploading {file_path}: {detail}") from exc


def jmeter_property_args(config: dict) -> list[str]:
    """Convert environment and task variables into JMeter -J key=value args."""
    environment = config.get("environment") or {}
    variables = {
        **(environment.get("variables") or {}),
        **((config.get("jmeter") or {}).get("variables") or {}),
    }
    if environment.get("base_url"):
        variables.setdefault("base_url", environment["base_url"])
    args: list[str] = []
    for key, value in variables.items():
        args.append(f"-J{key}={value}")
    return args


def run_jmeter(config: dict, jmeter_bin: str, dry_run: bool) -> int:
    """Run JMeter in non-GUI mode using metadata from the platform task config."""
    jmeter = config.get("jmeter") or {}
    jmx_path = Path(jmeter.get("jmx_path") or "")
    if not jmx_path:
        raise RuntimeError("config.jmeter.jmx_path is required")
    jtl_path = Path(jmeter.get("jtl_path") or "reports/jmeter/result.jtl")
    report_dir = Path(jmeter.get("report_dir") or "reports/jmeter/html")
    jtl_path.parent.mkdir(parents=True, exist_ok=True)
    if report_dir.exists():
        shutil.rmtree(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    command = [
        jmeter_bin,
        "-n",
        "-t",
        str(jmx_path),
        "-l",
        str(jtl_path),
        "-e",
        "-o",
        str(report_dir),
        *jmeter_property_args(config),
    ]
    print("JMeter command:", " ".join(command))
    if dry_run:
        return 0
    return subprocess.run(command, check=False).returncode


def parse_jtl_metrics(jtl_path: Path) -> dict:
    """Parse common JMeter CSV JTL fields into platform performance metrics."""
    if not jtl_path.exists():
        return {}
    elapsed_values: list[float] = []
    failures = 0
    started_at = None
    finished_at = None
    with jtl_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            elapsed = float(row.get("elapsed") or 0)
            timestamp = int(float(row.get("timeStamp") or 0))
            success = str(row.get("success", "")).lower() == "true"
            elapsed_values.append(elapsed)
            failures += 0 if success else 1
            started_at = timestamp if started_at is None else min(started_at, timestamp)
            finished_at = max(finished_at or timestamp, timestamp + int(elapsed))
    if not elapsed_values:
        return {}
    elapsed_values.sort()
    duration_seconds = max(((finished_at or 0) - (started_at or 0)) / 1000, 1)
    return {
        "samples": len(elapsed_values),
        "successes": len(elapsed_values) - failures,
        "failures": failures,
        "avg_ms": round(sum(elapsed_values) / len(elapsed_values), 2),
        "p95_ms": percentile(elapsed_values, 0.95),
        "p99_ms": percentile(elapsed_values, 0.99),
        "error_rate": round(failures / len(elapsed_values) * 100, 4),
        "tps": round(len(elapsed_values) / duration_seconds, 4),
        "tool": "jmeter",
    }


def percentile(values: list[float], ratio: float) -> float:
    """Return a nearest-rank percentile value."""
    index = max(0, min(len(values) - 1, int(round(ratio * len(values) + 0.5)) - 1))
    return round(values[index], 2)


def zip_report_dir(report_dir: Path) -> Path | None:
    """Zip a JMeter HTML report directory for platform attachment upload."""
    if not report_dir.exists() or not report_dir.is_dir():
        return None
    zip_path = report_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in report_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(report_dir.parent))
    return zip_path


def main() -> int:
    """Run the full read-config, execute, upload-result, upload-attachment flow."""
    parser = argparse.ArgumentParser(description="Run a JMeter task from Automation Platform metadata.")
    parser.add_argument("--base-url", required=True, help="Platform base URL, for example http://111.229.178.141")
    parser.add_argument("--task-code", required=True, help="Platform test task code")
    parser.add_argument("--token", default=os.getenv("EXTERNAL_TRIGGER_TOKEN"), help="External automation token")
    parser.add_argument("--jmeter-bin", default=os.getenv("JMETER_BIN", "jmeter"), help="JMeter executable")
    parser.add_argument("--dry-run", action="store_true", help="Read config and print command without running JMeter")
    args = parser.parse_args()
    if not args.token:
        raise RuntimeError("EXTERNAL_TRIGGER_TOKEN is required")

    base_url = args.base_url.rstrip("/")
    encoded_code = urllib.parse.quote(args.task_code, safe="")
    config = request_json("GET", f"{base_url}/api/v1/test-tasks/by-code/{encoded_code}/config", args.token)
    exit_code = run_jmeter(config, args.jmeter_bin, args.dry_run)
    if args.dry_run:
        print(json.dumps({"status": "dry-run", "task_code": args.task_code}, ensure_ascii=False, indent=2))
        return 0
    jmeter = config.get("jmeter") or {}
    jtl_path = Path(jmeter.get("jtl_path") or "reports/jmeter/result.jtl")
    report_dir = Path(jmeter.get("report_dir") or "reports/jmeter/html")
    metrics = parse_jtl_metrics(jtl_path)
    status = "passed" if exit_code == 0 and (metrics.get("failures") or 0) == 0 else "failed"
    upload = request_json(
        "POST",
        config["callbacks"]["result_upload_url"],
        args.token,
        {
            "trigger_type": "ci",
            "environment_id": config.get("environment_id"),
            "summary": {"source": "tools/jmeter_external_runner.py", "jtl_path": str(jtl_path), "exit_code": exit_code},
            "results": [{
                "result_type": "performance",
                "status": status,
                "metrics": metrics,
                "logs": f"JMeter exit_code={exit_code}, jtl={jtl_path}",
                "error": None if status == "passed" else "JMeter execution failed or contains failed samples",
                "environment_id": config.get("environment_id"),
            }],
        },
    )
    batch_id = upload.get("batch", {}).get("id")
    report_zip = zip_report_dir(report_dir)
    if batch_id and report_zip:
        upload_file(config["callbacks"]["attachment_upload_url"], args.token, report_zip, {"batch_id": str(batch_id), "attachment_type": "performance_report"})
    print(json.dumps({"status": status, "batch_id": batch_id, "metrics": metrics}, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
