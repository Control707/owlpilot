import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from owlpilot.core import (OwlPilotError, STATE_LIMIT, initial_state, handle_action, complete_guide,
                           guide_context, chunk_text, derive_priorities, merge_patch, check_budget, fail_request)
from owlpilot.__main__ import main


def apply_merge(target, patch):
    result = copy.deepcopy(target)
    for k, v in patch.items():
        if v is None:
            result.pop(k, None)
        elif isinstance(v, dict):
            result[k] = apply_merge(result.get(k, {}) if isinstance(result.get(k), dict) else {}, v)
        else:
            result[k] = copy.deepcopy(v)
    return result


class AcademicContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = initial_state()
        self.counter = 0
        result = self.act("course.create", {"name": "Synthetic Biology", "isSample": True, "timezone": "America/New_York"})
        self.cid = result["result"]["courseId"]

    def tearDown(self):
        self.tmp.cleanup()

    def act(self, kind, data, aid=None, **kw):
        self.counter += 1
        data = {"domainRevision": self.state["domainRevision"], **data}
        result = handle_action(self.state, {"id": aid or f"a{self.counter}", "action": kind, "data": data}, root=self.root, **kw)
        self.state = result["state"]
        return result

    def import_confirm(self):
        result = self.act("course.import_text", {"courseId": self.cid, "name": "Cell notes", "text": "Cells maintain homeostasis. Membranes regulate transport.\nDiffusion moves particles down a concentration gradient.", "proposals": [{"kind": "topic", "value": "Membrane transport"}]})
        fid = result["result"]["factIds"][0]
        self.act("course.confirm_facts", {"courseId": self.cid, "decisions": [{"factId": fid, "status": "confirmed"}]})
        self.sid = self.state["facts"][fid]["sourceIds"][0]
        return fid

    def guide(self):
        return {"overview": "Review the supplied membrane notes.", "topics": [{"title": "Transport", "summary": "Membranes regulate transport.", "sourceIds": [self.sid]}], "mistakes": [], "practice": [{"question": "Explain diffusion in your own words.", "answer": "Movement down a concentration gradient.", "sourceIds": [self.sid]}], "checklist": ["Explain the process aloud."], "gaps": []}

    def test_empty_bootstrap_and_it_wrapper(self):
        result = handle_action({"revision": 7, "state": {"_page": {"draft": "x"}}}, {"id": "bootstrap", "action": "course.create", "data": {"domainRevision": 0, "name": "History", "isSample": False}}, root=self.root)
        self.assertEqual(result["ifRevision"], 7)
        self.assertEqual(result["patch"]["schemaVersion"], 1)
        self.assertNotIn("_page", result["patch"])
        self.assertEqual(result["state"]["domainRevision"], 1)

    def test_subject_independent_and_sample_isolation(self):
        other = self.act("course.create", {"name": "Art History", "isSample": False})["result"]["courseId"]
        self.assertNotEqual(self.cid, other)
        self.assertTrue(self.state["courses"][self.cid]["isSample"])
        self.assertFalse(self.state["courses"][other]["isSample"])
        self.import_confirm()
        self.assertRaises(OwlPilotError, guide_context, self.state, other)

    def test_create_validation(self):
        for payload in ({"name": "x", "isSample": "yes"}, {"name": "x", "isSample": True, "timezone": "Not/AZone"}, {"name": "", "isSample": True}):
            with self.assertRaises(OwlPilotError):
                self.act("course.create", payload)

    def test_sources_confirm_before_context_and_disk_checksum(self):
        result = self.act("course.import_text", {"courseId": self.cid, "name": "../../evil.txt", "text": "A valid course passage.\nA second line of evidence.", "proposals": [{"kind": "topic", "value": "Evidence"}]})
        material = self.state["materials"][result["result"]["materialId"]]
        self.assertTrue((self.root / material["originalPath"]).is_file())
        self.assertTrue(material["originalPath"].startswith("data/materials/mat_"))
        self.assertNotIn("evil", material["originalPath"])
        self.assertEqual(material["chunks"][0]["lineStart"], 1)
        self.assertEqual(material["chunks"][0]["lineEnd"], 2)
        with self.assertRaises(OwlPilotError):
            guide_context(self.state, self.cid)
        fid = result["result"]["factIds"][0]
        self.act("course.confirm_facts", {"courseId": self.cid, "decisions": [{"factId": fid, "status": "confirmed", "value": "Student amended topic"}]})
        self.assertTrue(self.state["facts"][fid]["userProvided"])
        self.assertIn("sourceChunks", guide_context(self.state, self.cid))

    def test_no_fake_proposals_and_later_explicit_proposal(self):
        r = self.act("course.import_text", {"courseId": self.cid, "name": "Notes", "text": "The material describes a process."})
        self.assertTrue(r["result"]["needsProposal"])
        self.assertEqual(self.state["facts"], {})
        mid = r["result"]["materialId"]
        sid = self.state["materials"][mid]["chunks"][0]["id"]
        r = self.act("course.propose_facts", {"courseId": self.cid, "materialId": mid, "proposals": [{"kind": "topic", "value": "Process", "sourceIds": [sid]}]})
        self.assertEqual(len(r["result"]["factIds"]), 1)

    def test_paste_limit_utf8_and_file_text_limit(self):
        with self.assertRaises(OwlPilotError):
            self.act("course.import_text", {"courseId": self.cid, "name": "Large", "text": "é" * 13000})
        p = self.root / "large.txt"
        p.write_text("a" * 100001)
        with self.assertRaises(OwlPilotError):
            self.act("course.import_file", {"courseId": self.cid, "name": "Large file"}, file_path=p)

    def test_invalid_text_and_action_limits(self):
        for value in ("", "bad\x00text"):
            with self.assertRaises(OwlPilotError):
                self.act("course.import_text", {"courseId": self.cid, "text": value})
        with self.assertRaises(OwlPilotError):
            self.act("course.import_text", {"courseId": self.cid, "text": "a" * 34000})

    def test_local_file_is_only_explicit_argument_and_symlink_rejected(self):
        source = self.root / "notes.txt"
        source.write_text("This is a valid small course source.")
        with self.assertRaises(OwlPilotError):
            self.act("course.import_file", {"courseId": self.cid, "path": str(source)})
        link = self.root / "link.txt"
        link.symlink_to(source)
        with self.assertRaises(OwlPilotError):
            self.act("course.import_file", {"courseId": self.cid}, file_path=link)
        self.act("course.import_file", {"courseId": self.cid}, file_path=source)

    def test_destination_symlink_rejected(self):
        external = self.root / "elsewhere"
        external.mkdir()
        (self.root / "data").symlink_to(external, target_is_directory=True)
        with self.assertRaises(OwlPilotError):
            self.act("course.import_text", {"courseId": self.cid, "text": "A course passage."})
        self.assertEqual(list(external.iterdir()), [])

    def test_long_line_chunks_preserve_exact_text(self):
        content = "A" * 5000 + "\nB\n"
        chunks = chunk_text(content, "m")
        self.assertEqual("".join(c["text"] for c in chunks), content)
        self.assertEqual(chunks[0]["lineStart"], 1)
        self.assertEqual(chunks[-1]["lineEnd"], 2)

    def test_deadline_requires_explicit_complete_datetime(self):
        r = self.act("course.import_text", {"courseId": self.cid, "text": "Read chapter one before the seminar.", "proposals": [{"kind": "deadline", "value": {"title": "Seminar", "date": "2099-01-01"}}]})
        fid = r["result"]["factIds"][0]
        self.act("course.confirm_facts", {"courseId": self.cid, "decisions": [{"factId": fid, "status": "confirmed"}]})
        self.assertEqual(self.state["priorities"], [])
        self.act("course.confirm_facts", {"courseId": self.cid, "decisions": [{"factId": fid, "status": "confirmed", "value": {"title": "Seminar", "date": "2099-01-01", "time": "09:00", "timezone": "UTC"}}]})
        self.assertEqual(self.state["priorities"][0]["title"], "Seminar")

    def test_invalid_dates(self):
        for val in ({"title": "X", "date": "2025-02-30"}, {"title": "X", "time": "25:61"}, {"title": "X", "timezone": "Fake/Fake"}):
            with self.assertRaises(OwlPilotError):
                self.act("course.import_text", {"courseId": self.cid, "text": "An upcoming assignment is mentioned.", "proposals": [{"kind": "deadline", "value": val}]})

    def test_dedup_before_revision_and_hash_mismatch(self):
        action = {"id": "stable-action", "action": "course.create", "data": {"domainRevision": self.state["domainRevision"], "name": "Math", "isSample": True}}
        r = handle_action(self.state, action, root=self.root)
        replay = handle_action(r["state"], action, root=self.root)
        self.assertEqual(replay["status"], "duplicate")
        self.assertEqual(replay["patch"], {})
        action["data"]["name"] = "Altered"
        with self.assertRaises(OwlPilotError):
            handle_action(r["state"], action, root=self.root)

    def test_stale_revision_and_unknown_action(self):
        with self.assertRaises(OwlPilotError):
            self.act("mistake.add", {"domainRevision": 0, "courseId": self.cid})
        with self.assertRaises(OwlPilotError):
            self.act("external.submit", {"courseId": self.cid})

    def test_mistake_validations_and_inert_content(self):
        base = {"courseId": self.cid, "origin": "graded", "assessment": "Quiz", "question": "Q1", "description": "<script>alert(1)</script>", "feedback": "Review the concept."}
        for points in (-1, float("nan"), True):
            with self.assertRaises(OwlPilotError):
                self.act("mistake.add", {**base, "pointsLost": points})
        for origin in ("live", "timed", "submission"):
            with self.assertRaises(OwlPilotError):
                self.act("mistake.add", {**base, "origin": origin})
        r = self.act("mistake.add", {**base, "pointsLost": 0.5})
        self.assertEqual(self.state["mistakes"][r["result"]["mistakeId"]]["description"], base["description"])
        self.assertEqual(self.state["priorities"][0]["kind"], "mistake")

    def test_guide_reserved_context_and_complete(self):
        self.import_confirm()
        r = self.act("guide.generate", {"courseId": self.cid}, aid="guide1")
        self.assertEqual(r["status"], "running")
        self.assertEqual(r["context"]["requestId"], "guide1")
        with self.assertRaises(OwlPilotError):
            self.act("guide.generate", {"courseId": self.cid})
        done = complete_guide({"revision": 88, "state": self.state}, "guide1", self.guide())
        self.assertEqual(done["ifRevision"], 88)
        self.assertEqual(done["status"], "succeeded")
        self.assertFalse(done["state"]["guides"][self.cid]["stale"])
        replay = complete_guide(done["state"], "guide1", self.guide())
        self.assertEqual(replay["patch"], {})
        changed = self.guide()
        changed["overview"] = "Changed"
        with self.assertRaises(OwlPilotError):
            complete_guide(done["state"], "guide1", changed)

    def test_unknown_citation_unconfirmed_and_cross_course_rejected(self):
        self.import_confirm()
        self.act("guide.generate", {"courseId": self.cid}, aid="guide1")
        g = self.guide()
        g["topics"][0]["sourceIds"] = ["invented"]
        with self.assertRaises(OwlPilotError):
            complete_guide(self.state, "guide1", g)
        g = self.guide()
        g["mistakes"] = [{"mistakeId": "unknown", "advice": "Study", "sourceIds": [self.sid]}]
        with self.assertRaises(OwlPilotError):
            complete_guide(self.state, "guide1", g)
        g = self.guide()
        g["unsafe"] = "arbitrary"
        with self.assertRaises(OwlPilotError):
            complete_guide(self.state, "guide1", g)

    def test_stale_completion_does_not_replace_current_guide(self):
        self.import_confirm()
        self.act("guide.generate", {"courseId": self.cid}, aid="old-guide")
        self.act("mistake.add", {"courseId": self.cid, "origin": "practice", "assessment": "Practice", "description": "Wrong reasoning", "feedback": "Check evidence"})
        stale = complete_guide(self.state, "old-guide", self.guide())
        self.assertEqual(stale["status"], "stale")
        self.assertNotIn(self.cid, stale["state"]["guides"])
        with self.assertRaises(OwlPilotError):
            complete_guide(stale["state"], "old-guide", self.guide())

    def test_consumer_generation_stales_completion(self):
        self.import_confirm()
        self.act("guide.generate", {"courseId": self.cid}, aid="old-agent")
        self.state["runtime"]["generation"] += 1
        self.assertEqual(complete_guide(self.state, "old-agent", self.guide())["status"], "stale")

    def test_merge_patch_preserves_unrelated_and_page_keys(self):
        before = copy.deepcopy(self.state)
        before["_page"] = {"draft": "keep"}
        before["otherApp"] = {"x": 1}
        r = handle_action(before, {"id": "refresh", "action": "priorities.refresh", "data": {"courseId": self.cid, "domainRevision": before["domainRevision"]}}, root=self.root)
        merged = apply_merge(before, r["patch"])
        self.assertEqual(merged["_page"], before["_page"])
        self.assertEqual(merged["otherApp"], before["otherApp"])
        self.assertNotIn("_page", r["patch"])
        self.assertEqual(merged["domainRevision"], r["state"]["domainRevision"])

    def test_budget_rejects_no_material_write(self):
        self.state["runtime"]["oversized"] = "a" * STATE_LIMIT
        with self.assertRaises(OwlPilotError):
            self.act("course.import_text", {"courseId": self.cid, "text": "A valid passage."})
        self.assertFalse((self.root / "data").exists())

    def test_request_history_prunes_finished_but_keeps_running(self):
        self.state["requests"] = {f"r{i:03}": {"id": f"r{i:03}", "status": "succeeded", "createdAt": f"2026-01-01T00:{i//60:02}:{i%60:02}"} for i in range(150)}
        self.state["requests"]["live"] = {"id": "live", "status": "running", "createdAt": "2000-01-01"}
        self.act("priorities.refresh", {"courseId": self.cid})
        self.assertLessEqual(len(self.state["requests"]), 82)
        self.assertIn("live", self.state["requests"])
        self.assertNotIn("r000", self.state["requests"])

    def test_cli_initial_handle_and_existing_output(self):
        from contextlib import redirect_stdout, redirect_stderr
        statefile = self.root / "state.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["initial", "--out", str(statefile)]), 0)
        actionfile = self.root / "action.json"
        actionfile.write_text(json.dumps({"id": "cli-action", "action": "course.create", "data": {"domainRevision": 0, "name": "History", "isSample": True}}))
        patchfile = self.root / "patch.json"
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["handle", "--state", str(statefile), "--action", str(actionfile), "--out", str(patchfile)]), 0)
        self.assertTrue(patchfile.is_file())
        self.assertIn("warning", json.loads(out.getvalue()))
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["initial", "--out", str(statefile)]), 2)

    def test_guide_complete_action(self):
        self.import_confirm()
        self.act("guide.generate", {"courseId": self.cid}, aid="guide-action")
        result = self.act("guide.complete", {"courseId": self.cid, "requestId": "guide-action", "guide": self.guide()})
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(self.state["requests"]["guide-action"]["status"], "succeeded")
        self.assertIn(self.cid, self.state["guides"])

    def test_explicit_failure_allows_new_request_not_auto_retry(self):
        self.import_confirm()
        self.act("guide.generate", {"courseId": self.cid}, aid="interrupted")
        failed = fail_request(self.state, "interrupted", "Provider unavailable; operator inspected the request.")
        self.state = failed["state"]
        self.assertEqual(failed["status"], "failed")
        self.assertRaises(OwlPilotError, complete_guide, self.state, "interrupted", self.guide())
        self.assertEqual(self.act("guide.generate", {"courseId": self.cid})["status"], "running")

    def test_material_replacement_stales_facts_and_old_context(self):
        fid = self.import_confirm()
        oldmid = self.state["facts"][fid]["materialId"]
        self.act("guide.generate", {"courseId": self.cid}, aid="reserved")
        r = self.act("course.import_text", {"courseId": self.cid, "name": "Updated notes", "text": "Updated notes clarify the course concept.", "replacesMaterialId": oldmid})
        newmid = r["result"]["materialId"]
        self.assertEqual(self.state["materials"][newmid]["revision"], 2)
        self.assertEqual(self.state["facts"][fid]["status"], "stale")
        self.assertRaises(OwlPilotError, guide_context, self.state, self.cid, "reserved")
        self.assertRaises(OwlPilotError, self.act, "course.confirm_facts", {"courseId": self.cid, "decisions": [{"factId": fid, "status": "confirmed"}]})

    def test_combined_state_budget(self):
        self.state["_page"] = {"huge": "a" * (512 * 1024)}
        self.assertRaises(OwlPilotError, check_budget, self.state)

    def test_cross_course_citation(self):
        self.import_confirm()
        sid = self.sid
        other = self.act("course.create", {"name": "History", "isSample": False})["result"]["courseId"]
        with self.assertRaises(OwlPilotError):
            self.act("course.import_text", {"courseId": other, "name": "History", "text": "Historical analysis relies on source evaluation.", "proposals": [{"kind": "topic", "value": "Sources", "sourceIds": [sid]}]})

    def test_encrypted_and_malformed_pdf(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        writer.encrypt("test-password")
        encrypted = self.root / "encrypted.pdf"
        with encrypted.open("wb") as f:
            writer.write(f)
        malformed = self.root / "bad.pdf"
        malformed.write_bytes(b"not a PDF")
        for p in (encrypted, malformed):
            self.assertRaises(OwlPilotError, self.act, "course.import_file", {"courseId": self.cid}, file_path=p)

    def test_pdf_text_scanned_and_page_limit(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject
        def make_pdf(path, text_content=None, pages=1):
            writer = PdfWriter()
            for _ in range(pages):
                page = writer.add_blank_page(width=300, height=300)
                if text_content:
                    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
                    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
                    stream = DecodedStreamObject()
                    stream.set_data(b"BT /F1 12 Tf 20 250 Td (" + text_content.encode("ascii") + b") Tj ET")
                    page[NameObject("/Contents")] = writer._add_object(stream)
            with path.open("wb") as f:
                writer.write(f)
        good = self.root / "good.pdf"
        make_pdf(good, "Course evidence describes membrane transport and diffusion.")
        r = self.act("course.import_file", {"courseId": self.cid, "name": "PDF notes"}, file_path=good)
        mat = self.state["materials"][r["result"]["materialId"]]
        self.assertEqual(mat["chunks"][0]["page"], 1)
        blank = self.root / "blank.pdf"
        make_pdf(blank)
        too_many = self.root / "many.pdf"
        make_pdf(too_many, pages=51)
        for path in (blank, too_many):
            with self.assertRaises(OwlPilotError):
                self.act("course.import_file", {"courseId": self.cid}, file_path=path)


if __name__ == "__main__":
    unittest.main()
