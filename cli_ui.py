from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass(frozen=True)
class ExecutionResult:
    """
    UI-friendly payload for one processed log.

    Keeping this structure independent from log/agent internals makes it easy to
    replace terminal rendering with an HTML/web renderer later.
    """

    file_path: Path
    error_type: str
    root_cause: str
    fix: str
    severity: str
    timestamp: datetime


class CliUI:
    """
    Terminal renderer for the prototype.

    This class is intentionally focused only on presentation so future UI channels
    (HTML, API, dashboard) can reuse the same processing pipeline.
    """

    def __init__(self) -> None:
        self.console = Console()
        self._unicode_ok = self._supports_unicode_output()

    # ---------- Top-level status banners ----------
    def show_startup(self, logs_dir: Path) -> None:
        title = Text(f"{self._icon('rocket')} AI Log Analyzer Started", style="bold cyan")
        subtitle = (
            f"Watching: {logs_dir.resolve()}\n"
            "Drop new .log files to analyze or use --simulate.\n"
            "Press Ctrl+C to stop."
        )
        self.console.print(Panel.fit(subtitle, title=title, border_style="cyan"))

    def show_shutdown(self) -> None:
        self.console.print(
            Panel.fit(f"{self._icon('stop')} Stopping watcher...", border_style="yellow")
        )

    # ---------- Core result rendering ----------
    def show_result(self, result: ExecutionResult) -> None:
        emoji = self._type_emoji(result.error_type)
        sev_style = self._severity_style(result.severity)

        summary = Table.grid(expand=True)
        summary.add_column(style="bold")
        summary.add_column()
        summary.add_row(f"{self._icon('file')} File", result.file_path.name)
        summary.add_row(f"{self._icon('tag')} Type", f"{emoji} {result.error_type}")
        summary.add_row(
            f"{self._icon('clock')} Timestamp", result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        )
        summary.add_row(
            f"{self._icon('fire')} Severity", f"[{sev_style}]{result.severity}[/{sev_style}]"
        )

        body = Table.grid(padding=(0, 1))
        body.add_column()
        body.add_row(summary)
        body.add_row("")
        body.add_row(f"[bold magenta]{self._icon('search')} Root Cause[/bold magenta]")
        body.add_row(result.root_cause.strip() or "(empty)")
        body.add_row("")
        body.add_row(f"[bold green]{self._icon('fix')} Fix[/bold green]")
        body.add_row(result.fix.strip() or "(empty)")

        self.console.print(
            Panel(
                body,
                title="[bold white]Execution Result[/bold white]",
                border_style=self._type_color(result.error_type),
            )
        )

    # ---------- Visual mapping helpers ----------
    @staticmethod
    def _type_color(error_type: str) -> str:
        m = {"db": "blue", "infra": "red", "code": "magenta", "unknown": "yellow"}
        return m.get((error_type or "").lower(), "white")

    def _type_emoji(self, error_type: str) -> str:
        m = {"db": "db", "infra": "infra", "code": "code", "unknown": "unknown"}
        key = m.get((error_type or "").lower(), "unknown")
        return self._emoji_or_ascii(key, self._unicode_ok)

    @staticmethod
    def _severity_style(severity: str) -> str:
        s = (severity or "").lower()
        if s == "high":
            return "bold red"
        if s == "medium":
            return "bold yellow"
        if s == "low":
            return "bold green"
        return "bold white"

    @staticmethod
    def _supports_unicode_output() -> bool:
        """
        Check if terminal encoding can handle emoji glyphs.
        """
        encoding = (sys.stdout.encoding or "").lower()
        if "utf" in encoding:
            return True
        try:
            "🚀".encode(sys.stdout.encoding or "ascii")
            return True
        except Exception:
            return False

    @staticmethod
    def _emoji_or_ascii(name: str, unicode_ok: bool) -> str:
        unicode_map = {
            "rocket": "🚀",
            "stop": "🛑",
            "file": "📄",
            "tag": "🏷️",
            "clock": "⏰",
            "fire": "🔥",
            "search": "🔍",
            "fix": "🛠️",
            "db": "🗄️",
            "infra": "🧱",
            "code": "🐍",
            "unknown": "❓",
        }
        ascii_map = {
            "rocket": "[START]",
            "stop": "[STOP]",
            "file": "[FILE]",
            "tag": "[TYPE]",
            "clock": "[TIME]",
            "fire": "[SEV]",
            "search": "[CAUSE]",
            "fix": "[FIX]",
            "db": "[DB]",
            "infra": "[INFRA]",
            "code": "[CODE]",
            "unknown": "[?]",
        }
        return unicode_map[name] if unicode_ok else ascii_map[name]

    def _icon(self, name: str) -> str:
        return self._emoji_or_ascii(name, self._unicode_ok)

