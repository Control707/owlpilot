# OwlPilot — It-native hackathon specification

Status: APPROVED PLAN — user explicitly selected “Approve revised plan” in the final review. Wayfinder planning is complete. No installation or implementation has occurred; separate start authorization and normal operation approvals still apply.

## 1. Goal and agreed scope

Deliver a supervised local demo within the under-24-hour build budget: supplied course material → confirmed topics/deadlines → mistake log → source-grounded review guide. Preserve the [existing HTML design](../../owlpilot_academic_co_pilot.html), keeping the original reference unchanged. One course is the demonstration scope, not hardcoded subject logic.

Decisions and evidence: [Wayfinder map](map.md), [It research](it-integration-research.md), and [It-native revision](it-native-revision.md). Documentation/source support is not runtime verification.

Must work:
- Text-based PDF, Markdown, plain text, and pasted text import; student confirms source-linked extracted topics/deadlines before use.
- Mistakes from already-graded work or ungraded practice, with course, assessment/question labels, description and correction/feedback; optional points lost.
- A personalized instructional guide with cited explanations, ungraded practice/reveal, a study checklist, and explicit evidence gaps.
- Durable records across page reopening and supervised agent changes.
- A clear active-agent label, pending/error states, sample/real distinction, and simple priorities from confirmed deadlines/mistakes.

Keep other prototype screens as clearly labeled demos/not connected. Disable misleading live controls. No fictional GPA, identity, grades, sync status, dates, cron jobs or external actions shown as real facts.

Defer: OCR, guaranteed equation/diagram parsing, full multi-course UI, live D2L/DegreeWorks, calendar/GitHub/email writes, unattended jobs, hosted service/distribution, seamless agent-context migration, and concurrent agent operation.

## 2. Reuse It before building infrastructure

| Need | Use from It | OwlPilot adds |
|---|---|---|
| Display the existing HTML | `it create/update`, injected runtime, stable page identity | Academic UI/state rendering; retain vanilla HTML/CSS/JS |
| Inputs and file upload | `It.action`, `It.stage/commit`, actual File attachments | Allowlisted bounded academic action payloads |
| Durable UI edits | `It.store`, `_page`, `It.onState` | Per-control drafts; load/save/error handling |
| Durable academic records | Agent JSON state in It's local database; revision-checked patches | Compact course/fact/mistake/guide objects, revisions and validation |
| Queue and delivery | Existing actions, wait/retrieval, acknowledgment and add-ons | Supervised handling instructions, minimal request status |
| Progress | `It.onProgress` plus domain result state | Honest pending/running/completed/failed copy |
| Agent integration | Existing supported add-ons; CLI fallback for other agents | Shared academic context/result contract |
| Local file handling | Action file storage and installed CLI save/read operations | Small text/PDF extraction and evidence-validation helper |

No second database, extra web server, hosted service, custom queue, model API SDK, or agent daemon. Do not fork It unless an explicitly demonstrated missing requirement needs a separately agreed extension.

Read the installed `it skill` and relevant help before using exact commands. Research used It 0.1.45, commit `3f243321f71c656dae1b51f97c556bbfb8eeeb18`; installed versions may differ.

## 3. Storage ownership and limits

### Canonical compact records: It state

Use one stable OwlPilot page ID across code updates and supervised agent changes. Store app records as objects keyed by ID plus small order arrays, as documented by It. Keep UI controls/drafts in `_page`/It.store, separate from agent-owned domain keys.

Minimum logical state shape:

| Key | Contents |
|---|---|
| `schemaVersion`, `domainRevision` | App schema and domain revision |
| `courses`, `courseOrder` | Stable ID, name, sample flag, timezone or unset; no hardcoded subject |
| `materials` | Course ID, safe display name, SHA-256, source revision, extraction status, selected source chunks/locators |
| `facts` | Topic/deadline, course/material/source IDs, candidate/confirmed/rejected status, revision, explicit unresolved date/time fields |
| `mistakes`, `mistakeOrder` | Stable ID, course, graded/practice origin, labels, description, feedback, optional topic/source references and points |
| `guides` | Current concise guide per course, request/agent label, generated timestamp, input revisions, structured sections/citations, stale flag |
| `requests` | Action ID, payload hash, type, course/input revision, consumer generation, pending/running/terminal status, result/error summary |
| `runtime` | Active agent label, consumer generation, readiness/last verified status; no credentials |

Subject-independent records are mandatory; a second-subject fixture tests the contract without expanding the stage UI to multiple courses.

### Local source files, not a parallel database

Keep originals/extracted text in a workspace-local gitignored `data/materials/<generated-id>/` directory. Use safe generated paths, immutable source revisions, checksums and locators. Nothing sensitive is bundled into the published page by default. Full source documents do not belong in It.store. Relevant concise excerpts in state are disclosed to the student and may reach the selected model provider, as agreed.

Use It's own backup guidance for its data home; a simple app export can additionally save domain JSON plus referenced local material files. Do not promise independent transactional backups of all It internals. Export only while idle; validate schema, paths/checksums and missing files before restore. Restore is a supervised explicit operation, not a destructive page button, and retains the previous export/state.

### Size budgets

It's documented total state limit is 512 KiB, including `_page`; It.store values and action JSON data are each limited to 32 KiB. App target: domain state ≤128 KiB UTF-8 and explicit small UI draft budgets, checked before updates. Keep concise current guides/excerpts and a bounded request history. Warn on capacity before refusing new content; archive/export only with explicit confirmation, never silently discard mistakes or live processing records.

Raw page-paste actions are limited to 24 KiB UTF-8 plus bounded metadata/envelope margin. Larger text goes as an actual File attachment or a user-selected local file, never chunked into raw action data. Proposed source limits: PDF ≤10 MiB/50 pages; local/attached text ≤100,000 bytes. File transfer limits in It are larger, but OwlPilot applies these smaller demo extraction limits. Check before sending when possible and again on receipt. If context/result exceeds the app budget, ask for a narrower source/guide rather than silently truncate.

## 4. Import and source contract

Primary stage UX: page file input → `It.action` with a real File → supported agent/CLI receives the action and saves the attachment to a validated safe local destination → helper extracts/stores source → agent proposes structured topics/deadlines → validated candidates appear → student confirms before activation.

It documents real File attachments and `it save` retrieval. Verify exact installed CLI syntax and the upload round trip in the first integration spike. A local file supplied through the trusted conversation/CLI is an alternative if needed, clearly described in the UI. No arbitrary remote URL fetch, browser access to local paths, base64 file embedding in state, or unverified drag-and-drop promise.

- Small Python 3 helper uses standard-library parsing/validation and pinned `pypdf` for PDF text extraction. No database dependency. Installation is an authorized implementation step, not already performed.
- Extract page-by-page for PDFs and line ranges for text; stable chunk IDs reference material ID/revision/hash. Preserve original source files.
- Reject encrypted, malformed, scanned/near-empty or oversized inputs visibly; offer text/paste fallback. OCR is not supported.
- Imported text and model output are untrusted, escaped data, never executable markup/instructions. Markdown is evidence text, not raw trusted HTML.
- Every proposed topic/deadline cites actual source chunks. Confirmation accepts/edits/rejects candidates. Student edits are labeled user-provided, not falsely attributed to a source.
- Missing/ambiguous dates, weekday conflicts, scope, weights or timezone remain unresolved. Ask for the course timezone when necessary; do not infer from historical prototype dates or unavailable browser context.
- New material version marks dependent facts/guides stale. Do not silently replace confirmed facts.
- Sample course IDs/data remain separate from real records. Sample mode must be unmistakable.

## 5. Actions and supervised agent contract

Use existing It queue/delivery, not a replacement.

| Action | Bounded effect |
|---|---|
| `course.import_file` | Actual file attachment + safe metadata; validates and stages import |
| `course.import_text` | Small pasted text; same candidate/confirmation flow |
| `course.confirm_facts` | Accept/edit/reject candidate IDs at a checked domain revision |
| `mistake.add` | One validated graded/practice mistake |
| `guide.generate` | Reserve one request from confirmed context and relevant mistakes |
| `priorities.refresh` | Nearest confirmed future deadlines plus mistake topics and visible reasons |

For every action: check type, field lengths, file/text sizes, course/material IDs, expected revisions and source references. Never turn an action field into shell text. Optional points must be finite and nonnegative. Client-side double-click prevention supplements, not replaces, durable processing status.

Read current It state and its revision before state mutation, then revision-check the patch. A conflict means reread and revalidate; never blindly replace all state or overwrite `_page`. Combine related domain/request changes in one state patch where possible. Files are not atomically committed with state: stage them safely, patch references only after successful extraction, and report incomplete imports explicitly.

Minimum request state: pending → running → succeeded/failed. It is authoritative for delivery status; app state is authoritative for whether the academic operation succeeded. A turn ending does not mean success. Unavailable agent requests stay pending. Interrupted/uncertain running generation requires explicit review/retry; do not automatically resubmit a possibly charged model call.

Persist request reservation before model generation. Before applying output, recheck action ID/payload hash, input revisions and consumer generation. Completed action replay reuses the saved result rather than adding another mistake or regenerating. Same action ID/different payload is rejected. A changed input produces a stale result, not replacement of a newer guide. Record the academic result/request completion in one checked patch, then acknowledge. If acknowledgment is uncertain, inspect state before retrying; do not repeat model generation. No exactly-once provider execution guarantee.

Small helper verbs may include validation, extraction, context selection, patch preparation and export checking; these are app proposals, not existing It commands. Let installed It handle file transfer, state persistence, queue delivery and acknowledgment.

## 6. Review guide and evidence validation

Structured output: overview; ranked topics with reasons; cited concept summaries; common-error feedback; generated ungraded practice with revealable explanations; study checklist; evidence gaps.

Each course-specific factual section cites actual same-course source chunk IDs/revisions. Feedback may cite mistake IDs. Generated practice is labeled generated, not instructor-authored. Mechanical validation checks existence/course/revision, not semantic truth. Manually review the known fixture's guide during rehearsal. Missing evidence leads to a gap/request for materials, not invented citations or generic text falsely labeled personalized.

Open source references as escaped excerpts with filename and PDF page/text line locator; no iframe PDF viewer. Relevant excerpts and mistake details may be processed by the selected agent's configured model provider. Show that disclosure; local storage does not imply offline inference.

No writing/submitting graded work, posting discussion responses, opening timed assessments, or changing D2L. Application handlers provide no external-write tools. Prompt boundaries are not a sandbox for a general-purpose agent: retain host permissions and supervision.

## 7. Runtime choice and switching

DSH preferred; separately configured Claude Code is an alternative. One active supervised agent, same page and domain records. No seamless context migration or custom unattended wake.

First implementation spike: publish non-sensitive page → upload/text action → actual named agent receives it → checked state update → visible result → reopen persistence. Include original file receipt and It.store draft save. Read actual `arrives.byItself`/ownership guidance; never infer DSH automatic inbound turns from CLI availability.

Timebox bridge verification to 60 minutes after authorized setup, with a bounded DSH attempt and time reserved for Claude Code. DSH uses explicit page-scoped wait/retrieval unless a native route is actually verified. Document any required human turn. Do not construct an unapproved watcher to inject Harness messages. If DSH isn't reliable within the spike, use verified Claude Code for the stage demo and label the actual active agent. If neither route works, stop expansion and ask for a scope/runtime decision.

Switch only at idle: settle/cancel work explicitly, stop the old consumer, inspect page ownership and records, transfer/adopt using installed It guidance, advance app consumer generation, verify one action with the new agent. A label or selector alone is not proof of handoff. No direct edits of It's internal database to bypass ownership.

Setup: network exposure, telemetry and auto-wake off for the supervised demo, retaining host approvals. Installed settings/traffic are verified rather than assumed; provider calls and optional update/resource traffic remain disclosed. Prefer system fonts over the current Google Fonts import. No secrets in page state, bundles, exports or test artifacts. Data remains unencrypted unless the host protects it.

## 8. Acceptance gates

1. **Real bridge:** observed action/upload/result with actual agent label; reopen saved state/drafts. Record DSH manual behavior or verified Claude fallback.
2. **Import:** one text PDF and text/paste fixture cite stable locators; invalid/scanned/oversized inputs fail clearly; no priorities before confirmation; ambiguous dates unresolved.
3. **Generic course:** second-subject fixture uses the same contract; sample/real records and citations never mix.
4. **Mistakes:** invalid course/points rejected; malicious-looking text inert; duplicate action yields one record.
5. **Guide:** live known-fixture generation with actual evidence/mistake references; unknown/cross-course citations rejected; insufficient context disclosed.
6. **Persistence/conflicts:** reopening retains state; stale revision refused and safely rebased; completed replay does not regenerate; uncertain running work needs explicit recovery; app warns at size limits.
7. **Safety/honesty:** no external-write handlers, unattended wake, false sync/grade claims, secret leakage, or prerecorded results labeled live AI.
8. **Demo recovery:** rehearse happy path, model/agent unavailable, idle agent change if supported, and simple state/material export/restore on sample data.

## 9. Delivery and approval

Implementation deliverables: adapted vanilla page, small extraction/validation helper (no database), shared supervised agent instructions, synthetic course fixtures, contract tests, and short setup/demo/recovery guide. Full live documents stay out of publication bundles/Git.

The [build plan](build-plan.md) sequences the work. This revised spec replaces the earlier separate-SQLite proposal at the user's request. Approval of the completed plan closes Wayfinder planning; installation, authentication and implementation start remain separate actions subject to normal approvals. Unknown runtime behavior is an early test gate, not a claim of success.
