from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DemoStartupSmokeTests(unittest.TestCase):
    def test_module_entry_starts_health_endpoint_and_stops(self) -> None:
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]

        environment = os.environ.copy()
        environment.update({"HOST": "127.0.0.1", "PORT": str(port)})
        process = subprocess.Popen(
            [sys.executable, "-B", "-m", "apps.demo"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = ""
        try:
            deadline = time.monotonic() + 10
            health = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    output = process.stdout.read() if process.stdout is not None else ""
                    self.fail(f"Demo exited before becoming healthy:\n{output}")
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/healthz", timeout=0.5
                    ) as response:
                        health = json.load(response)
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.1)
            self.assertEqual(
                {"status": "ok", "case": "ST-001", "mode": "demo-v0.1"},
                health,
                "Demo did not become healthy before the timeout",
            )
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/", timeout=2
            ) as response:
                self.assertIn(b"SimTrouble Tutor", response.read())
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    process.terminate()
                else:
                    process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
        self.assertIsNotNone(process.returncode)


if __name__ == "__main__":
    unittest.main()
