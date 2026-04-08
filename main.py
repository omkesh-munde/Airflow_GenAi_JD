from __future__ import annotations

import argparse
import shutil
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from agents import route_agent
from classifier import classify_error
from config import SETTINGS
from log_watcher import LogWatcher, extract_error_block


def _print_structured(
    *,
    file_path: Path,
    error_type: str,
    root_cause: str,
    fix: str,
    severity: str,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 24)
    print(f"Timestamp: {ts}")
    print(f"File: {file_path.name}")
    print(f"Error Type: {error_type}")
    print()
    print("Root Cause:")
    print(root_cause.strip() if root_cause else "(empty)")
    print()
    print("Fix:")
    print(fix.strip() if fix else "(empty)")
    print()
    print("Severity:")
    print(severity.strip() if severity else "(empty)")
    print("===")
    sys.stdout.flush()


def _handle_new_log(file_path: Path, log_text: str) -> None:
    if not log_text or not log_text.strip():
        _print_structured(
            file_path=file_path,
            error_type="unknown",
            root_cause="Log file is empty.",
            fix="Ensure the logging system writes content to the file.",
            severity="Low",
        )
        return

    error_block = extract_error_block(log_text)
    if not error_block:
        _print_structured(
            file_path=file_path,
            error_type="unknown",
            root_cause="No error keywords found (ERROR / Traceback / Exception).",
            fix="No action needed. If this is unexpected, expand error detection rules.",
            severity="Low",
        )
        return

    error_type = classify_error(error_block)
    agent = route_agent(error_type)
    result = agent.analyze(error_block)

    _print_structured(
        file_path=file_path,
        error_type=error_type,
        root_cause=result.root_cause,
        fix=result.fix,
        severity=result.severity,
    )


def _simulate_copy_samples(sample_dir: Path, logs_dir: Path, delay_s: float = 1.0) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(sample_dir.glob("*.log")):
        dst = logs_dir / f"{src.stem}_{int(time.time())}.log"
        shutil.copyfile(src, dst)
        time.sleep(delay_s)


def main() -> int:
    # Keep prototype output clean on newer Python versions.
    warnings.filterwarnings(
        "ignore",
        message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.*",
        category=UserWarning,
    )

    load_dotenv()

    parser = argparse.ArgumentParser(description="Prototype log watcher + AI error router")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Copy dummy logs from sample_logs/ into logs/ to trigger the watcher",
    )
    parser.add_argument(
        "--simulate-delay",
        type=float,
        default=1.0,
        help="Delay (seconds) between copied sample logs when using --simulate",
    )
    args = parser.parse_args()

    watcher = LogWatcher(logs_dir=SETTINGS.logs_dir, on_new_log=_handle_new_log)
    watcher.start()
    print(f"Watching: {SETTINGS.logs_dir.resolve()}")
    print("Drop new *.log files into the folder to trigger analysis. Press Ctrl+C to stop.")

    try:
        if args.simulate:
            _simulate_copy_samples(
                SETTINGS.sample_logs_dir, SETTINGS.logs_dir, delay_s=args.simulate_delay
            )
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

