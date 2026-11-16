"""OpenJarvis local agent connector & brain bridge.

Enables Remi to function as a voice-first, Windows-native frontend while optionally
delegating complex reasoning, multi-step agent graphs, and agentskills.io tool execution
to a local OpenJarvis instance (running on http://127.0.0.1:8000 or custom port).
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from remi.core.registry import EngineRegistry

logger = logging.getLogger(__name__)


@EngineRegistry.register("openjarvis_bridge")
class OpenJarvisBridge:
    """HTTP client bridge communicating with local OpenJarvis agent server."""

    def __init__(self, endpoint: str = "http://127.0.0.1:8000", timeout: float = 15.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        """Probe if local OpenJarvis server is reachable."""
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/health", method="GET")
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_agents(self) -> list[str]:
        """Fetch list of active OpenJarvis agents (ReAct, orchestrator, scheduled)."""
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/agents", method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [a.get("name", "") for a in data.get("agents", [])]
        except Exception as ex:
            logger.debug(f"OpenJarvis agents fetch failed: {ex}")
            return []

    def dispatch_agent_task(self, query: str, agent: str = "orchestrator") -> dict[str, Any] | None:
        """Delegate a query to OpenJarvis ReAct/orchestrator agent and return structured response."""
        url = f"{self.endpoint}/api/agent/dispatch"
        payload = {
            "query": query,
            "agent": agent,
            "stream": False,
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "ok": True,
                    "action": data.get("action", "speak"),
                    "spoken": data.get("spoken", data.get("response", "Task completed.")),
                    "detail": f"openjarvis:{agent}",
                    "result": data.get("result", {}),
                }
        except Exception as ex:
            logger.debug(f"OpenJarvis task dispatch failed: {ex}")
            return None


_cached_bridge: OpenJarvisBridge | None = None


def get_openjarvis_bridge(endpoint: str = "http://127.0.0.1:8000") -> OpenJarvisBridge:
    """Return singleton OpenJarvis bridge instance."""
    global _cached_bridge
    if _cached_bridge is None or _cached_bridge.endpoint != endpoint.rstrip("/"):
        _cached_bridge = OpenJarvisBridge(endpoint=endpoint)
    return _cached_bridge
