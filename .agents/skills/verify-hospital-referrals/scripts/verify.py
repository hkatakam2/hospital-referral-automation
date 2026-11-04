#!/usr/bin/env python3
"""Run repository verification and retain evidence outside disposable test state."""

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

FEATURES = {
    "intake": ["tests/test_referrals.py", "tests/test_health.py"],
    "documents": ["tests/test_documents.py", "tests/test_pdf_reader.py"],
    "extraction": ["tests/test_extractions.py"],
    "review": ["tests/test_referrals.py", "tests/test_extractions.py"],
    "persistence": ["tests/test_persistence.py", "tests/test_document_restart.py"],
}
PORTS = (8001, 5174)


def ports_in_use():
    busy = []
    for port in PORTS:
        with socket.socket() as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                busy.append(port)
    return busy


def capture(command, cwd):
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def snapshot(root):
    files = capture(["git", "ls-files", "--cached", "--others", "--exclude-standard"], root)
    digest = hashlib.sha256()
    for name in sorted(set(files.splitlines())):
        path = root / name
        if path.is_file() and not path.is_symlink():
            digest.update(name.encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {
        "testedCommit": capture(["git", "rev-parse", "HEAD"], root),
        "workingTree": capture(["git", "status", "--short"], root),
        "sourceFingerprint": digest.hexdigest(),
    }


def doctor(root):
    """No migrations, fixture writes, installs, service launches, or DB mutations."""
    problems = []
    required = [
        "backend/.venv/bin/python",
        "backend/.venv/bin/pytest",
        "backend/.venv/bin/ruff",
        "frontend/node_modules/@playwright/test/cli.js",
        "frontend/node_modules/.bin/vite",
        "frontend/playwright.config.ts",
        "backend/tests/browser_server.py",
    ]
    problems.extend(
        f"Missing prerequisite: {name}" for name in required if not (root / name).exists()
    )
    problems.extend(
        f"Missing executable: {name}" for name in ("node", "npm", "git") if not shutil.which(name)
    )
    busy = ports_in_use()
    if busy:
        problems.append(f"Verification ports already occupied: {busy}; leave their owners running.")
    if not problems:
        code = """
import os
import psycopg
from sqlalchemy.engine import make_url
from app.config import settings
url = make_url(os.environ.get("TEST_DATABASE_URL", settings.database_url))
try:
    dsn = url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    with psycopg.connect(dsn, connect_timeout=3) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT rolcreatedb OR rolsuper FROM pg_roles WHERE rolname = current_user"
            )
            if not cursor.fetchone()[0]:
                raise RuntimeError("The configured test role needs CREATEDB")
except Exception as error:
    print("PostgreSQL prerequisite failed: " + type(error).__name__
          + "; check local PostgreSQL and the test role")
    raise SystemExit(1)
print("PostgreSQL reachable; test role can create isolated databases")
"""
        result = subprocess.run(
            [str(root / "backend/.venv/bin/python"), "-c", code],
            cwd=root / "backend",
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
        )
        if result.returncode:
            problems.append(
                result.stdout.strip()
                or "Backend import check failed; inspect dependencies privately."
            )
    if not problems:
        browser_check = subprocess.run(
            [
                "node",
                "-e",
                "const fs = require('node:fs'); "
                "const { chromium } = require('@playwright/test'); "
                "process.exit(fs.existsSync(chromium.executablePath()) ? 0 : 1)",
            ],
            cwd=root / "frontend",
            capture_output=True,
            text=True,
        )
        if browser_check.returncode:
            problems.append("Playwright Chromium missing; follow the README browser setup.")
    return {"status": "blocked" if problems else "ready", "problems": problems}


def execute(name, command, cwd, evidence, env=None):
    log = evidence / f"{name}.log"
    started = time.monotonic()
    print(f"Running {name}…", flush=True)
    with log.open("w") as stream:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=600)
        except (KeyboardInterrupt, subprocess.TimeoutExpired):
            # This is only the process group this runner created, never a name/port match.
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            raise
    return {
        "name": name,
        "command": command,
        "cwd": str(cwd),
        "exitCode": code,
        "durationSeconds": round(time.monotonic() - started, 2),
        "log": log.name,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["doctor", "run"])
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--feature", choices=["all", *FEATURES], default="all")
    parser.add_argument(
        "--evidence-dir", type=Path, help="New directory outside the checkout; never overwritten"
    )
    args = parser.parse_args()
    root = args.repo.resolve()
    if (
        not (root / "backend/app/main.py").is_file()
        or not (root / "frontend/package.json").is_file()
    ):
        parser.error("--repo must be the hospital-referral-automation repository root")
    if args.action == "doctor":
        result = doctor(root)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "ready" else 2
    if args.evidence_dir:
        evidence = args.evidence_dir.resolve()
        if evidence == root or root in evidence.parents:
            parser.error(
                "Keep evidence outside the checkout so it cannot change the tested source snapshot"
            )
        evidence.mkdir(parents=True, exist_ok=False)
    else:
        evidence = Path(tempfile.mkdtemp(prefix="referral-verification-"))
    report = {
        **snapshot(root),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "scope": args.feature,
        "commands": [],
        "unverifiedChecks": [],
        "status": "blocked",
    }
    print(f"Evidence: {evidence}", flush=True)
    try:
        result = doctor(root)
        (evidence / "doctor.json").write_text(json.dumps(result, indent=2) + "\n")
        if result["status"] != "ready":
            report["unverifiedChecks"] = [
                "Runtime checks blocked: " + "; ".join(result["problems"])
            ]
            return 2
        python = root / "backend/.venv/bin/python"
        tests = [] if args.feature == "all" else FEATURES[args.feature]
        commands = [
            (
                "backend",
                [
                    str(python),
                    "-m",
                    "pytest",
                    "-q",
                    "--tb=short",
                    f"--junitxml={evidence / 'backend.xml'}",
                    *tests,
                ],
                root / "backend",
            ),
            ("ruff", [str(root / "backend/.venv/bin/ruff"), "check", "."], root / "backend"),
            ("eslint", ["npm", "run", "lint"], root / "frontend"),
            ("build", ["npm", "run", "build"], root / "frontend"),
            ("diff", ["git", "diff", "--check", "HEAD"], root),
        ]
        for name, command, cwd in commands:
            report["commands"].append(execute(name, command, cwd, evidence))
        # Existing tests include both real integration journeys and mocked UI failure probes.
        playwright = root / "frontend/node_modules/@playwright/test/cli.js"
        env = {**os.environ, "PLAYWRIGHT_JSON_OUTPUT_FILE": str(evidence / "browser.json")}
        report["commands"].append(
            execute(
                "browser",
                [
                    "node",
                    str(playwright),
                    "test",
                    "--reporter=list,json",
                    "--trace=on",
                    f"--output={evidence / 'browser'}",
                ],
                root / "frontend",
                evidence,
                env,
            )
        )
        # Add a genuine browser-created intake journey; existing intake UI tests mock API writes.
        skill = Path(__file__).resolve().parents[1]
        config = evidence / "live.config.cjs"
        config.write_text(
            "const { defineConfig } = require("
            + json.dumps(str(root / "frontend/node_modules/@playwright/test"))
            + ");\nmodule.exports = defineConfig("
            + json.dumps(
                {
                    "testDir": str(skill / "scripts"),
                    "testMatch": "live.spec.cjs",
                    "workers": 1,
                    "use": {"baseURL": "http://127.0.0.1:5174", "trace": "on"},
                    "webServer": [
                        {
                            "command": (
                                "../backend/.venv/bin/python ../backend/tests/browser_server.py"
                            ),
                            "cwd": str(root / "frontend"),
                            "url": "http://127.0.0.1:8001/api/health",
                            "reuseExistingServer": False,
                            "gracefulShutdown": {"signal": "SIGTERM", "timeout": 5000},
                        },
                        {
                            "command": "npm run dev -- --host 127.0.0.1 --port 5174",
                            "cwd": str(root / "frontend"),
                            "env": {"API_PROXY_TARGET": "http://127.0.0.1:8001"},
                            "url": "http://127.0.0.1:5174",
                            "reuseExistingServer": False,
                        },
                    ],
                }
            )
            + ");\n"
        )
        env.update(
            {
                "REFERRAL_VERIFY_REPO": str(root),
                "PLAYWRIGHT_JSON_OUTPUT_FILE": str(evidence / "live.json"),
            }
        )
        report["commands"].append(
            execute(
                "live",
                [
                    "node",
                    str(playwright),
                    "test",
                    "--config",
                    str(config),
                    "--reporter=list,json",
                    f"--output={evidence / 'live'}",
                ],
                root / "frontend",
                evidence,
                env,
            )
        )
        for suite in ("browser", "live"):
            summary = evidence / f"{suite}.json"
            if not summary.is_file():
                report["unverifiedChecks"].append(f"Missing {suite} JSON evidence.")
                continue
            stats = json.loads(summary.read_text()).get("stats", {})
            report[f"{suite}Tests"] = stats
            if not stats.get("expected") or stats.get("skipped") or stats.get("flaky"):
                report["unverifiedChecks"].append(f"{suite} had absent, skipped, or flaky tests.")
            if not list((evidence / suite).rglob("trace.zip")):
                report["unverifiedChecks"].append(f"Missing {suite} runtime traces.")
        if not list((evidence / "live").rglob("*.png")):
            report["unverifiedChecks"].append("Missing live browser screenshots.")
        if ports_in_use():
            report["unverifiedChecks"].append(
                "Verification ports remain occupied; inspect ownership before cleanup."
            )
        report["after"] = snapshot(root)
        if report["after"]["sourceFingerprint"] != report["sourceFingerprint"]:
            report["unverifiedChecks"].append(
                "Source changed during verification; rerun the affected checks."
            )
        if (evidence / "backend.xml").is_file():
            suites = ET.parse(evidence / "backend.xml").getroot()
            report["backendTests"] = sum(
                int(suite.get("tests", "0")) for suite in suites.iter("testsuite")
            )
        report["status"] = (
            "passed"
            if all(item["exitCode"] == 0 for item in report["commands"])
            and not report["unverifiedChecks"]
            else "failed"
        )
        return 0 if report["status"] == "passed" else 1
    except (KeyboardInterrupt, subprocess.TimeoutExpired, OSError, ValueError) as error:
        report["unverifiedChecks"].append(
            f"Verification interrupted: {type(error).__name__}; inspect retained logs."
        )
        return 2
    finally:
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        report["evidencePaths"] = sorted(
            str(path.relative_to(evidence)) for path in evidence.rglob("*") if path.is_file()
        )
        (evidence / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Result: {report['status']}; report: {evidence / 'report.json'}", flush=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    raise SystemExit(main())
