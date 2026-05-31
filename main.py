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
from memory import AnalysisMemory
from pipeline_context import build_pipeline_context, format_rag_context
from value_doc import update_value_document
from web.app import start_web_server

UI = CliUI()
MEMORY = AnalysisMemory()
PIPELINE_CONTEXT = build_pipeline_context()


def _emit_result(
    *,
    file_path: Path,
    error_type: str,
    error_label: str,
    root_cause: str,
    fix: str,
    severity: str,
    rag_matches: list[dict],
) -> None:
    UI.show_result(
        ExecutionResult(
            file_path=file_path,
            error_type=error_type,
            error_label=error_label,
            root_cause=root_cause,
            fix=fix,
            severity=severity,
            timestamp=datetime.now(),
            rag_match_count=len(rag_matches),
            rag_available=MEMORY.rag_available,
        )
    )


def _handle_new_log(file_path: Path, log_text: str) -> None:
    """
    Pipeline: extract -> classify -> RAG retrieve -> LLM analyze -> store -> update value doc.
    """
    if not log_text or not log_text.strip():
        _emit_result(
            file_path=file_path,
            error_type="unknown",
            error_label="Unknown",
            root_cause="Log file is empty.",
            fix="Ensure the logging system writes content to the file.",
            severity="Low",
            rag_matches=[],
        )
        return

    error_block = extract_error_block(log_text)
    if not error_block:
        _emit_result(
            file_path=file_path,
            error_type="unknown",
            error_label="Unknown",
            root_cause="No error keywords found (ERROR / Traceback / Exception).",
            fix="No action needed. If this is unexpected, expand error detection rules.",
            severity="Low",
            rag_matches=[],
        )
        return

    error_type_id, error_label = classify_error(error_block)
    rag_matches = MEMORY.retrieve_similar(error_block) if SETTINGS.rag_enabled else []
    rag_context = format_rag_context(rag_matches)

    agent = route_agent(error_type_id)
    result = agent.analyze(
        error_block,
        error_type_id=error_type_id,
        error_label=error_label,
        pipeline_context=PIPELINE_CONTEXT,
        rag_context=rag_context,
    )

    MEMORY.store(
        file_path=file_path,
        error_type=error_type_id,
        error_label=error_label,
        root_cause=result.root_cause,
        fix=result.fix,
        severity=result.severity,
        error_text=error_block,
    )

    stats = MEMORY.stats()
    update_value_document(
        file_path=file_path,
        error_type=error_type_id,
        error_label=error_label,
        root_cause=result.root_cause,
        fix=result.fix,
        severity=result.severity,
        rag_match_count=len(rag_matches),
        memory_stats=stats,
    )

    _emit_result(
        file_path=file_path,
        error_type=error_type_id,
        error_label=error_label,
        root_cause=result.root_cause,
        fix=result.fix,
        severity=result.severity,
        rag_matches=rag_matches,
    )


def _simulate_copy_samples(sample_dir: Path, logs_dir: Path, delay_s: float = 1.0) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(sample_dir.glob("*.log")):
        dst = logs_dir / f"{src.stem}_{int(time.time())}.log"
        shutil.copyfile(src, dst)
        time.sleep(delay_s)


def main() -> int:
    warnings.filterwarnings(
        "ignore",
        message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.*",
        category=UserWarning,
    )

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Airflow log watcher + RAG-enhanced AI error analyzer"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Copy sample logs from sample_logs/ into logs/ to trigger the watcher",
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

    if SETTINGS.web_enabled:
        start_web_server(MEMORY)
        UI.show_web_dashboard(SETTINGS.web_host, SETTINGS.web_port)

    UI.show_startup(
        logs_dir=SETTINGS.logs_dir,
        pipeline_name=SETTINGS.pipeline.name,
        error_type_count=len(SETTINGS.error_types),
        rag_enabled=MEMORY.rag_available,
        llm_provider=SETTINGS.llm_provider,
    )

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
