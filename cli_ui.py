from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass(frozen=True)
class ExecutionResult:
    file_path: Path
    error_type: str
    error_label: str
    root_cause: str
    fix: str
    severity: str
    timestamp: datetime
    rag_match_count: int = 0
    rag_available: bool = False


class CliUI:
    def __init__(self) -> None:
        self.console = Console()
        self._unicode_ok = self._supports_unicode_output()

    def show_web_dashboard(self, host: str, port: int) -> None:
        url = f"http://{host}:{port}"
        self.console.print(
            Panel.fit(
                f"Audit dashboard: [bold cyan]{url}[/bold cyan]\n"
                "View live stats, charts, and full audit history.",
                title="[bold green]Web Dashboard[/bold green]",
                border_style="green",
            )
        )

    def show_startup(
        self,
        logs_dir: Path,
        pipeline_name: str,
        error_type_count: int,
        rag_enabled: bool,
        llm_provider: str,
    ) -> None:
        title = Text(f"{self._icon('rocket')} {pipeline_name}", style="bold cyan")
        rag_status = "active" if rag_enabled else "disabled (SQLite keyword fallback)"
        subtitle = (
            f"Watching: {logs_dir.resolve()}\n"
            f"Error taxonomy: {error_type_count} Airflow types | LLM: {llm_provider}\n"
            f"RAG memory: {rag_status}\n"
            "Drop new .log files or use --simulate. Ctrl+C to stop."
        )
        self.console.print(Panel.fit(subtitle, title=title, border_style="cyan"))

    def show_shutdown(self) -> None:
        self.console.print(
            Panel.fit(f"{self._icon('stop')} Stopping watcher...", border_style="yellow")
        )

    def show_result(self, result: ExecutionResult) -> None:
        emoji = self._type_emoji(result.error_type)
        sev_style = self._severity_style(result.severity)

        summary = Table.grid(expand=True)
        summary.add_column(style="bold")
        summary.add_column()
        summary.add_row(f"{self._icon('file')} File", result.file_path.name)
        summary.add_row(f"{self._icon('tag')} Type", f"{emoji} {result.error_type}")
        summary.add_row("Label", result.error_label)
        summary.add_row(
            f"{self._icon('clock')} Timestamp", result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        )
        summary.add_row(
            f"{self._icon('fire')} Severity", f"[{sev_style}]{result.severity}[/{sev_style}]"
        )
        summary.add_row(
            "RAG matches",
            f"{result.rag_match_count} similar past case(s)"
            + (" (vector store)" if result.rag_available else " (fallback)"),
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

    @staticmethod
    def _type_color(error_type: str) -> str:
        prefix_map = {
            "dag": "magenta",
            "task": "red",
            "scheduler": "yellow",
            "connection": "blue",
            "xcom": "cyan",
            "sensor": "orange3",
            "pool": "purple",
            "worker": "red",
            "metadata": "blue",
            "variable": "magenta",
            "dag_file": "yellow",
            "celery": "red",
            "upstream": "magenta",
            "kubernetes": "red",
            "unknown": "yellow",
        }
        for prefix, color in prefix_map.items():
            if error_type.startswith(prefix):
                return color
        return "white"

    def _type_emoji(self, error_type: str) -> str:
        return self._emoji_or_ascii("tag", self._unicode_ok)

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
        }
        return unicode_map.get(name, "•") if unicode_ok else ascii_map.get(name, "[*]")

    def _icon(self, name: str) -> str:
        return self._emoji_or_ascii(name, self._unicode_ok)
