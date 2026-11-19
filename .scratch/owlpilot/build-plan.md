# OwlPilot — It-native hackathon build plan

Status: APPROVED PLAN — user explicitly selected “Approve revised plan” in the final review. Uses It for existing infrastructure rather than a second database. Relative engineering targets, not guaranteed completion times. See [spec](spec.md), [map](map.md), and [research](it-integration-research.md).

## Rules

- Preserve the existing vanilla design; no React migration, extra server, SQLite layer, custom queue or agent daemon.
- Use It's installed skill/help, state/store, files/actions, queue, progress and existing agent connections.
- Only add academic extraction/validation, evidence contracts and UI behavior.
- Use synthetic fixtures first. Install/authenticate/start nothing before the appropriate separate authorization.
- Keep uncertainty explicit. Passing a mock adapter test is not passing a real It/agent integration.

## Phase 0 — Authorized setup and integration gate (target 1 hour)

Inspect installation steps and ask for required host changes; verify installed version, data paths, service, network exposure, telemetry and auto-wake settings. Keep exposure/telemetry/auto-wake off and normal host permission controls intact. No credentials in logs or pages.

Publish a tiny page. Verify action delivery, actual File upload/save, checked agent-state patch, It.store draft save, visible result and reopening. Try DSH with explicit page-scoped wait/retrieval; document any manual user turn. Reserve time within the spike to verify Claude Code if DSH is not reliable. Read real ownership/arrival guidance before claiming agent switching works.

**Gate:** observed named-agent round trip + durable state/file access. If neither route works, stop expansion and report the failure; no pretending prerecorded output solved the bridge.

## Phase 1 — It-native records and existing page (target 1.5 hours)

Define compact domain keys for courses, materials/facts, mistakes, current guides and bounded request statuses. Keep `_page` controls separate. Adapt the existing page to asynchronous state arrival and It.store drafts, not canonical localStorage. Add sample/real and actual-agent labels. Write a small deterministic JSON/action validator with state-budget checks; use It's checked patches and queue rather than duplicating them.

**Tests:** save/reopen; bad payload/points; duplicate mistake action; stale revision; escaped text; state-size rejection; no mock identity/grades/sync shown as real. Test single-consumer procedure.

## Phase 2 — Import and confirm (target 2 hours)

Use verified File action retrieval for PDF/text uploads and a ≤24 KiB raw paste path. Store originals/extracted text in gitignored local material files. Add pinned pypdf in an approved project environment. Preserve page/line locators and revisions; propose source-linked facts and show confirmation before use.

**Tests:** small text PDF/text; malformed/scanned/oversized rejection; actual upload; unknown source IDs; date ambiguity; sample/real separation; source-change staleness. Conversation-local import remains a documented alternative, not an invented browser path API.

## Phase 3 — Cited review loop (target 2 hours)

Use the selected configured agent to handle guide actions with relevant confirmed excerpts/mistakes. Shared structured result format, deterministic source/revision validation and one checked completion patch. Render overview, priorities, cited explanations, practice/reveal, checklist and evidence gaps. Reuse It progress plus academic result states; never equate turn completion with success.

**Tests:** actual fixture-grounded generation, semantic spot-check, invalid/cross-course citations, missing evidence, repeated delivery, stale input, uncertain interruption. No automatic model retry.

## Phase 4 — Recovery and demo polish (target 1.5 hours)

Basic confirmed-deadline/mistake priorities; clear pending/error states; idle agent handoff operating instructions; simple domain JSON/material export/restore. Keep histories bounded with explicit archival/export, not silent deletion. Disable/labeled demo controls on unconnected screens. Prefer system fonts and review mobile/keyboard behavior.

**Tests:** reopen, checked-patch conflict, result saved but ack uncertain, size warning, second-subject schema smoke test, source excerpt opening, sample snapshot/restore. Verify alternative agent only if actually configured; no selector-only support claim.

## Phase 5 — Rehearse and freeze (target 1 hour)

Run import → confirm → mistake → live cited guide → inspect excerpt → reopen. Show actual active agent and disclose provider traffic. Rehearse agent/model unavailable and clear recovery. Make a simple export plus local source copy. Prepare a labeled saved sample walkthrough for presentation contingency, never represented as live AI.

**Gate:** must-have acceptance cases from the spec pass; document limitations and observed agent behavior. Freeze working versions and keep the original HTML reference intact.

## Budget/cut line

Targets total approximately 9 engineering hours, leaving contingency within the user's under-24-hour build budget. Reassess after each gate; these are estimates, not guarantees.

Drop extra courses, richer priority ranking, polished switching UI (retain supervised documented procedure) and decorative polish before cutting the core evidence/review/persistence tests. If accepted PDF scope or either live-agent route fails, report it and ask for a narrower scope rather than silently dropping it.

After the demo only: independent domain database if state scale warrants it; multi-course UI, OCR, native DSH adapter, automated backups, university integrations, unattended jobs, external approval workflows. Distribution/hosting requires license review and a separate effort.
