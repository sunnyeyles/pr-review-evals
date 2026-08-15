"""Smoke tests for the routing layer. Run with ``python -m unittest discover``."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tasksvc import api, config, db  # noqa: E402


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.AUDIT_LOG_PATH = os.path.join(self.tmp.name, "audit.log")
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)

        self.member = db.create_user(self.conn, "member@example.com", "member")
        db.issue_token(self.conn, self.member.id, "member-token")
        self.admin = db.create_user(self.conn, "admin@example.com", "admin")
        db.issue_token(self.conn, self.admin.id, "admin-token")

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def request(self, method, path, token="member-token", query=None, body=None):
        return api.handle(
            self.conn,
            api.Request(
                method=method,
                path=path,
                query=query or {},
                headers={"Authorization": f"Bearer {token}"} if token else {},
                body=json.dumps(body).encode() if body is not None else b"",
            ),
        )

    def test_healthz_needs_no_token(self):
        status, _ = api.handle(self.conn, api.Request(method="GET", path="/healthz"))
        self.assertEqual(status, 200)

    def test_unauthenticated_is_rejected(self):
        status, _ = self.request("GET", "/tasks", token=None)
        self.assertEqual(status, 401)

    def test_create_and_list_task(self):
        status, payload = self.request("POST", "/tasks", body={"title": "write docs"})
        self.assertEqual(status, 201)
        created = json.loads(payload)

        status, payload = self.request("GET", "/tasks")
        self.assertEqual(status, 200)
        page = json.loads(payload)
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["id"], created["id"])

    def test_title_is_required(self):
        status, _ = self.request("POST", "/tasks", body={"title": "   "})
        self.assertEqual(status, 422)

    def test_member_cannot_list_all_tasks(self):
        status, _ = self.request("GET", "/tasks", query={"scope": "all"})
        self.assertEqual(status, 403)

    def test_admin_can_list_all_tasks(self):
        status, _ = self.request("GET", "/tasks", token="admin-token", query={"scope": "all"})
        self.assertEqual(status, 200)

    def test_status_transition_is_validated(self):
        _, payload = self.request("POST", "/tasks", body={"title": "ship it"})
        task_id = json.loads(payload)["id"]
        status, _ = self.request(
            "POST", f"/tasks/{task_id}/status", body={"status": "banana"}
        )
        self.assertEqual(status, 422)


if __name__ == "__main__":
    unittest.main()
