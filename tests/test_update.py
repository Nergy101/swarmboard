"""Tests for `swrm update` self-update (NER-329): version flag, up-to-date
check, per-install-method plans and error handling, against a local mock of
the PyPI JSON API (stdlib http.server)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWRM = os.path.join(REPO_ROOT, "swrm")

VERSION_IN_SOURCE = None
with open(os.path.join(REPO_ROOT, "swrm.py")) as _f:
    for _line in _f:
        if _line.startswith("VERSION = __version__"):
            VERSION_IN_SOURCE = _line.split('"')[1]
            break


class MockIndexHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.endswith("/swarmboard/json"):
            self.send_response(200)
            payload = json.dumps({"info": {"version": self.server.latest}}).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()


class UpdateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="swrm-update-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = os.path.join(self.tmp, "board.db")
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), MockIndexHandler)
        self.srv.latest = VERSION_IN_SOURCE
        t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(self.srv.shutdown)
        self.addCleanup(self.srv.server_close)
        self.index = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def run_swrm(self, *args, via=None, expect_ok=True):
        env = dict(os.environ, KANBAN_DB=self.db, KANBAN_ACTOR="tester",
                   SWRM_PYPI_INDEX=self.index)
        if via:
            env["SWRM_INSTALL_VIA"] = via
        p = subprocess.run([sys.executable, SWRM, *args],
                           capture_output=True, text=True, env=env, timeout=60)
        if expect_ok and p.returncode != 0:
            raise AssertionError(f"swrm {' '.join(args)} failed rc={p.returncode}\n"
                                 f"stdout: {p.stdout}\nstderr: {p.stderr}")
        return p

    def test_version_flag_matches_source(self):
        p = self.run_swrm("--version")
        self.assertIn(f"swrm {VERSION_IN_SOURCE}", p.stdout)
        self.assertNotEqual(VERSION_IN_SOURCE, None)

    def test_up_to_date(self):
        p = self.run_swrm("update", "--json")
        data = json.loads(p.stdout)
        self.assertEqual(data["latest"], VERSION_IN_SOURCE)
        self.assertIn("up to date", self.run_swrm("update").stdout)

    def test_dry_run_plans_per_install_method(self):
        self.srv.latest = "99.0.0"
        for via, expect in [
            ("pipx", "pipx upgrade swarmboard"),
            ("brew", "brew upgrade swrm"),
            ("git", "git pull --ff-only"),
            ("script", "manual download"),
        ]:
            p = self.run_swrm("update", "--dry-run", via=via)
            self.assertIn("swrm", p.stdout)
            self.assertIn(expect, p.stdout)
            data = json.loads(self.run_swrm("update", "--dry-run", "--json", via=via).stdout)
            self.assertEqual(data["latest"], "99.0.0")
            self.assertEqual(data["via"], via)

    def test_loose_script_gets_instructions_and_fails(self):
        self.srv.latest = "99.0.0"
        p = self.run_swrm("update", "--yes", via="script", expect_ok=False)
        self.assertEqual(p.returncode, 1)
        self.assertIn("curl -LO", p.stdout)

    def test_unreachable_index_is_a_clear_error(self):
        env = dict(os.environ, KANBAN_DB=self.db, KANBAN_ACTOR="tester",
                   SWRM_PYPI_INDEX=f"http://127.0.0.1:1")  # nothing listens here
        p = subprocess.run([sys.executable, SWRM, "update", "--dry-run"],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn("cannot reach the package index", p.stderr)


if __name__ == "__main__":
    unittest.main()
