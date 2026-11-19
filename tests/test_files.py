import io
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from d2l import errors as d2l_errors

from owlpilot import d2l
from owlpilot.core import guide_context, initial_state, validate_state


def pptx(*slides):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, text in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", f'<p:sld><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:sld>')
    return buf.getvalue()


class Response:
    def __init__(self, content):
        self.content = content


class FakeClient:
    _host = "https://school.brightspace.com"

    def __init__(self):
        self.calls = []

    def content_topic_file(self, ou, tid):
        self.calls.append(("topic", tid))
        if tid == 3:
            return Response(b"Syllabus\nGrading: Exams 50%, Homework 30%, Quizzes 20%\nLate work loses 10% per day.\n")
        if tid == 9:
            raise d2l_errors.ForbiddenError(403, "u")
        return Response(pptx("Eigenvalues &amp; eigenvectors", "Diagonalization steps"))

    def assignment_attachment(self, ou, fid, file_id):
        self.calls.append(("att", file_id))
        return Response(b"Homework 4: prove the spectral theorem for 2x2 symmetric matrices.")


def record():
    def topic(tid, title, url, modified):
        return {"TopicId": tid, "Title": title, "Url": url, "TypeIdentifier": "File", "LastModifiedDate": modified}
    return {"content": {"Modules": [{"Title": "Week 5", "Topics": [
                topic(1, "Lecture 5", "/c/lecture5.pptx", "2026-11-10T00:00:00Z"),
                topic(2, "Old video", "/c/clip.mp4", "2026-11-12T00:00:00Z"),
                topic(3, "Course Syllabus", "/c/syllabus.txt", "2026-08-20T00:00:00Z"),
                topic(9, "Locked notes", "/c/locked.pdf", "2026-11-11T00:00:00Z"),
                {**topic(4, "Hidden", "/c/hidden.pdf", "2026-11-13T00:00:00Z"), "IsHidden": True}], "Modules": []}]},
            "assignments": [{"Id": 7, "Name": "HW 4", "DueDate": "2026-12-01T00:00:00Z",
                             "Attachments": [{"FileId": 70, "FileName": "hw4.txt", "Size": 80}]},
                            {"Id": 8, "Name": "HW 1", "DueDate": "2026-09-01T00:00:00Z",
                             "Attachments": [{"FileId": 80, "FileName": "hw1.txt", "Size": 80}]}]}


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(d2l, "FILES", Path(self.tmp.name) / "files")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_pptx_text_extraction(self):
        self.assertIn("Eigenvalues & eigenvectors", d2l.extract_text(pptx("Eigenvalues &amp; eigenvectors"), ".pptx"))
        self.assertEqual(d2l.extract_text(b"not a zip", ".pptx"), "")

    def test_course_files_picks_current_readable_files_and_caches(self):
        client = FakeClient()
        now = datetime(2026, 11, 19, tzinfo=timezone.utc)
        files = d2l.course_files(client, d2l_errors, 101, record(), now)
        titles = [f["title"] for f in files]
        self.assertEqual(titles, ["Lecture 5", "hw4.txt"], "skips video, hidden, forbidden, syllabus and past-due attachments")
        self.assertEqual(files[0]["where"], "Week 5")
        d2l.course_files(client, d2l_errors, 101, record(), now)
        self.assertEqual(sum(1 for c in client.calls if c == ("topic", 1)), 1, "unchanged files are downloaded once")

    def test_posted_syllabus_keeps_grading_lines_first(self):
        sy = d2l.posted_syllabus(FakeClient(), d2l_errors, 101, record())
        self.assertTrue(sy["text"].startswith("GRADING AND POLICY LINES\nGrading: Exams 50%"))
        self.assertIn("/d2l/le/content/101/viewContent/3/View", sy["url"])

    def test_files_and_syllabus_become_cited_evidence(self):
        snap = {"syncedAt": "2026-11-19T00:00:00Z", "site": "https://school.brightspace.com", "timezone": "UTC", "courses": [{
            "ou": 101, "name": "Linear Algebra", "code": "M", "assignments": [], "content": {"Modules": []},
            "files": [{"title": "Lecture 5", "kind": "Course file", "where": "Week 5", "text": "Eigenvalues and eigenvectors.", "truncated": False}],
            "syllabus": {"title": "Syllabus", "term": "", "url": "https://x/s", "text": "Exams 50%", "truncated": False}}]}
        state = initial_state()
        result = d2l.apply_snapshot(state, snap, write_files=False)
        merged = initial_state()
        for key, value in result["patch"].items():
            merged[key] = value if not isinstance(value, dict) else {**merged.get(key, {}), **value}
        validate_state(merged)
        sources = {m["source"] for m in merged["materials"].values()}
        self.assertEqual(sources, {"d2l", "d2l-file", "syllabus"})
        ctx = guide_context(merged, "d2l_101")
        text = " ".join(c["text"] for c in ctx["sourceChunks"].values())
        self.assertIn("Eigenvalues", text)
        self.assertIn("Exams 50%", text)
        self.assertEqual(merged["coursework"]["d2l_101"]["syllabus"]["url"], "https://x/s")
        # A later sync where the file is gone removes its material and fact.
        snap["courses"][0]["files"] = []
        again = d2l.apply_snapshot(merged, snap, write_files=False)
        removed = [k for k, v in again["patch"].get("materials", {}).items() if v is None]
        self.assertEqual(len(removed), 1)


if __name__ == "__main__":
    unittest.main()
