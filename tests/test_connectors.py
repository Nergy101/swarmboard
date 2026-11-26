"""Tests for connectors (NER-331): config CRUD + a full two-way Linear sync
against a local mock of the Linear GraphQL API (stdlib http.server).

No network access and no real token are needed; the mock records every
mutation so push results can be asserted.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWRM = os.path.join(REPO_ROOT, "swrm")

MOCK_STATES = [
    {"id": "s1", "name": "Todo"},
    {"id": "s2", "name": "In Progress"},
    {"id": "s3", "name": "Blocked"},
    {"id": "s4", "name": "Done"},
]


def now_ms_iso():
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f".{int((t % 1) * 1000):03d}Z"


class MockLinearHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep test output clean
        pass

    def do_POST(self):
        srv = self.server
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        query = body.get("query", "")
        variables = body.get("variables") or {}
        if srv.require_token and self.headers.get("Authorization") != srv.require_token:
            self._send(200, {"errors": [{"message": "Authentication required"}]})
            return
        srv.requests.append({"query": query, "variables": variables})

        def issue_view(i):
            return {"id": i["id"], "identifier": i["identifier"], "title": i["title"],
                    "description": i["description"], "updatedAt": i["updatedAt"],
                    "state": {"name": i["stateName"]}}

        if "teams(" in query:
            data = {"teams": {"nodes": [{"id": "team_1", "key": "NER", "name": "Core"}]}}
        elif "projects(" in query:
            data = {"projects": {"nodes": [{"id": "proj_1", "name": "Swarmboard"}]}}
        elif "team(id:" in query:
            data = {"team": {"states": {"nodes": MOCK_STATES}}}
        elif "issueCreate" in query:
            inp = variables["input"]
            srv.sequence += 1
            issue = {"id": f"lin-issue-{srv.sequence}",
                     "identifier": f"NER-{srv.sequence}",
                     "title": inp.get("title", ""),
                     "description": inp.get("description", ""),
                     "updatedAt": now_ms_iso(),
                     "stateName": "Todo",
                     "teamId": inp.get("teamId"), "projectId": inp.get("projectId")}
            srv.issues.append(issue)
            data = {"issueCreate": {"success": True,
                                   "issue": {"id": issue["id"], "identifier": issue["identifier"]}}}
        elif "issueUpdate" in query:
            iid = variables["id"]
            inp = variables["input"]
            hits = [i for i in srv.issues if i["id"] == iid]
            if not hits:
                data = {"issueUpdate": {"success": False, "issue": None}}
            else:
                i = hits[0]
                srv.updates.append({"id": iid, "input": inp})
                if "title" in inp:
                    i["title"] = inp["title"]
                if "description" in inp:
                    i["description"] = inp["description"]
                if inp.get("stateId"):
                    names = {s["id"]: s["name"] for s in MOCK_STATES}
                    i["stateName"] = names[inp["stateId"]]
                i["updatedAt"] = now_ms_iso()
                data = {"issueUpdate": {"success": True, "issue": {"id": iid}}}
        elif "issues(" in query:
            since = ((variables.get("filter") or {}).get("updatedAt") or {}).get("gte", "")
            nodes = [issue_view(i) for i in sorted(srv.issues, key=lambda x: x["updatedAt"])
                     if i["updatedAt"] >= since]
            data = {"issues": {"nodes": nodes,
                               "pageInfo": {"hasNextPage": False, "endCursor": None}}}
        else:
            self._send(200, {"errors": [{"message": f"mock: unhandled query {query[:60]}"}]})
            return
        self._send(200, {"data": data})

    def _send(self, code, obj):
        payload = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class ConnectorTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="swrm-conn-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = os.path.join(self.tmp, "board.db")
        self.run_swrm("init", "--db", self.db)

    def run_swrm(self, *args, expect_ok=True):
        env = dict(os.environ, KANBAN_DB=self.db, KANBAN_ACTOR="tester")
        env.pop("SWRM_LINEAR_TOKEN", None)
        p = subprocess.run([sys.executable, SWRM, *args],
                           capture_output=True, text=True, env=env, timeout=60, cwd=self.tmp)
        if expect_ok and p.returncode != 0:
            raise AssertionError(f"swrm {' '.join(args)} failed rc={p.returncode}\n"
                                  f"stdout: {p.stdout}\nstderr: {p.stderr}")
        return p

    def get_tasks(self):
        return {t["title"]: t for t in
                json.loads(self.run_swrm("ls", "--json").stdout)}


class TestConnectorConfig(ConnectorTestCase):
    def test_add_list_pause_resume_rm(self):
        self.run_swrm("connector", "add", "linear", "werk",
                      "--key", "team=NER", "--key", "project=Swarmboard",
                      "--map", "blocked=Blocked")
        listing = json.loads(self.run_swrm("connector", "ls", "--json").stdout)["connectors"]
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["team"], "NER")
        self.assertFalse(listing[0]["paused"])

        self.run_swrm("connector", "pause", "werk")
        listing = json.loads(self.run_swrm("connector", "ls", "--json").stdout)["connectors"]
        self.assertTrue(listing[0]["paused"])

        self.run_swrm("connector", "resume", "werk")
        self.run_swrm("connector", "rm", "werk")
        self.assertEqual(json.loads(self.run_swrm("connector", "ls", "--json").stdout)["connectors"], [])

    def test_add_rejects_bad_input(self):
        p = self.run_swrm("connector", "add", "linear", "x", "--key", "bogus=1", expect_ok=False)
        self.assertEqual(p.returncode, 2)
        p = self.run_swrm("connector", "add", "linear", "x", "--map", "geenstatus=Todo", expect_ok=False)
        self.assertEqual(p.returncode, 2)
        p = self.run_swrm("connector", "add", "linear", "x")
        p = self.run_swrm("connector", "add", "linear", "x", expect_ok=False)  # duplicate name
        self.assertEqual(p.returncode, 1)

    def test_auth_writes_mode_600_secrets(self):
        self.run_swrm("connector", "add", "linear", "werk")
        self.run_swrm("connector", "auth", "werk", "--token", "lin_test_token")
        secrets_path = os.path.join(self.tmp, "connectors.secrets.json")
        self.assertTrue(os.path.exists(secrets_path))
        self.assertEqual(os.stat(secrets_path).st_mode & 0o777, 0o600)
        with open(secrets_path) as f:
            self.assertEqual(json.load(f)["werk"]["token"], "lin_test_token")
        p = self.run_swrm("connector", "auth", "werk", expect_ok=False)
        self.assertEqual(p.returncode, 2)  # no --token/--token-file

    def test_external_ref_migration(self):
        # simulate a pre-NER-331 board: drop the column, then let connect() re-add it
        con = sqlite3.connect(self.db)
        con.execute("ALTER TABLE tasks DROP COLUMN external_ref")  # sqlite >= 3.35
        con.commit()
        con.close()
        tasks = self.get_tasks()  # any command calls connect() -> migration runs
        self.assertEqual(tasks, {})
        con = sqlite3.connect(self.db)
        cols = [r[1] for r in con.execute("PRAGMA table_info(tasks)")]
        con.close()
        self.assertIn("external_ref", cols)


class TestLinearSync(ConnectorTestCase):
    def start_mock(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), MockLinearHandler)
        srv.issues = []
        srv.requests = []
        srv.updates = []
        srv.sequence = 0
        srv.require_token = "lin_test_token"
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.shutdown)
        self.addCleanup(srv.server_close)
        port = srv.server_address[1]
        return srv, f"http://127.0.0.1:{port}"

    def setUp(self):
        super().setUp()
        self.srv, self.api = self.start_mock()
        self.run_swrm("connector", "add", "linear", "werk",
                      "--key", f"api_base={self.api}",
                      "--key", "team=NER", "--key", "project=Swarmboard")
        self.run_swrm("connector", "auth", "werk", "--token", "lin_test_token")

    def sync(self):
        return self.run_swrm("connector", "sync", "werk", "--json")

    def test_two_way_sync_cycle(self):
        self.run_swrm("add", "Sync taak")
        before = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        time.sleep(0.05)
        res = json.loads(self.sync().stdout)["synced"][0]
        # push: task -> new Linear issue
        self.assertEqual(res["created_issues"], 1, res)
        tasks = self.get_tasks()
        task = tasks["Sync taak"]
        self.assertTrue(task["external_ref"], "external_ref must be set after push")
        issue = self.srv.issues[0]
        self.assertEqual(issue["title"], "Sync taak")
        self.assertEqual(issue["teamId"], "team_1")
        self.assertEqual(issue["projectId"], "proj_1")

        # Linear-side change -> board (pull, within one cycle)
        issue["stateName"] = "In Progress"
        issue["updatedAt"] = now_ms_iso()
        res = json.loads(self.sync().stdout)["synced"][0]
        self.assertEqual(res["pulled_updated"], 1, res)
        tasks = self.get_tasks()
        self.assertEqual(tasks["Sync taak"]["status"], "doing")

        events = json.loads(self.run_swrm("events", "--json").stdout)
        pull_events = [e for e in events if e["actor"] == "connector:werk"]
        self.assertTrue(pull_events, "pull changes must be logged as events")

        # board-side change -> Linear (push)
        self.run_swrm("move", task["id"], "done")
        res = json.loads(self.sync().stdout)["synced"][0]
        self.assertEqual(res["updated_issues"], 1, res)
        self.assertEqual(issue["stateName"], "Done")  # status_map: done -> Done
        state_updates = [u for u in self.srv.updates if u["input"].get("stateId")]
        self.assertEqual(state_updates[-1]["input"]["stateId"], "s4")

        # idempotency: syncing again without changes pushes/pulls nothing new
        res = json.loads(self.sync().stdout)["synced"][0]
        self.assertEqual(res["pushed"], 0, res)
        self.assertEqual(res["pulled_updated"], 0, res)
        self.assertEqual(len(self.srv.updates), 1)  # exactly one issueUpdate ever

    def test_pull_new_opt_in(self):
        self.srv.issues.append({"id": "lin-existing", "identifier": "NER-42",
                                "title": "Alleen in Linear", "description": "x",
                                "updatedAt": now_ms_iso(), "stateName": "Done",
                                "teamId": "team_1", "projectId": "proj_1"})
        res = json.loads(self.sync().stdout)["synced"][0]
        self.assertEqual(res["pulled_created"], 0)
        self.assertEqual(res["pull_skipped"], 1)
        self.assertNotIn("Alleen in Linear", self.get_tasks())

        self.run_swrm("connector", "add", "linear", "importer",
                      "--key", f"api_base={self.api}", "--key", "team=NER",
                      "--key", "pull_new=true")
        self.run_swrm("connector", "auth", "importer", "--token", "lin_test_token")
        importer = json.loads(
            self.run_swrm("connector", "sync", "importer", "--json").stdout)["synced"][0]
        self.assertGreaterEqual(importer["pulled_created"], 1)
        self.assertIn("Alleen in Linear", self.get_tasks())

    def test_unknown_team_fails_with_error_recorded(self):
        self.run_swrm("connector", "add", "linear", "fout",
                      "--key", f"api_base={self.api}", "--key", "team=NOPE")
        self.run_swrm("connector", "auth", "fout", "--token", "lin_test_token")
        p = self.run_swrm("connector", "sync", "fout", expect_ok=False)
        self.assertEqual(p.returncode, 1)
        status = json.loads(self.run_swrm("connector", "status", "fout", "--json").stdout)
        self.assertIn("no Linear team matches", status["connectors"][0]["last_error"])

    def test_missing_token_is_a_clear_error(self):
        self.run_swrm("connector", "add", "linear", "tokloos",
                      "--key", f"api_base={self.api}", "--key", "team=NER")
        p = self.run_swrm("connector", "sync", "tokloos", expect_ok=False)
        self.assertEqual(p.returncode, 2)
        self.assertIn("no token", p.stderr)

    def test_full_resync_is_repeatable(self):
        self.run_swrm("add", "Reset taak")
        self.sync()
        first_issue = self.srv.issues[0]
        res = json.loads(self.run_swrm("connector", "sync", "werk", "--full", "--json").stdout)
        # full reset: tasks still exist (external_ref kept) -> update, not a second create
        self.assertEqual(res["synced"][0]["created_issues"], 0)
        self.assertEqual(res["synced"][0]["updated_issues"], 1)
        self.assertEqual(len(self.srv.issues), 1)
        self.assertEqual(first_issue["id"], self.srv.issues[0]["id"])


if __name__ == "__main__":
    unittest.main()
