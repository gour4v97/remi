"""Lightweight REST API server for Remi - modeled after OpenJarvis server.

Provides HTTP JSON endpoints for executing voice/text commands, querying history,
checking LLM status, accessing SQLite memory facts, and inspecting discovered skills.
"""
from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from remi.core import config
from remi.core.constants import APP_DISPLAY_NAME, APP_VERSION
from remi.core.memory import get_memory
from remi.engine.llm import auto_detect_llm
from remi.engine.openjarvis import get_openjarvis_bridge
from remi.skills import SkillManager
from remi.tools import history, router

logger = logging.getLogger(__name__)


class RemiRequestHandler(BaseHTTPRequestHandler):
    """Handles REST API requests for Remi assistant."""

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            cfg = config.load("remi-py")
            oj_enabled = cfg.get("openjarvis", {}).get("enabled", False)
            oj_connected = False
            oj_endpoint = cfg.get("openjarvis", {}).get("endpoint", "http://127.0.0.1:8000")

            if oj_enabled:
                oj_bridge = get_openjarvis_bridge(oj_endpoint)
                oj_connected = oj_bridge.is_available()

            self._send_json(
                200,
                {
                    "status": "healthy",
                    "app": APP_DISPLAY_NAME,
                    "version": APP_VERSION,
                    "openjarvis_bridge": {
                        "enabled": oj_enabled,
                        "connected": oj_connected,
                        "endpoint": oj_endpoint,
                    },
                },
            )
            return

        if path == "/v1/history":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", [20])[0])
            entries = history.load("remi-py", limit)
            self._send_json(200, {"entries": entries, "count": len(entries)})
            return

        if path == "/v1/memory":
            mem = get_memory()
            facts = mem.get_all_facts()
            recent_turns = mem.get_recent_history(limit=10)
            last_url = mem.recall_entity("last_url")
            self._send_json(
                200,
                {
                    "user_facts": facts,
                    "recent_turns": recent_turns,
                    "last_recalled_entity": last_url,
                },
            )
            return

        if path == "/v1/skills":
            mgr = SkillManager()
            skills = [
                {
                    "name": s.name,
                    "description": s.description,
                    "triggers": s.triggers,
                    "enabled": s.enabled,
                }
                for s in mgr.list_skills()
            ]
            self._send_json(200, {"skills": skills, "count": len(skills)})
            return

        if path == "/v1/llm":
            llm = auto_detect_llm()
            if llm:
                self._send_json(
                    200,
                    {
                        "available": True,
                        "engine": llm.__class__.__name__,
                        "model": llm.model,
                        "models": llm.list_models(),
                    },
                )
            else:
                self._send_json(200, {"available": False, "models": []})
            return

        self._send_json(404, {"error": "Not found", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/v1/command":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON payload"})
                return

            text = body.get("text", "").strip()
            if not text:
                self._send_json(400, {"error": "Missing 'text' parameter"})
                return

            cfg = config.load("remi-py")
            outcome = router.run(text, cfg)
            self._send_json(
                200,
                {
                    "ok": outcome.ok,
                    "spoken": outcome.spoken,
                    "detail": outcome.detail,
                    "transcript": text,
                },
            )
            return

        if path == "/v1/memory/fact":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON payload"})
                return

            key = body.get("key", "").strip()
            val = body.get("value", "").strip()
            category = body.get("category", "general")
            if not key or not val:
                self._send_json(400, {"error": "Missing 'key' or 'value'"})
                return

            get_memory().set_fact(key, val, category=category)
            self._send_json(200, {"status": "saved", "key": key, "value": val})
            return

        self._send_json(404, {"error": "Not found", "path": path})

    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))


def start_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Instantiate and start the Remi HTTP server."""
    server = ThreadingHTTPServer((host, port), RemiRequestHandler)
    return server
