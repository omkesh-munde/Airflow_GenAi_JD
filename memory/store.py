from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document

from config import SETTINGS
from embedding_factory import create_embeddings, embeddings_configured


@dataclass(frozen=True)
class StoredAnalysis:
    analysis_id: str
    file_path: str
    error_type: str
    error_label: str
    root_cause: str
    fix: str
    severity: str
    error_text: str
    timestamp: str


class AnalysisMemory:
    """
    Hybrid memory: SQLite for structured history + Chroma for semantic retrieval.
    """

    COLLECTION = "airflow_error_analyses"

    def __init__(self) -> None:
        self._persist_dir = SETTINGS.chroma_persist_dir
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._sqlite_path = self._persist_dir / "analyses.sqlite"
        self._vectorstore = None
        self._embeddings_ready = False
        self._init_sqlite()
        self._init_vectorstore()

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_label TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    fix TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    error_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _init_vectorstore(self) -> None:
        if not SETTINGS.rag_enabled:
            return
        if not embeddings_configured():
            return
        try:
            from langchain_chroma import Chroma

            self._vectorstore = Chroma(
                collection_name=self.COLLECTION,
                embedding_function=create_embeddings(),
                persist_directory=str(self._persist_dir),
            )
            self._embeddings_ready = True
        except Exception:
            self._vectorstore = None
            self._embeddings_ready = False

    @property
    def rag_available(self) -> bool:
        return SETTINGS.rag_enabled and self._embeddings_ready and self._vectorstore is not None

    def store(
        self,
        *,
        file_path: Path,
        error_type: str,
        error_label: str,
        root_cause: str,
        fix: str,
        severity: str,
        error_text: str,
    ) -> str:
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        with sqlite3.connect(self._sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO analyses
                (id, file_path, error_type, error_label, root_cause, fix, severity, error_text, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    str(file_path),
                    error_type,
                    error_label,
                    root_cause,
                    fix,
                    severity,
                    error_text,
                    timestamp,
                ),
            )
            conn.commit()

        if self.rag_available and self._vectorstore is not None:
            doc = Document(
                page_content=error_text,
                metadata={
                    "analysis_id": analysis_id,
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "error_type": error_type,
                    "error_label": error_label,
                    "root_cause": root_cause,
                    "fix": fix,
                    "severity": severity,
                    "timestamp": timestamp,
                },
            )
            try:
                self._vectorstore.add_documents([doc], ids=[analysis_id])
            except Exception:
                pass

        return analysis_id

    def retrieve_similar(self, error_text: str, *, top_k: int | None = None) -> list[dict]:
        k = top_k or SETTINGS.rag_top_k
        if not self.rag_available or self._vectorstore is None:
            return self._sqlite_fallback_similar(error_text, k)

        try:
            results = self._vectorstore.similarity_search_with_score(error_text, k=k)
        except Exception:
            return self._sqlite_fallback_similar(error_text, k)

        matches: list[dict] = []
        for doc, score in results:
            if SETTINGS.rag_min_similarity and score < SETTINGS.rag_min_similarity:
                continue
            meta = doc.metadata
            matches.append(
                {
                    "analysis_id": meta.get("analysis_id", ""),
                    "file_name": meta.get("file_name", ""),
                    "error_type": meta.get("error_type", "unknown"),
                    "error_label": meta.get("error_label", ""),
                    "root_cause": meta.get("root_cause", ""),
                    "fix": meta.get("fix", ""),
                    "severity": meta.get("severity", ""),
                    "timestamp": meta.get("timestamp", ""),
                    "error_excerpt": doc.page_content[:1200],
                    "score": round(float(score), 4),
                }
            )
        return matches

    def _sqlite_fallback_similar(self, error_text: str, k: int) -> list[dict]:
        """Keyword overlap fallback when vector store is unavailable."""
        query_tokens = set(error_text.lower().split())
        with sqlite3.connect(self._sqlite_path) as conn:
            rows = conn.execute(
                "SELECT id, file_path, error_type, error_label, root_cause, fix, severity, error_text, timestamp "
                "FROM analyses ORDER BY timestamp DESC LIMIT 100"
            ).fetchall()

        scored: list[tuple[float, dict]] = []
        for row in rows:
            text = row[7].lower()
            tokens = set(text.split())
            overlap = len(query_tokens & tokens) / max(len(query_tokens), 1)
            if overlap <= 0:
                continue
            scored.append(
                (
                    overlap,
                    {
                        "analysis_id": row[0],
                        "file_name": Path(row[1]).name,
                        "error_type": row[2],
                        "error_label": row[3],
                        "root_cause": row[4],
                        "fix": row[5],
                        "severity": row[6],
                        "timestamp": row[8],
                        "error_excerpt": row[7][:1200],
                        "score": round(overlap, 4),
                    },
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:k]]

    def stats(self) -> dict:
        with sqlite3.connect(self._sqlite_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
            by_type = conn.execute(
                "SELECT error_type, COUNT(*) FROM analyses GROUP BY error_type ORDER BY COUNT(*) DESC"
            ).fetchall()
            by_severity = conn.execute(
                "SELECT severity, COUNT(*) FROM analyses GROUP BY severity"
            ).fetchall()
            latest = conn.execute(
                "SELECT timestamp FROM analyses ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        return {
            "total_analyses": total,
            "by_error_type": dict(by_type),
            "by_severity": dict(by_severity),
            "rag_available": self.rag_available,
            "latest_timestamp": latest[0] if latest else None,
        }

    def list_analyses(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        error_type: str | None = None,
        severity: str | None = None,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        """Return paginated audit history and total matching count."""
        conditions: list[str] = []
        params: list[object] = []

        if error_type:
            conditions.append("error_type = ?")
            params.append(error_type)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if search:
            conditions.append(
                "(error_label LIKE ? OR root_cause LIKE ? OR file_path LIKE ? OR error_type LIKE ?)"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with sqlite3.connect(self._sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(
                f"SELECT COUNT(*) FROM analyses {where}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT id, file_path, error_type, error_label, root_cause, fix, severity, error_text, timestamp
                FROM analyses {where}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        items = [
            {
                "id": row["id"],
                "file_name": Path(row["file_path"]).name,
                "file_path": row["file_path"],
                "error_type": row["error_type"],
                "error_label": row["error_label"],
                "root_cause": row["root_cause"],
                "fix": row["fix"],
                "severity": row["severity"],
                "error_excerpt": row["error_text"][:500],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]
        return items, total

    def get_analysis(self, analysis_id: str) -> dict | None:
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, file_path, error_type, error_label, root_cause, fix, severity, error_text, timestamp
                FROM analyses WHERE id = ?
                """,
                (analysis_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "file_name": Path(row["file_path"]).name,
            "file_path": row["file_path"],
            "error_type": row["error_type"],
            "error_label": row["error_label"],
            "root_cause": row["root_cause"],
            "fix": row["fix"],
            "severity": row["severity"],
            "error_text": row["error_text"],
            "timestamp": row["timestamp"],
        }
