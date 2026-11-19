import unittest
from datetime import datetime, timedelta, timezone

from owlpilot.core import initial_state, validate_state, guide_context
from owlpilot.d2l import apply_snapshot, render_course


def snapshot():
    due = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {"syncedAt": "2026-11-19T00:00:00Z", "site": "https://example.test", "user": "Sam", "courses": [{
        "ou": 101, "name": "Linear Algebra I", "code": "MATH-3260-01", "errors": {"quizzes": "HTTP 403"},
        "assignments": [{"Name": "HW 2 <script>alert(1)</script>", "DueDate": due, "CustomInstructions": {"Text": "Sections 2.1-2.4"}}],
        "quizzes": {"Objects": []},
        "news": [{"Title": "Test 1 scope", "StartDate": "2026-11-10T12:00:00Z", "Body": {"Text": "Covers 1.1-2.4."}}],
        "grades": [{"GradeObjectIdentifier": "7", "GradeObjectName": "Quiz 2", "PointsNumerator": 6, "PointsDenominator": 10,
                    "Comments": {"Text": "Check independence before calling it a basis."}},
                   {"GradeObjectIdentifier": "8", "GradeObjectName": "Quiz 1", "PointsNumerator": 10, "PointsDenominator": 10, "Comments": {"Text": ""}}],
        "content": {"Modules": [{"Title": "Systems of equations", "Topics": [{"Title": "Row reduction"}], "Modules": []}]}}]}


class D2LSyncTests(unittest.TestCase):
    def test_snapshot_creates_cited_course_records(self):
        result = apply_snapshot({"state": initial_state(), "revision": 4}, snapshot(), "act1", write_files=False)
        self.assertEqual(result["ifRevision"], 4)
        state = initial_state()
        def merge(a, b):
            for k, v in b.items():
                if v is None: a.pop(k, None)
                elif isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)
                else: a[k] = v
        merge(state, result["patch"])
        validate_state(state)
        self.assertIn("d2l_101", state["courses"])
        self.assertFalse(state["courses"]["d2l_101"]["isSample"])
        kinds = sorted(f["kind"] for f in state["facts"].values())
        self.assertEqual(kinds, ["deadline", "topic"])
        self.assertTrue(all(f["status"] == "confirmed" and f["sourceIds"] for f in state["facts"].values()))
        self.assertEqual(len(state["mistakes"]), 1, "only graded items with points lost and feedback become mistakes")
        self.assertEqual(state["runtime"]["d2l"]["status"], "synced")
        self.assertEqual(state["requests"]["act1"]["status"], "succeeded")
        context = guide_context(state, "d2l_101")
        self.assertTrue(context["sourceChunks"])

    def test_repeat_sync_is_idempotent(self):
        state = initial_state()
        first = apply_snapshot(state, snapshot(), None, write_files=False)
        def merge(a, b):
            for k, v in b.items():
                if v is None: a.pop(k, None)
                elif isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)
                else: a[k] = v
        merge(state, first["patch"])
        second = apply_snapshot(state, snapshot(), None, write_files=False)
        self.assertNotIn("materials", second["patch"])
        self.assertEqual(len(state["mistakes"]), 1)

    def test_rendered_text_is_plain_and_bounded(self):
        text, deadlines, topics, grades = render_course(snapshot()["courses"][0])
        self.assertIn("HW 2", text)
        self.assertIn("Not visible in this sync: quizzes", text)
        self.assertLess(len(text), 9500)
        self.assertEqual(len(deadlines), 1)


if __name__ == "__main__":
    unittest.main()
