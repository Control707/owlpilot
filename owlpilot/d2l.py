"""Read-only D2L Brightspace connector for OwlPilot.

The student signs in to D2L in a normal browser window (SSO/MFA included); the agent never sees
the password. The browser session is saved to data/d2l/session.json (gitignored, owner-only) and
reused for read-only GET requests to D2L's own API. Nothing is ever submitted, posted, opened as
an attempt, or changed in D2L.

Commands:
  python -m owlpilot.d2l login                  open D2L and wait for the student to sign in
  python -m owlpilot.d2l sync  --state S --out P [--action A]
  python -m owlpilot.d2l apply --state S --snapshot F --out P [--action A]   (offline/testing)
The patch is applied by the operator with `it patch owlpilot --file P --if-revision N`.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .core import (ROOT, OwlPilotError, bump_course, check_budget, chunk_text, derive_priorities,
                   encoded, merge_patch, save_material, stamp, unpack_state, validate_deadline)

BASE = os.environ.get("OWLPILOT_D2L_URL", "https://kennesaw.view.usg.edu").rstrip("/")
EDGE = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
DATA = ROOT / "data" / "d2l"
SESSION = DATA / "session.json"
TZ = "America/New_York"
MISTAKE_THRESHOLD = 80  # graded items below this percentage enter the mistake log
COURSE_TEXT_LIMIT = 7000
MAX_COURSES = 8


class D2LError(Exception):
    pass


class NeedsLogin(D2LError):
    pass


def _clean(value, limit):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _browser(p, headless):
    """Use Playwright's Chromium if installed; otherwise fall back to Chrome or Edge on this machine."""
    custom = os.environ.get("OWLPILOT_BROWSER")
    if custom:
        return p.chromium.launch(headless=headless, executable_path=custom)
    try:
        return p.chromium.launch(headless=headless)
    except Exception:
        for channel in ("chrome", "msedge"):
            try:
                return p.chromium.launch(headless=headless, channel=channel)
            except Exception:
                continue
        if Path(EDGE).exists():
            return p.chromium.launch(headless=headless, executable_path=EDGE)
        raise D2LError("No browser found. Run: .venv/bin/python -m playwright install chromium")


def _get_json(ctx, path):
    response = ctx.request.get(BASE + path, timeout=30000)
    if response.status in (401, 403):
        raise NeedsLogin(f"D2L refused {path.split('?')[0]} ({response.status}).")
    if response.status != 200:
        raise D2LError(f"HTTP {response.status}")
    if "json" not in (response.headers.get("content-type") or ""):
        raise NeedsLogin("D2L answered with a sign-in page instead of data.")
    return response.json()


def _versions(ctx):
    found = {item["ProductCode"]: item["LatestVersion"] for item in _get_json(ctx, "/d2l/api/versions/")}
    if "lp" not in found or "le" not in found:
        raise D2LError("D2L did not report its API versions.")
    return found["lp"], found["le"]


def _save_session(ctx):
    DATA.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    ctx.storage_state(path=str(SESSION))
    os.chmod(SESSION, 0o600)


def login(timeout=600):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = _browser(p, False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(BASE + "/d2l/home")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                lp, _ = _versions(ctx)
                who = _get_json(ctx, f"/d2l/api/lp/{lp}/users/whoami")
                _save_session(ctx)
                browser.close()
                return {"status": "connected", "user": _clean(who.get("FirstName"), 60), "site": BASE}
            except D2LError:
                pass
            try:
                page.wait_for_timeout(3000)
            except Exception:
                break
        browser.close()
    return {"status": "not_connected", "reason": "Sign-in was not completed or the window was closed."}


def _paged_enrollments(ctx, lp):
    items, bookmark = [], None
    for _ in range(10):
        query = "?orgUnitTypeId=3" + (f"&bookmark={bookmark}" if bookmark else "")
        page = _get_json(ctx, f"/d2l/api/lp/{lp}/enrollments/myenrollments/{query}")
        items.extend(page.get("Items", []))
        info = page.get("PagingInfo") or {}
        if not info.get("HasMoreItems"):
            break
        bookmark = info.get("Bookmark")
    return items


def _current(enrollments, now):
    chosen = []
    for e in enrollments:
        access = e.get("Access") or {}
        if not access.get("CanAccess") or not access.get("IsActive", True):
            continue
        start, end = _iso(access.get("StartDate")), _iso(access.get("EndDate"))
        if end and end < now - timedelta(days=21):
            continue
        if start and start > now + timedelta(days=45):
            continue
        chosen.append(e)
    chosen.sort(key=lambda e: (e.get("Access") or {}).get("LastAccessed") or "", reverse=True)
    return chosen[:MAX_COURSES]


def collect():
    """Read-only GET requests against D2L using the saved browser session."""
    if not SESSION.exists():
        raise NeedsLogin("No saved D2L sign-in yet.")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = _browser(p, True)
        ctx = browser.new_context(storage_state=str(SESSION))
        try:
            lp, le = _versions(ctx)
            who = _get_json(ctx, f"/d2l/api/lp/{lp}/users/whoami")
            enrollments = _current(_paged_enrollments(ctx, lp), datetime.now(timezone.utc))
            courses = []
            for e in enrollments:
                org = e["OrgUnit"]
                ou = int(org["Id"])
                record = {"ou": ou, "name": org.get("Name", ""), "code": org.get("Code", ""), "errors": {}}
                for key, path in (("assignments", f"/d2l/api/le/{le}/{ou}/dropbox/folders/"),
                                  ("quizzes", f"/d2l/api/le/{le}/{ou}/quizzes/"),
                                  ("news", f"/d2l/api/le/{le}/{ou}/news/"),
                                  ("grades", f"/d2l/api/le/{le}/{ou}/grades/values/myGradeValues/"),
                                  ("content", f"/d2l/api/le/{le}/{ou}/content/toc")):
                    try:
                        record[key] = _get_json(ctx, path)
                    except D2LError as exc:
                        record["errors"][key] = str(exc)
                courses.append(record)
            _save_session(ctx)
        finally:
            browser.close()
    return {"syncedAt": stamp(), "site": BASE, "user": _clean(who.get("FirstName"), 60), "courses": courses}


def _local(dt):
    return dt.astimezone(ZoneInfo(TZ))


def _due_items(course):
    items = []
    for folder in course.get("assignments") or []:
        items.append(("Assignment", folder.get("Name"), _iso(folder.get("DueDate")),
                      ((folder.get("CustomInstructions") or {}).get("Text"))))
    quizzes = course.get("quizzes")
    for quiz in quizzes.get("Objects", []) if isinstance(quizzes, dict) else []:
        items.append(("Quiz", quiz.get("Name"), _iso(quiz.get("DueDate") or quiz.get("EndDate")), None))
    items.sort(key=lambda x: (x[2] is None, x[2] or datetime.max.replace(tzinfo=timezone.utc)))
    return items


def render_course(course):
    """Plain-text, line-addressable snapshot plus structured items keyed by line number."""
    lines, deadlines, topics, grades = [], [], [], []
    size = 0
    full = False

    def add(line, item=None):
        nonlocal size, full
        if full:
            return
        line = line.rstrip()
        if size + len(line) + 1 > COURSE_TEXT_LIMIT:
            lines.append("… more items are in D2L; this snapshot was shortened to stay within limits.")
            full = True
            return
        lines.append(line)
        size += len(line) + 1
        if item is not None:
            item["line"] = len(lines)

    add(f"D2L COURSE SNAPSHOT — {_clean(course['name'], 160)} ({_clean(course['code'], 80)})")
    add(f"Read-only copy synced from {BASE}. Dates shown in {TZ}.")
    add("")
    add("ASSIGNMENTS, QUIZZES AND DUE DATES")
    due_items = _due_items(course)
    for kind, name, due, notes in due_items[:30]:
        name = _clean(name, 160)
        if not name:
            continue
        when = _local(due).strftime("%a %b %d, %Y %I:%M %p") if due else "no due date listed"
        item = {"kind": kind, "title": f"{kind}: {name}", "due": due}
        add(f"{kind}: {name} — due {when}", item if due else None)
        if due:
            deadlines.append(item)
        if notes:
            add(f"  Instructions: {_clean(notes, 300)}")
    if not due_items:
        add("No assignments or quizzes were visible.")
    add("")
    add("RECENT ANNOUNCEMENTS")
    news = sorted(course.get("news") or [], key=lambda n: n.get("StartDate") or "", reverse=True)[:6]
    for n in news:
        when = _iso(n.get("StartDate"))
        add(f"{_clean(n.get('Title'), 160)} ({_local(when).strftime('%b %d') if when else 'undated'})")
        add(f"  {_clean((n.get('Body') or {}).get('Text'), 700)}")
    if not news:
        add("No announcements were visible.")
    add("")
    add("GRADED FEEDBACK")
    for g in course.get("grades") or []:
        if g.get("GradeObjectType") not in (1, None):
            continue  # skip categories, calculated and formula totals
        name = _clean(g.get("GradeObjectName"), 160)
        num, den = g.get("PointsNumerator"), g.get("PointsDenominator")
        comment = _clean((g.get("Comments") or {}).get("Text"), 400)
        score = f"{num:g}/{den:g}" if isinstance(num, (int, float)) and isinstance(den, (int, float)) else _clean(g.get("DisplayedGrade"), 40) or "no score"
        item = {"id": str(g.get("GradeObjectIdentifier") or name), "name": name, "num": num, "den": den, "comment": comment}
        add(f"{name}: {score}" + (f" — feedback: {comment}" if comment else ""), item)
        grades.append(item)
    if not course.get("grades"):
        add("No released grades were visible.")
    add("")
    add("COURSE CONTENT OUTLINE")

    def walk(modules, depth):
        for module in modules or []:
            title = _clean(module.get("Title"), 160)
            if title:
                item = {"title": title}
                add(("  " * depth) + "Module: " + title, item)
                if depth == 0:
                    topics.append(item)
            for topic in (module.get("Topics") or [])[:15]:
                add(("  " * (depth + 1)) + "• " + _clean(topic.get("Title"), 160))
            if depth < 1:
                walk(module.get("Modules"), depth + 1)

    walk((course.get("content") or {}).get("Modules") if isinstance(course.get("content"), dict) else [], 0)
    if course.get("errors"):
        add("")
        add("Not visible in this sync: " + ", ".join(sorted(course["errors"])) + ".")
    return "\n".join(lines) + "\n", deadlines, topics, grades


def _chunk_for(chunks, line):
    for chunk in chunks:
        if chunk["lineStart"] <= line <= chunk["lineEnd"]:
            return chunk["id"]
    return chunks[-1]["id"]


def apply_snapshot(document, snapshot, action_id=None, write_files=True):
    state, it_revision = unpack_state(document)
    before = copy.deepcopy(state)
    if action_id and state["requests"].get(action_id, {}).get("status") == "succeeded":
        return {"status": "duplicate", "patch": {}, "ifRevision": it_revision}
    storage = []
    for c in snapshot.get("courses", []):
        ou = int(c["ou"])
        cid = f"d2l_{ou}"
        name = _clean(c.get("name"), 200) or f"D2L course {ou}"
        if cid not in state["courses"]:
            state["courses"][cid] = {"id": cid, "name": name, "code": _clean(c.get("code"), 80), "isSample": False,
                                     "timezone": TZ, "revision": 1, "source": "d2l", "d2lOrgUnitId": ou}
            state["courseOrder"].append(cid)
        else:
            state["courses"][cid].update({"name": name, "code": _clean(c.get("code"), 80)})
        text, deadlines, topics, grades = render_course(c)
        raw = text.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        old = [m for m in state["materials"].values() if m.get("courseId") == cid and m.get("source") == "d2l"]
        mid = f"mat_d2l_{ou}_{digest[:12]}"
        chunks = chunk_text(text, mid)
        unchanged = bool(old) and all(m.get("sha256") == digest for m in old)
        for m in ([] if unchanged else old):
            state["materials"].pop(m["id"], None)
            for fid in [f for f, fact in state["facts"].items() if fact.get("materialId") == m["id"] and fact.get("proposedBy") == "d2l"]:
                state["facts"].pop(fid)
        material = {"id": mid, "courseId": cid, "name": "D2L course snapshot", "sha256": digest, "revision": 1,
                    "extractionStatus": "extracted", "chunks": chunks, "source": "d2l", "syncedAt": snapshot.get("syncedAt"),
                    "originalPath": f"data/materials/{mid}/original.txt", "textPath": f"data/materials/{mid}/extracted.txt"}
        if not unchanged:
            state["materials"][mid] = material
            storage.append((material, raw, text))
        else:
            chunks = old[0]["chunks"]
        for d in deadlines:
            if "line" not in d:
                continue
            local = _local(d["due"])
            value = validate_deadline({"title": _clean(d["title"], 300), "date": local.date().isoformat(),
                                       "time": local.strftime("%H:%M"), "timezone": TZ})
            fid = "fact_d2l_" + hashlib.sha256(f"{ou}|{d['title']}|{d['due'].isoformat()}".encode()).hexdigest()[:16]
            state["facts"][fid] = {"id": fid, "courseId": cid, "materialId": mid, "materialRevision": 1, "kind": "deadline",
                                   "value": value, "sourceIds": [_chunk_for(chunks, d["line"])], "status": "confirmed",
                                   "revision": 1, "proposedBy": "d2l"}
        for t in [t for t in topics if "line" in t][:12]:
            fid = "fact_d2l_" + hashlib.sha256(f"{ou}|topic|{t['title']}".encode()).hexdigest()[:16]
            state["facts"][fid] = {"id": fid, "courseId": cid, "materialId": mid, "materialRevision": 1, "kind": "topic",
                                   "value": t["title"], "sourceIds": [_chunk_for(chunks, t["line"])], "status": "confirmed",
                                   "revision": 1, "proposedBy": "d2l"}
        work = []
        for kind, name, due, _notes in _due_items(c):
            if name and due:
                work.append({"kind": kind, "title": _clean(name, 200), "due": due.isoformat()})
        scored = []
        for g in grades:
            num, den = g["num"], g["den"]
            pct = round(100 * num / den, 1) if isinstance(num, (int, float)) and isinstance(den, (int, float)) and den else None
            scored.append({"name": g["name"], "score": f"{num:g}/{den:g}" if pct is not None else "", "percent": pct,
                           "feedback": g["comment"][:300]})
            if "line" not in g or pct is None or pct >= MISTAKE_THRESHOLD or not g["name"]:
                continue
            mid_key = "mistake_d2l_" + hashlib.sha256(f"{ou}|{g['id']}".encode()).hexdigest()[:16]
            existing = state["mistakes"].get(mid_key, {})
            state["mistakes"][mid_key] = {**existing, "id": mid_key, "courseId": cid, "origin": "graded", "assessment": g["name"],
                                          "question": "", "description": f"Scored {num:g} of {den:g} ({pct:g}%).",
                                          "feedback": g["comment"] or "No written feedback was released in D2L. Add your own note about what went wrong.",
                                          "sourceIds": [_chunk_for(chunks, g["line"])], "pointsLost": round(den - num, 2),
                                          "revision": existing.get("revision", 0) + 1, "source": "d2l", "percent": pct}
            if mid_key not in state["mistakeOrder"]:
                state["mistakeOrder"].append(mid_key)
        news_items = [{"title": _clean(n.get("Title"), 200), "date": (n.get("StartDate") or "")[:10],
                       "body": _clean((n.get("Body") or {}).get("Text"), 600)}
                      for n in sorted(c.get("news") or [], key=lambda n: n.get("StartDate") or "", reverse=True)[:5]]
        state["coursework"][cid] = {"work": sorted(work, key=lambda w: w["due"])[:40], "grades": scored[:40], "news": news_items,
                                    "topics": [t["title"] for t in topics][:30], "syncedAt": snapshot.get("syncedAt")}
        if not unchanged:
            bump_course(state, cid)
    errors = sum(len(c.get("errors") or {}) for c in snapshot.get("courses", []))
    state["runtime"]["d2l"] = {"status": "synced", "syncedAt": snapshot.get("syncedAt"), "site": snapshot.get("site", BASE),
                               "user": snapshot.get("user", ""), "courses": len(snapshot.get("courses", [])), "unavailable": errors}
    if action_id:
        state["requests"][action_id] = {"id": action_id, "action": "d2l.sync", "status": "succeeded", "createdAt": stamp(),
                                        "courseId": None, "result": {"courses": len(snapshot.get("courses", []))}}
    state["domainRevision"] += 1
    state["priorities"] = derive_priorities(state)
    check_budget(state)
    if write_files:
        for item in storage:
            save_material(ROOT, *item)
    return {"status": "succeeded", "patch": merge_patch(before, state), "ifRevision": it_revision,
            "courses": len(snapshot.get("courses", [])), "unavailable": errors}


def status_patch(document, status, reason, action_id=None):
    state, it_revision = unpack_state(document)
    before = copy.deepcopy(state)
    state["runtime"]["d2l"] = {**state["runtime"].get("d2l", {}), "status": status, "message": _clean(reason, 300), "checkedAt": stamp()}
    if action_id:
        state["requests"][action_id] = {"id": action_id, "action": "d2l.sync", "status": status, "createdAt": stamp(),
                                        "courseId": None, "error": _clean(reason, 300)}
    state["domainRevision"] += 1
    return {"status": status, "patch": merge_patch(before, state), "ifRevision": it_revision}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_new(path, value):
    p = Path(path)
    if p.exists():
        raise OwlPilotError("Output already exists; choose a new filename.")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("xb") as f:
        f.write(encoded(value) + b"\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only D2L sync for OwlPilot. Never submits, posts or changes anything in D2L.")
    sub = parser.add_subparsers(dest="command", required=True)
    log = sub.add_parser("login", help="Open D2L in a browser window and wait for the student to sign in.")
    log.add_argument("--timeout", type=int, default=600)
    for name in ("sync", "apply"):
        cmd = sub.add_parser(name, help="Read D2L (sync) or a saved snapshot (apply) and write an It merge patch.")
        cmd.add_argument("--state", required=True, help="`it state owlpilot` output.")
        cmd.add_argument("--out", required=True, help="New patch filename.")
        cmd.add_argument("--action", help="Saved d2l.sync It action JSON, for deduplication.")
        if name == "apply":
            cmd.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "login":
            print(json.dumps(login(args.timeout)))
            return 0
        document = _load(args.state)
        action_id = _load(args.action).get("id") if args.action else None
        if args.command == "apply":
            snapshot = _load(args.snapshot)
        else:
            try:
                snapshot = collect()
            except NeedsLogin as exc:
                result = status_patch(document, "needs_login", f"Sign in to D2L to sync. {exc}")
                _write_new(args.out, result["patch"])
                print(json.dumps({"status": "needs_login", "patchPath": str(Path(args.out).resolve()),
                                  "requiresItRevision": result["ifRevision"],
                                  "next": "Run `python -m owlpilot.d2l login`, then sync again. Do not ack the action yet."}))
                return 3
            DATA.mkdir(parents=True, exist_ok=True)
            os.chmod(DATA, 0o700)
            _write_new(DATA / f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json", snapshot)
        result = apply_snapshot(document, snapshot, action_id)
        _write_new(args.out, result["patch"])
        print(json.dumps({"status": result["status"], "patchPath": str(Path(args.out).resolve()),
                          "requiresItRevision": result["ifRevision"], "courses": result.get("courses"),
                          "unavailableSections": result.get("unavailable")}))
        return 0
    except (OwlPilotError, D2LError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
