"""Tests for multi-board support: registry, -b/--board, boards, switch (NER-330).

Runs the real CLI as a subprocess against throw-away SQLite boards, with an
isolated SWRM_HOME so the registry (~/.swarmboard/boards.json) never touches
the developer's real registry.
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


class BoardTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="swrm-boards-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = os.path.join(self.tmp, "swrm-home")
        os.makedirs(self.home)
        self.db_a = os.path.join(self.tmp, "a.db")
        self.db_b = os.path.join(self.tmp, "b.db")

    def run_swrm(self, *args, expect_ok=True, cwd=None):
        env = dict(os.environ, KANBAN_ACTOR="tester", SWRM_HOME=self.home)
        # make sure ambient KANBAN_DB / cwd defaults cannot interfere
        env.pop("KANBAN_DB", None)
        p = subprocess.run(
            [sys.executable, SWRM, *args],
            capture_output=True, text=True, env=env, timeout=60, cwd=cwd or self.tmp,
        )
        if expect_ok and p.returncode != 0:
            raise AssertionError(f"swrm {' '.join(args)} failed rc={p.returncode}\n"
                                 f"stdout: {p.stdout}\nstderr: {p.stderr}")
        return p


class TestRegistry(BoardTestCase):
    def test_add_list_json_and_active_marker(self):
        self.run_swrm("init", "--db", self.db_a)
        self.run_swrm("init", "--db", self.db_b)
        self.run_swrm("boards", "add", "alpha", self.db_a)
        self.run_swrm("boards", "add", "beta", self.db_b)
        listing = json.loads(self.run_swrm("boards", "--json").stdout)
        self.assertEqual([b["name"] for b in listing["boards"]], ["alpha", "beta"])
        self.assertIsNone(listing["active"])
        self.run_swrm("switch", "alpha")
        listing = json.loads(self.run_swrm("boards", "--json").stdout)
        self.assertEqual(listing["active"], "alpha")
        self.assertTrue(listing["boards"][0]["active"])
        # 'ls' is an alias for the default listing
        self.assertIn("alpha", self.run_swrm("boards", "ls").stdout)

    def test_add_duplicate_name_fails(self):
        self.run_swrm("init", "--db", self.db_a)
        self.run_swrm("boards", "add", "alpha", self.db_a)
        p = self.run_swrm("boards", "add", "alpha", self.db_b, expect_ok=False)
        self.assertEqual(p.returncode, 1)
        self.assertIn("taken", p.stderr)

    def test_rename_keeps_active(self):
        self.run_swrm("init", "--db", self.db_a)
        self.run_swrm("boards", "add", "alpha", self.db_a)
        self.run_swrm("switch", "alpha")
        self.run_swrm("boards", "rename", "alpha", " hoofdboard ".strip())
        self.run_swrm("boards", "rename", "hoofdboard", "alfa")
        listing = json.loads(self.run_swrm("boards", "--json").stdout)
        self.assertEqual(listing["active"], "alfa")
        self.assertEqual(listing["boards"][0]["path"], self.db_a)
        p = self.run_swrm("ls", "-b", "alpha", expect_ok=False)
        self.assertEqual(p.returncode, 2)  # renamed away

    def test_rm_clears_active_but_keeps_db(self):
        self.run_swrm("init", "--db", self.db_a)
        self.run_swrm("boards", "add", "alpha", self.db_a)
        self.run_swrm("switch", "alpha")
        self.run_swrm("boards", "rm", "alpha")
        listing = json.loads(self.run_swrm("boards", "--json").stdout)
        self.assertEqual(listing["boards"], [])
        self.assertIsNone(listing["active"])
        self.assertTrue(os.path.exists(self.db_a), "rm must not delete the database")


class TestBoardSelection(BoardTestCase):
    def seed(self):
        self.run_swrm("init", "--db", self.db_a)
        self.run_swrm("init", "--db", self.db_b)
        self.run_swrm("boards", "add", "alpha", self.db_a)
        self.run_swrm("boards", "add", "beta", self.db_b)

    def test_b_flag_selects_board(self):
        self.seed()
        self.run_swrm("add", "taak A")
        self.run_swrm("add", "taak B", "-b", "beta")
        titles_a = {t["title"] for t in json.loads(
            self.run_swrm("ls", "--json").stdout)}
        titles_b = {t["title"] for t in json.loads(
            self.run_swrm("ls", "--json", "-b", "beta").stdout)}
        self.assertEqual(titles_a, {"taak A"})
        self.assertEqual(titles_b, {"taak B"})

    def test_db_wins_over_board_flag(self):
        self.seed()
        self.run_swrm("add", "op beta", "-b", "beta")
        rows = json.loads(
            self.run_swrm("ls", "--json", "--db", self.db_b, "-b", "alpha").stdout)
        self.assertEqual([t["title"] for t in rows], ["op beta"])

    def test_switch_changes_default_board(self):
        self.seed()
        self.run_swrm("switch", "alpha")
        self.run_swrm("add", "op alpha")
        self.run_swrm("switch", "beta")
        self.run_swrm("add", "op beta")
        rows = json.loads(self.run_swrm("ls", "--json").stdout)
        self.assertEqual([t["title"] for t in rows], ["op beta"])
        self.run_swrm("switch", "alpha")
        rows = json.loads(self.run_swrm("ls", "--json").stdout)
        self.assertEqual([t["title"] for t in rows], ["op alpha"])

    def test_unknown_board_errors(self):
        self.seed()
        p = self.run_swrm("ls", "-b", "gamma", expect_ok=False)
        self.assertEqual(p.returncode, 2)
        p = self.run_swrm("switch", "gamma", expect_ok=False)
        self.assertEqual(p.returncode, 1)

    def test_kanban_db_env_wins_over_registry(self):
        self.seed()
        self.run_swrm("init", "--db", self.db_a)
        self.run_swrm("boards", "add", "anders", self.db_a)
        self.run_swrm("switch", "anders")
        env_db = os.path.join(self.tmp, "env.db")
        env = dict(os.environ, KANBAN_ACTOR="tester", SWRM_HOME=self.home,
                   KANBAN_DB=env_db)
        subprocess.run([sys.executable, SWRM, "init"],
                       capture_output=True, text=True, env=env, timeout=60, check=True)
        p = subprocess.run([sys.executable, SWRM, "ls", "--json"],
                           capture_output=True, text=True, env=env, timeout=60, check=True)
        self.assertEqual(json.loads(p.stdout), [])

    def test_dash_title_shows_board_name(self):
        self.seed()
        self.run_swrm("add", "x", "-b", "beta")
        out = self.run_swrm("dash", "--once", "-b", "beta").stdout
        first = out.splitlines()[0]
        self.assertIn("beta", first)
        self.assertNotIn("alpha", first)


if __name__ == "__main__":
    unittest.main()
