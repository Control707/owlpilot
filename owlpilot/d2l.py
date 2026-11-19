"""Read-only D2L Brightspace connector for OwlPilot, built on d2l-cli.

All D2L access goes through d2l-cli (https://github.com/Aaryan-Kapoor/d2l-cli), which works at any
Brightspace school and owns authentication: `d2l login` opens a normal browser window (SSO/MFA
included; the agent never sees the password) and captures D2L's short-lived API token into
~/.d2l/token.json. When that token expires, d2l-cli silently refreshes it from the saved browser
profile, so the student signs in roughly once per device. Every request is a GET; nothing is ever
submitted, posted, opened as an attempt, or changed in D2L.

Commands:
  python -m owlpilot.d2l setup (--school NAME | --host URL)    choose the Brightspace school
  python -m owlpilot.d2l login                                 open D2L and wait for sign-in
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
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .core import (ROOT, OwlPilotError, bump_course, check_budget, chunk_text, derive_priorities,
                   encoded, merge_patch, save_material, stamp, unpack_state, validate_deadline)

DATA = ROOT / "data" / "d2l"
MISTAKE_THRESHOLD = 80  # graded items below this percentage enter the mistake log
COURSE_TEXT_LIMIT = 7000
MAX_COURSES = 8
LOGIN_TIMEOUT = 600

# Older OwlPilot versions used OWLPILOT_D2L_URL; d2l-cli reads D2L_HOST. Keep the old name working.
if os.environ.get("OWLPILOT_D2L_URL") and not os.environ.get("D2L_HOST"):
    os.environ["D2L_HOST"] = os.environ["OWLPILOT_D2L_URL"]


class D2LError(Exception):
    pass


class NeedsLogin(D2LError):
    pass


class NeedsSetup(D2LError):
    pass


def _lib():
    """Import d2l-cli lazily so tests and the offline `apply` command work without it."""
    try:
        from d2l import auth, client, config, errors, schools
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise D2LError("d2l-cli is not installed. Run ./scripts/setup.sh "
                       "(or: .venv/bin/python -m pip install -r requirements.txt).") from exc
    return auth, client, config, errors, schools


def local_timezone():
    """IANA zone for due dates: OWLPILOT_TZ, else this computer's zone, else UTC."""
    for candidate in (os.environ.get("OWLPILOT_TZ"), os.environ.get("TZ")):
        if candidate:
            try:
                ZoneInfo(candidate)
                return candidate
            except (ZoneInfoNotFoundError, ValueError):
                pass
    try:
        target = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in target:
            name = target.split("zoneinfo/", 1)[1]
            ZoneInfo(name)
            return name
    except (OSError, ZoneInfoNotFoundError, ValueError):
        pass
    return "UTC"


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


# ---------- School configuration (shared with the `d2l` command, in ~/.d2l/config.json) ----------

def school_info():
    """Current school, without network access. Never includes credentials."""
    try:
        auth, _client, config, _errors, schools = _lib()
    except D2LError as exc:
        return {"configured": False, "error": str(exc), "presets": []}
    host = config.get_lms_host(required=False)
    name = config.load_config().get("school") or ""
    if host and not name:
        name = next((p["name"] for p in schools.SCHOOLS.values() if p["lms_host"] == host), "")
    token = auth.token_info()
    return {"configured": bool(host), "site": host or "", "school": name, "token": token.get("status", "not found"),
            "presets": [{"key": k, "name": p["name"], "host": p["lms_host"]} for k, p in schools.SCHOOLS.items()]}


def setup_school(school=None, host=None):
    """Choose the Brightspace school by preset name or by URL. Only https URLs are accepted."""
    _auth, _client, config, _errors, schools = _lib()
    updates = {}
    if school:
        found = schools.find_school(str(school))
        if not found:
            raise OwlPilotError(f"Unknown school '{_clean(school, 60)}'. Pick one from the list or enter your D2L web address.")
        preset = found[1]
        updates = {"school": preset["name"], "lms_host": preset["lms_host"], "syllabus_host": preset["syllabus_host"]}
    elif host:
        raw = _clean(host, 300)
        if "://" in raw and not raw.lower().startswith("https://"):
            raise OwlPilotError("Use your school's https:// D2L address.")
        normalized = config.normalize_host(raw)
        if not normalized or not normalized.startswith("https://") or not re.fullmatch(r"https://[A-Za-z0-9.-]+(:\d+)?", normalized):
            raise OwlPilotError("That does not look like a D2L web address, e.g. https://yourschool.brightspace.com")
        updates = {"school": None, "lms_host": normalized.lower(), "syllabus_host": None}
    else:
        raise OwlPilotError("Choose a school or enter your D2L web address.")
    if os.environ.get("D2L_HOST"):
        raise OwlPilotError("D2L_HOST is set in the environment and overrides this choice; unset it first.")
    config.save_config(updates)
    return school_info()


# ---------- Authentication (owned by d2l-cli) ----------

def _d2l_command():
    local = Path(sys.executable).parent / "d2l"
    return str(local) if local.exists() else shutil.which("d2l")


def login(timeout=LOGIN_TIMEOUT):
    """Run `d2l login`: a browser window opens on this computer and the student signs in themselves."""
    info = school_info()
    if not info["configured"]:
        return {"status": "needs_setup", "reason": "Choose your school first (Settings → School)."}
    command = _d2l_command()
    if not command:
        return {"status": "not_connected", "reason": "The d2l command is missing. Run ./scripts/setup.sh."}
    try:
        proc = subprocess.run([command, "login"], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "not_connected", "reason": "Sign-in was not completed in time."}
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return {"status": "not_connected", "reason": _clean(tail[-1] if tail else "Sign-in was not completed or the window was closed.", 300)}
    try:
        who = _client().whoami()
    except D2LError as exc:
        return {"status": "not_connected", "reason": str(exc)}
    return {"status": "connected", "user": _clean(who.get("FirstName"), 60), "site": info["site"]}


def _token(refresh=True):
    auth, _client_mod, config, errors, _schools = _lib()
    if not config.get_lms_host(required=False):
        raise NeedsSetup("Choose your school first (Settings → School).")
    try:
        return auth.load_token()
    except (errors.TokenExpiredError, errors.TokenNotFoundError) as exc:
        if refresh:
            from d2l.commands.auth_cmd import attempt_auto_login
            if attempt_auto_login():  # silent headless refresh from the saved browser profile
                return auth.load_token()
        raise NeedsLogin("Your D2L sign-in needs renewing.") from exc


def _client(refresh=True):
    auth, client_mod, _config, _errors, _schools = _lib()
    return client_mod.D2LClient(auth.make_session(_token(refresh)))


# ---------- Read-only collection ----------

def _is_course(enrollment):
    unit_type = (enrollment.get("OrgUnit") or {}).get("Type") or {}
    return unit_type.get("Id") == 3 or unit_type.get("Code") == "Course Offering" or unit_type.get("Name") == "Course Offering"


def _current(enrollments, now):
    chosen = []
    for e in enrollments:
        if not _is_course(e):
            continue
        access = e.get("Access") or {}
        if not access.get("CanAccess", True) or not access.get("IsActive", True):
            continue
        start, end = _iso(access.get("StartDate")), _iso(access.get("EndDate"))
        if end and end < now - timedelta(days=21):
            continue
        if start and start > now + timedelta(days=45):
            continue
        chosen.append(e)
    chosen.sort(key=lambda e: (e.get("Access") or {}).get("LastAccessed") or "", reverse=True)
    return chosen[:MAX_COURSES]


def collect(client=None, now=None):
    """Read-only snapshot through d2l-cli. A token that expires mid-sync is refreshed once."""
    _auth, _client_mod, config, errors, _schools = _lib()
    try:
        return _collect(client or _client(), config, errors, now)
    except errors.TokenExpiredError:
        if client is not None:
            raise NeedsLogin("D2L refused the saved sign-in.")
        try:
            return _collect(_client(), config, errors, now)
        except errors.TokenExpiredError as exc:
            raise NeedsLogin("D2L refused the saved sign-in.") from exc
    except errors.ConfigError as exc:
        raise NeedsSetup(str(exc)) from exc
    except errors.D2LError as exc:
        raise D2LError(str(exc)) from exc


def _collect(client, config, errors, now):
    who = client.whoami()
    enrollments = _current(client.my_enrollments(active_only=True), now or datetime.now(timezone.utc))
    courses = []
    for e in enrollments:
        org = e["OrgUnit"]
        ou = int(org["Id"])
        record = {"ou": ou, "name": org.get("Name", ""), "code": org.get("Code", ""), "errors": {}}
        for key, fetch in (("assignments", client.assignments), ("quizzes", client.quizzes), ("news", client.news),
                           ("grades", client.grades), ("content", client.content_toc)):
            try:
                record[key] = fetch(ou)
            except errors.TokenExpiredError:
                raise
            except errors.D2LError as exc:  # 403/404/other API errors: section is just not visible
                record["errors"][key] = _clean(exc, 120)
        courses.append(record)
    site = config.get_lms_host(required=False) or ""
    school = config.load_config().get("school") or ""
    return {"syncedAt": stamp(), "site": site, "school": school, "timezone": local_timezone(),
            "user": _clean(who.get("FirstName"), 60), "courses": courses}


# ---------- Mapping a snapshot to OwlPilot state ----------

def _due_items(course):
    items = []
    for folder in course.get("assignments") or []:
        items.append(("Assignment", folder.get("Name"), _iso(folder.get("DueDate")),
                      ((folder.get("CustomInstructions") or {}).get("Text"))))
    quizzes = course.get("quizzes")
    if isinstance(quizzes, dict):
        quizzes = quizzes.get("Objects", [])
    for quiz in quizzes or []:
        items.append(("Quiz", quiz.get("Name"), _iso(quiz.get("DueDate") or quiz.get("EndDate")), None))
    items.sort(key=lambda x: (x[2] is None, x[2] or datetime.max.replace(tzinfo=timezone.utc)))
    return items


def render_course(course, site="D2L", tz="UTC"):
    """Plain-text, line-addressable snapshot plus structured items keyed by line number."""
    zone = ZoneInfo(tz)
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
    add(f"Read-only copy synced from {_clean(site, 200)}. Dates shown in {tz}.")
    add("")
    add("ASSIGNMENTS, QUIZZES AND DUE DATES")
    due_items = _due_items(course)
    for kind, name, due, notes in due_items[:30]:
        name = _clean(name, 160)
        if not name:
            continue
        when = due.astimezone(zone).strftime("%a %b %d, %Y %I:%M %p") if due else "no due date listed"
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
        add(f"{_clean(n.get('Title'), 160)} ({when.astimezone(zone).strftime('%b %d') if when else 'undated'})")
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


def _snapshot_tz(snapshot):
    tz = snapshot.get("timezone") or local_timezone()
    try:
        ZoneInfo(tz)
        return tz
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC"


def apply_snapshot(document, snapshot, action_id=None, write_files=True):
    state, it_revision = unpack_state(document)
    before = copy.deepcopy(state)
    if action_id and state["requests"].get(action_id, {}).get("status") == "succeeded":
        return {"status": "duplicate", "patch": {}, "ifRevision": it_revision}
    tz = _snapshot_tz(snapshot)
    site = snapshot.get("site") or "D2L"
    storage = []
    for c in snapshot.get("courses", []):
        ou = int(c["ou"])
        cid = f"d2l_{ou}"
        name = _clean(c.get("name"), 200) or f"D2L course {ou}"
        if cid not in state["courses"]:
            state["courses"][cid] = {"id": cid, "name": name, "code": _clean(c.get("code"), 80), "isSample": False,
                                     "timezone": tz, "revision": 1, "source": "d2l", "d2lOrgUnitId": ou}
            state["courseOrder"].append(cid)
        else:
            state["courses"][cid].update({"name": name, "code": _clean(c.get("code"), 80)})
        text, deadlines, topics, grades = render_course(c, site, tz)
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
            local = d["due"].astimezone(ZoneInfo(tz))
            value = validate_deadline({"title": _clean(d["title"], 300), "date": local.date().isoformat(),
                                       "time": local.strftime("%H:%M"), "timezone": tz})
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
        for kind, item_name, due, _notes in _due_items(c):
            if item_name and due:
                work.append({"kind": kind, "title": _clean(item_name, 200), "due": due.isoformat()})
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
    state["runtime"]["d2l"] = {**state["runtime"].get("d2l", {}), "status": "synced", "syncedAt": snapshot.get("syncedAt"),
                               "site": site, "school": _clean(snapshot.get("school"), 120), "timezone": tz,
                               "user": snapshot.get("user", ""), "courses": len(snapshot.get("courses", [])),
                               "unavailable": errors, "message": None}
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


def status_patch(document, status, reason, action_id=None, action="d2l.sync", extra=None):
    state, it_revision = unpack_state(document)
    before = copy.deepcopy(state)
    state["runtime"]["d2l"] = {**state["runtime"].get("d2l", {}), **(extra or {}), "status": status,
                               "message": _clean(reason, 300), "checkedAt": stamp()}
    if action_id:
        failed = status not in ("synced", "connected", "configured", "signing_in")
        state["requests"][action_id] = {"id": action_id, "action": action, "status": "failed" if failed else "succeeded",
                                        "createdAt": stamp(), "courseId": None,
                                        **({"error": _clean(reason, 300)} if failed else {"result": {"status": status}})}
    state["domainRevision"] += 1
    return {"status": status, "patch": merge_patch(before, state), "ifRevision": it_revision}


def school_patch(document, info):
    """Publish the school choice and preset list to the page (no credentials)."""
    state, it_revision = unpack_state(document)
    before = copy.deepcopy(state)
    current = state["runtime"].get("d2l", {})
    fields = {"site": info.get("site", ""), "school": info.get("school", ""), "presets": info.get("presets", [])}
    if not info.get("configured"):
        fields["status"] = "needs_setup"
    elif current.get("status") in (None, "needs_setup"):
        fields["status"] = "needs_login"
    state["runtime"]["d2l"] = {**current, **fields}
    if state["runtime"]["d2l"] == current:
        return {"patch": {}, "ifRevision": it_revision}
    return {"patch": merge_patch(before, state), "ifRevision": it_revision}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_new(path, value):
    p = Path(path)
    if p.exists():
        raise OwlPilotError("Output already exists; choose a new filename.")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("xb") as f:
        f.write(encoded(value) + b"\n")


def save_snapshot(snapshot):
    DATA.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    path = DATA / f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    _write_new(path, snapshot)
    os.chmod(path, 0o600)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only D2L sync for OwlPilot (via d2l-cli). Never submits, posts or changes anything in D2L.")
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("setup", help="Choose your Brightspace school (shared with the `d2l` command).")
    group = st.add_mutually_exclusive_group(required=True)
    group.add_argument("--school", help="Preset name, e.g. ksu or 'georgia state'.")
    group.add_argument("--host", help="Your school's D2L address, e.g. https://yourschool.brightspace.com")
    log = sub.add_parser("login", help="Open D2L in a browser window and wait for the student to sign in.")
    log.add_argument("--timeout", type=int, default=LOGIN_TIMEOUT)
    for name in ("sync", "apply"):
        cmd = sub.add_parser(name, help="Read D2L (sync) or a saved snapshot (apply) and write an It merge patch.")
        cmd.add_argument("--state", required=True, help="`it state owlpilot` output.")
        cmd.add_argument("--out", required=True, help="New patch filename.")
        cmd.add_argument("--action", help="Saved d2l.sync It action JSON, for deduplication.")
        if name == "apply":
            cmd.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            info = setup_school(args.school, args.host)
            print(json.dumps({k: info[k] for k in ("site", "school", "token")}))
            return 0
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
            except (NeedsLogin, NeedsSetup) as exc:
                status = "needs_setup" if isinstance(exc, NeedsSetup) else "needs_login"
                result = status_patch(document, status, str(exc))
                _write_new(args.out, result["patch"])
                print(json.dumps({"status": status, "patchPath": str(Path(args.out).resolve()),
                                  "requiresItRevision": result["ifRevision"],
                                  "next": "Run `python -m owlpilot.d2l setup` / `login`, then sync again. Do not ack the action yet."}))
                return 3
            save_snapshot(snapshot)
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
