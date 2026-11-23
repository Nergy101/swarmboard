"""Tests for card labels: add/rm/rm-all/ls/color + label filters (NER-328).

Runs the real CLI as a subprocess against throw-away SQLite boards, because
that is exactly how agents use swrm.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWRM = os.path.join(REPO_ROOT, "swrm")


def run(*args, db, expect_ok=True):
    env = dict(os.environ, KANBAN_DB=db, KANBAN_ACTOR="tester")
    p = subprocess.run(
        [sys.executable, SWRM, *args],
        capture_output=True, text=True, env=env, timeout=60,
    )
    if expect_ok and p.returncode != 0:
        raise AssertionError(f"swrm {' '.join(args)} failed rc={p.returncode}\n"
                             f"stdout: {p.stdout}\nstderr: {p.stderr}")
    return p


class LabelTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="swrm-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = os.path.join(self.tmp, "board.db")
        run("init", db=self.db)
        for i, title in enumerate(["alpha werk", "beta werk", "gamma werk"]):
            run("add", title, db=self.db)
        self.ids = [t["id"] for t in json.loads(
            run("ls", "--json", db=self.db).stdout)]

    def add_labels(self, tid, *labels):
        run("label", "add", tid, *labels, db=self.db)


class TestLabelMutations(LabelTestCase):
    def test_add_single_and_multiple(self):
        self.add_labels(self.ids[0], "frontend")
        self.add_labels(self.ids[1], "backend", "infra")
        tasks = {t["id"]: t for t in json.loads(run("ls", "--json", db=self.db).stdout)}
        self.assertEqual(tasks[self.ids[0]]["labels"], ["frontend"])
        self.assertEqual(tasks[self.ids[1]]["labels"], ["backend", "infra"])

    def test_add_duplicate_fails(self):
        self.add_labels(self.ids[0], "frontend")
        p = run("label", "add", self.ids[0], "frontend", db=self.db, expect_ok=False)
        self.assertEqual(p.returncode, 1)
        self.assertIn("already on", p.stderr)

    def test_rm_labels(self):
        self.add_labels(self.ids[0], "a", "b", "c")
        run("label", "rm", self.ids[0], "a", "c", db=self.db)
        tasks = {t["id"]: t for t in json.loads(run("ls", "--json", db=self.db).stdout)}
        self.assertEqual(tasks[self.ids[0]]["labels"], ["b"])

    def test_rm_missing_label_fails(self):
        self.add_labels(self.ids[0], "a")
        p = run("label", "rm", self.ids[0], "nope", db=self.db, expect_ok=False)
        self.assertEqual(p.returncode, 1)
        self.assertIn("not on", p.stderr)

    def test_rm_all(self):
        self.add_labels(self.ids[0], "a", "b", "c")
        run("label", "rm-all", self.ids[0], db=self.db)
        tasks = {t["id"]: t for t in json.loads(run("ls", "--json", db=self.db).stdout)}
        self.assertEqual(tasks[self.ids[0]]["labels"], [])

    def test_events_emitted(self):
        self.add_labels(self.ids[0], "frontend")
        run("label", "rm", self.ids[0], "frontend", db=self.db)
        evs = json.loads(run("events", "--json", "--limit", "10", db=self.db).stdout)
        actions = [(e["action"], e["task_id"]) for e in evs
                   if e["action"] in ("labeled", "unlabeled")]
        self.assertEqual(actions[0], ("labeled", self.ids[0]))
        self.assertEqual(actions[1], ("unlabeled", self.ids[0]))


class TestLabelList(LabelTestCase):
    def test_ls_counts_and_colors(self):
        self.add_labels(self.ids[0], "frontend")
        self.add_labels(self.ids[1], "frontend", "backend")
        run("label", "color", "frontend", "cyan", db=self.db)
        rows = {r["label"]: r for r in json.loads(
            run("label", "ls", "--json", db=self.db).stdout)}
        self.assertEqual(rows["frontend"]["count"], 2)
        self.assertEqual(rows["frontend"]["color"], "cyan")
        self.assertEqual(rows["backend"]["color"], "")

    def test_plain_output_shows_color_name(self):
        self.add_labels(self.ids[0], "frontend")
        run("label", "color", "frontend", "red", db=self.db)
        out = run("label", "ls", db=self.db).stdout
        self.assertIn("frontend", out)
        self.assertIn("red", out)
        self.assertNotIn("\x1b[", out)


class TestLabelColors(LabelTestCase):
    def test_set_and_clear_color(self):
        self.add_labels(self.ids[0], "urgent")
        run("label", "color", "urgent", "red", db=self.db)
        rows = {r["label"]: r for r in json.loads(
            run("label", "ls", "--json", db=self.db).stdout)}
        self.assertEqual(rows["urgent"]["color"], "red")
        run("label", "color", "urgent", "", db=self.db)
        rows = {r["label"]: r for r in json.loads(
            run("label", "ls", "--json", db=self.db).stdout)}
        self.assertEqual(rows["urgent"]["color"], "")
        # --color form works too
        run("label", "color", "urgent", "--color", "green", db=self.db)
        rows = {r["label"]: r for r in json.loads(
            run("label", "ls", "--json", db=self.db).stdout)}
        self.assertEqual(rows["urgent"]["color"], "green")

    def test_invalid_color_rejected(self):
        self.add_labels(self.ids[0], "urgent")
        p = run("label", "color", "urgent", "perzik", db=self.db, expect_ok=False)
        self.assertEqual(p.returncode, 2)
        self.assertIn("color must be one of", p.stderr)


class TestLabelFilters(LabelTestCase):
    def test_ls_single_and_and_filter(self):
        self.add_labels(self.ids[0], "frontend", "urgent")
        self.add_labels(self.ids[1], "frontend")
        out = run("ls", "--label", "frontend", db=self.db).stdout
        self.assertEqual(len(out.strip().splitlines()), 2)
        out = run("ls", "--label", "frontend", "--label", "urgent", db=self.db).stdout
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn(self.ids[0], out)

    def test_board_label_filter(self):
        self.add_labels(self.ids[0], "frontend")
        out = run("board", "--label", "frontend", db=self.db).stdout
        self.assertIn("alpha werk", out)
        self.assertNotIn("beta werk", out)
        # board accepts status/assignee filters as well (tasks start in ready)
        out = run("board", "--status", "ready", db=self.db).stdout
        self.assertIn("alpha werk", out)

    def test_dash_label_filter(self):
        self.add_labels(self.ids[0], "frontend")
        out = run("dash", "--once", "--label", "frontend", db=self.db).stdout
        cards = out.split("FEED")[0]  # the FEED section echoes event details; check cards only
        self.assertIn("alpha werk", cards)
        self.assertNotIn("beta werk", cards)
        self.assertIn("READY (1)", out)


class TestRemoteLabels(LabelTestCase):
    def _free_port(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def test_remote_label_ops_and_snapshot(self):
        self.add_labels(self.ids[0], "frontend")
        port = self._free_port()
        env = dict(os.environ, KANBAN_DB=self.db)
        proc = subprocess.Popen(
            [sys.executable, SWRM, "serve", "--port", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
        )
        def _stop():
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self.addCleanup(_stop)
        url = f"http://127.0.0.1:{port}"
        # wait for the leader to come up
        import urllib.request
        for _ in range(50):
            try:
                with urllib.request.urlopen(url + "/snapshot?feed=1", timeout=2) as r:
                    snap = json.loads(r.read())
                break
            except Exception:
                time.sleep(0.2)
        else:
            self.fail("leader did not start")
        self.assertIn("labels", snap)  # snapshot exposes board label colors
        U = ("--url", url)
        # remote label add + filter
        run("label", "add", *U, self.ids[1], "remote", db=self.db)
        out = run("ls", *U, "--label", "remote", db=self.db).stdout
        self.assertIn(self.ids[1], out)
        self.assertNotIn(self.ids[0], out)
        # remote color lands in the snapshot's labels map
        run("label", "color", *U, "remote", "green", db=self.db)
        with urllib.request.urlopen(url + "/snapshot?feed=1", timeout=5) as r:
            snap = json.loads(r.read())
        self.assertIn("remote", snap["labels"])


if __name__ == "__main__":
    unittest.main()
