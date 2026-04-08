from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


ERROR_KEYWORDS = ("ERROR", "Traceback", "Exception")


def extract_error_block(log_text: str) -> str | None:
    """
    Extract an error *block* from a log.

    Heuristic (prototype):
    - Find the earliest occurrence of any keyword (ERROR / Traceback / Exception)
    - Return everything from that point to end-of-file
    This tends to capture full tracebacks and multi-line error context.
    """
    if not log_text or not log_text.strip():
        return None

    earliest_idx: int | None = None
    for kw in ERROR_KEYWORDS:
        idx = log_text.find(kw)
        if idx != -1 and (earliest_idx is None or idx < earliest_idx):
            earliest_idx = idx

    if earliest_idx is None:
        return None

    return log_text[earliest_idx:].strip()


def _read_text_when_stable(path: Path, max_wait_s: float = 5.0) -> str:
    """
    Wait briefly for file size to stabilize to reduce partial reads.
    """
    deadline = time.time() + max_wait_s
    last_size = -1
    while time.time() < deadline:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            time.sleep(0.1)
            continue
        if size == last_size:
            break
        last_size = size
        time.sleep(0.2)

    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        # Fallback if encoding is odd
        return path.read_text(errors="replace")


OnNewLogCallback = Callable[[Path, str], None]


@dataclass
class LogWatcher:
    logs_dir: Path
    on_new_log: OnNewLogCallback

    def __post_init__(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._processed: set[str] = set()
        self._observer: Observer | None = None

    def start(self) -> None:
        handler = _CreatedHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self.logs_dir), recursive=False)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5)

    def _handle_created(self, path: Path) -> None:
        if path.is_dir():
            return
        if path.suffix.lower() not in {".log", ".txt"}:
            return

        key = str(path.resolve()).lower()
        if key in self._processed:
            return
        self._processed.add(key)

        text = _read_text_when_stable(path)
        self.on_new_log(path, text)


class _CreatedHandler(FileSystemEventHandler):
    def __init__(self, watcher: LogWatcher) -> None:
        super().__init__()
        self.watcher = watcher

    def on_created(self, event):  # type: ignore[override]
        try:
            path = Path(event.src_path)
            self.watcher._handle_created(path)
        except Exception:
            # Prototype: avoid crashing the observer thread
            return

