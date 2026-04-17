from __future__ import annotations

import argparse
import shutil
import time
import warnings
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from agents import route_agent
from classifier import classify_error
from cli_ui import CliUI, ExecutionResult
from config import SETTINGS
from log_watcher import LogWatcher, extract_error_block

UI = CliUI()


def _emit_result(
    *,
    file_path: Path,
    error_type: str,
    root_cause: str,
    fix: str,
    severity: str,
) -> None:
    """
    Convert pipeline output into a UI-neutral object.

    This boundary is intentionally explicit so we can replace `CliUI` with an
    HTML renderer later without changing the core log-processing flow.
    """
    UI.show_result(
        ExecutionResult(
            file_path=file_path,
            error_type=error_type,
            root_cause=root_cause,
            fix=fix,
            severity=severity,
            timestamp=datetime.now(),
        )
    )


def _handle_new_log(file_path: Path, log_text: str) -> None:
    """
    Main pipeline callback for each new log file:
    1) detect error block, 2) classify, 3) route to specialist agent, 4) render.
    """
    if not log_text or not log_text.strip():
        _emit_result(
            file_path=file_path,
            error_type="unknown",
            root_cause="Log file is empty.",
            fix="Ensure the logging system writes content to the file.",
            severity="Low",
        )
        return

    error_block = extract_error_block(log_text)
    if not error_block:
        _emit_result(
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

    _emit_result(
        file_path=file_path,
        error_type=error_type,
        root_cause=result.root_cause,
        fix=result.fix,
        severity=result.severity,
    )


def _simulate_copy_samples(sample_dir: Path, logs_dir: Path, delay_s: float = 1.0) -> None:
    """
    Test helper: copy sample logs into watched folder to trigger the watcher.
    """
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
    UI.show_startup(SETTINGS.logs_dir)

    try:
        if args.simulate:
            _simulate_copy_samples(
                SETTINGS.sample_logs_dir, SETTINGS.logs_dir, delay_s=args.simulate_delay
            )
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        UI.show_shutdown()
        watcher.stop()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

