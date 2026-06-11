from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from flask import Flask, jsonify, render_template, request

from config import SETTINGS

if TYPE_CHECKING:
    from memory.store import AnalysisMemory


def create_app(memory: AnalysisMemory) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MEMORY"] = memory

    @app.get("/")
    def dashboard() -> str:
        return render_template("dashboard.html", pipeline=SETTINGS.pipeline)

    @app.get("/workflow")
    def workflow() -> str:
        return render_template("workflow.html", pipeline=SETTINGS.pipeline)

    @app.get("/api/dashboard")
    def api_dashboard():
        mem: AnalysisMemory = app.config["MEMORY"]
        stats = mem.stats()
        return jsonify(
            {
                "pipeline": {
                    "name": SETTINGS.pipeline.name,
                    "version": SETTINGS.pipeline.version,
                    "environment": SETTINGS.pipeline.environment,
                    "airflow_version": SETTINGS.pipeline.airflow_version,
                    "executor": SETTINGS.pipeline.executor,
                    "dag_id": SETTINGS.pipeline.dag_id,
                },
                "llm": {
                    "provider": SETTINGS.llm_provider,
                    "model": SETTINGS.model,
                },
                "embeddings": {
                    "provider": SETTINGS.embedding_provider,
                    "model": SETTINGS.embedding_model,
                },
                "rag": {
                    "enabled": SETTINGS.rag_enabled,
                    "available": stats["rag_available"],
                    "top_k": SETTINGS.rag_top_k,
                },
                "stats": stats,
                "error_types": [
                    {"id": et.id, "label": et.label, "agent": et.agent}
                    for et in SETTINGS.error_types
                ],
            }
        )

    @app.get("/api/history")
    def api_history():
        mem: AnalysisMemory = app.config["MEMORY"]
        limit = min(int(request.args.get("limit", 25)), 100)
        offset = int(request.args.get("offset", 0))
        error_type = request.args.get("error_type") or None
        severity = request.args.get("severity") or None
        search = request.args.get("search") or None

        items, total = mem.list_analyses(
            limit=limit,
            offset=offset,
            error_type=error_type,
            severity=severity,
            search=search,
        )
        return jsonify({"items": items, "total": total, "limit": limit, "offset": offset})

    @app.get("/api/history/<analysis_id>")
    def api_history_detail(analysis_id: str):
        mem: AnalysisMemory = app.config["MEMORY"]
        item = mem.get_analysis(analysis_id)
        if item is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(item)

    return app


def start_web_server(memory: AnalysisMemory) -> threading.Thread | None:
    if not SETTINGS.web_enabled:
        return None

    app = create_app(memory)

    def _run() -> None:
        app.run(
            host=SETTINGS.web_host,
            port=SETTINGS.web_port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    thread = threading.Thread(target=_run, name="web-dashboard", daemon=True)
    thread.start()
    return thread


def run_standalone() -> None:
    """Run dashboard only (no log watcher)."""
    from dotenv import load_dotenv
    from memory import AnalysisMemory

    load_dotenv()
    memory = AnalysisMemory()
    app = create_app(memory)
    app.run(
        host=SETTINGS.web_host,
        port=SETTINGS.web_port,
        debug=False,
        threaded=True,
    )


if __name__ == "__main__":
    run_standalone()
