"""Tests for onboarding (first-run guide): shown once by `swrm init` and the
first interactive `swrm dash`, always available via `swrm help`; never in
--json mode and never in piped (non-TTY) dash output.

Runs the real CLI as a subprocess with an isolated $SWRM_HOME so the
once-per-user marker never touches the developer's real ~/.swarmboard.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWRM = os.path.join(REPO_ROOT, "swrm")


class OnboardingTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="swrm-onboard-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = os.path.join(self.tmp, "board.db")
        self.home = os.path.join(self.tmp, "home")
        self.marker = os.path.join(self.home, "onboarded")

    def run_swrm(self, *args):
        env = dict(os.environ, KANBAN_DB=self.db, KANBAN_ACTOR="tester",
                   SWRM_HOME=self.home)
        return subprocess.run([sys.executable, SWRM, *args],
                              capture_output=True, text=True, env=env, timeout=60)

    def test_init_shows_welcome_once(self):
        first = self.run_swrm("init")
        self.assertIn("Quick start:", first.stdout)
        self.assertIn("swrm dash", first.stdout)
        self.assertIn("swrm help", first.stdout)
        self.assertTrue(os.path.exists(self.marker))
        second = self.run_swrm("init")
        self.assertEqual(second.returncode, 0)
        self.assertNotIn("Quick start:", second.stdout)

    def test_init_json_prints_no_welcome_and_no_marker(self):
        p = self.run_swrm("init", "--json")
        data = json.loads(p.stdout)
        self.assertTrue(data["db"].endswith("board.db"))
        self.assertNotIn("Quick start:", p.stdout)
        self.assertFalse(os.path.exists(self.marker))

    def test_help_always_shows_guide(self):
        # help works even after the user is onboarded
        self.run_swrm("init")
        p = self.run_swrm("help")
        self.assertIn("Quick start:", p.stdout)
        self.assertIn("swrm help", p.stdout)

    def test_dash_once_piped_shows_no_welcome_and_no_marker(self):
        self.run_swrm("add", "seed task")
        self.assertFalse(os.path.exists(self.marker))
        p = self.run_swrm("dash", "--once")
        self.assertEqual(p.returncode, 0)
        self.assertNotIn("Quick start:", p.stdout)
        self.assertFalse(os.path.exists(self.marker),
                         "piped dash must not consume the welcome marker")


if __name__ == "__main__":
    unittest.main()
