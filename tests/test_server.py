"""Unit tests for Remi REST API server."""
import json
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from remi.server import start_server


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 8789
        cls.server = start_server(host="127.0.0.1", port=cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/health"
        with urllib.request.urlopen(url, timeout=2) as r:
            self.assertEqual(r.status, 200)
            data = json.loads(r.read().decode("utf-8"))
            self.assertEqual(data["status"], "healthy")
            self.assertIn("Remi", data["app"])

    def test_skills_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/v1/skills"
        with urllib.request.urlopen(url, timeout=2) as r:
            self.assertEqual(r.status, 200)
            data = json.loads(r.read().decode("utf-8"))
            self.assertGreaterEqual(data["count"], 2)

    def test_post_command_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/v1/command"
        payload = json.dumps({"text": "what time is it"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=2) as r:
            self.assertEqual(r.status, 200)
            data = json.loads(r.read().decode("utf-8"))
            self.assertTrue(data["ok"])
            self.assertIn("it's", data["spoken"])


if __name__ == "__main__":
    unittest.main()
