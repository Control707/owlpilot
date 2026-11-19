import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from d2l import config as d2l_config
from d2l import errors as d2l_errors

from owlpilot import d2l, remote
from owlpilot.core import OwlPilotError, initial_state


class FakeClient:
    """Stands in for d2l.client.D2LClient; records that only read methods are used."""
    def __init__(self, fail=None):
        self.fail = fail or {}
        now = datetime.now(timezone.utc)
        self.enrollments = [
            {"OrgUnit": {"Id": 101, "Name": "Linear Algebra", "Code": "MATH-1", "Type": {"Id": 3, "Code": "Course Offering"}},
             "Access": {"CanAccess": True, "IsActive": True, "LastAccessed": "2026-11-18T00:00:00Z"}},
            {"OrgUnit": {"Id": 5, "Name": "Kennesaw State University", "Type": {"Id": 1, "Code": "Organization"}}, "Access": {}},
            {"OrgUnit": {"Id": 77, "Name": "Old course", "Code": "OLD", "Type": {"Id": 3}},
             "Access": {"CanAccess": True, "IsActive": True, "EndDate": (now - timedelta(days=90)).isoformat()}},
        ]

    def whoami(self):
        return {"FirstName": "Sam"}

    def my_enrollments(self, active_only=True):
        return self.enrollments

    def _maybe_fail(self, name):
        if name in self.fail:
            raise self.fail[name]

    def assignments(self, ou):
        self._maybe_fail("assignments")
        return [{"Name": "HW 1", "DueDate": "2026-12-01T04:59:00Z"}]

    def quizzes(self, ou):
        self._maybe_fail("quizzes")
        return [{"Name": "Quiz 1", "DueDate": None, "EndDate": "2026-12-02T04:59:00Z"}]

    def news(self, ou):
        return []

    def grades(self, ou):
        return []

    def content_toc(self, ou):
        return {"Modules": []}


class CollectTests(unittest.TestCase):
    def test_collect_uses_d2l_cli_client_and_filters_courses(self):
        fake = FakeClient(fail={"quizzes": d2l_errors.ForbiddenError(403, "u")})
        with mock.patch.dict("os.environ", {"D2L_HOST": "https://example.brightspace.com", "OWLPILOT_TZ": "America/Chicago"}):
            snap = d2l.collect(client=fake)
        self.assertEqual([c["ou"] for c in snap["courses"]], [101])
        self.assertEqual(snap["site"], "https://example.brightspace.com")
        self.assertEqual(snap["timezone"], "America/Chicago")
        self.assertIn("quizzes", snap["courses"][0]["errors"])

    def test_expired_token_becomes_needs_login(self):
        fake = FakeClient()
        fake.whoami = mock.Mock(side_effect=d2l_errors.TokenExpiredError("expired"))
        with self.assertRaises(d2l.NeedsLogin):
            d2l.collect(client=fake)

    def test_snapshot_uses_its_timezone_and_school(self):
        snap = {"syncedAt": "2026-11-19T00:00:00Z", "site": "https://x.brightspace.com", "school": "X U",
                "timezone": "America/Los_Angeles", "user": "Sam",
                "courses": [{"ou": 9, "name": "Bio", "code": "B", "assignments": [{"Name": "Lab", "DueDate": "2026-12-01T04:59:00Z"}]}]}
        result = d2l.apply_snapshot({"state": initial_state(), "revision": 1}, snap, write_files=False)
        facts = [f for f in result["patch"]["facts"].values() if f["kind"] == "deadline"]
        self.assertEqual(facts[0]["value"]["timezone"], "America/Los_Angeles")
        self.assertEqual(facts[0]["value"]["time"], "20:59")
        self.assertEqual(result["patch"]["runtime"]["d2l"]["school"], "X U")


class SchoolSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        self.patches = [mock.patch.object(d2l_config, "TOKEN_DIR", home),
                        mock.patch.object(d2l_config, "CONFIG_FILE", home / "config.json"),
                        mock.patch.dict("os.environ", {}, clear=False)]
        for p in self.patches:
            p.start()
        import os
        os.environ.pop("D2L_HOST", None)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_preset_and_custom_host(self):
        info = d2l.setup_school(school="ksu")
        self.assertEqual(info["site"], "https://kennesaw.view.usg.edu")
        self.assertEqual(info["school"], "Kennesaw State University")
        info = d2l.setup_school(host="MySchool.Brightspace.com/d2l/home")
        self.assertEqual(info["site"], "https://myschool.brightspace.com")

    def test_rejects_bad_hosts(self):
        for bad in ("http://insecure.example.com", "javascript:alert(1)", "not a url", ""):
            with self.assertRaises(OwlPilotError, msg=bad):
                d2l.setup_school(host=bad)
        with self.assertRaises(OwlPilotError):
            d2l.setup_school(school="nowhere university")


class RemoteTests(unittest.TestCase):
    def test_addresses_accept_strings_and_objects(self):
        self.assertEqual(remote._addresses(["100.64.1.2:4700", {"url": "https://mac.tail1.ts.net/"}, 5]),
                         ["http://100.64.1.2:4700", "https://mac.tail1.ts.net"])

    def test_pair_link_is_rewritten_to_tailnet_address(self):
        fake_status = {"mode": "tailscale", "urls": ["https://mac.tail1.ts.net/p/owlpilot"]}
        site = subprocess.CompletedProcess([], 0, json.dumps({"url": "http://localhost:4700/pair#secretcode"}), "")
        with mock.patch.object(remote, "status", return_value=fake_status), mock.patch.object(remote, "it", return_value=site):
            self.assertEqual(remote.pair_link(), "https://mac.tail1.ts.net/pair#secretcode")

    def test_pair_refused_when_off(self):
        with mock.patch.object(remote, "status", return_value={"mode": "off", "urls": []}):
            with self.assertRaises(OwlPilotError):
                remote.pair_link()

    def test_enable_requires_signed_in_tailscale(self):
        with mock.patch.object(remote, "tailscale_status", return_value={"installed": True, "running": False}):
            with self.assertRaises(OwlPilotError):
                remote.enable()
        with mock.patch.object(remote, "tailscale_status", return_value={"installed": False, "running": False}):
            with self.assertRaises(OwlPilotError):
                remote.enable()


if __name__ == "__main__":
    unittest.main()
