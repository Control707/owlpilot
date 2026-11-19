# Agree the implementation contract and hackathon build sequence

Type: grilling
Labels: wayfinder:grilling
Status: resolved
Assignee: lead
Blocked by: 03, 04, 05
Parent: [OwlPilot — Personal academic co-pilot](../map.md)

## Question

What minimal end-to-end implementation contract, verification criteria, and timeboxed build sequence are sufficient to deliver the approved one-course hackathon flow while preserving subject independence, canonical local records, replaceable agents, source grounding, and supervised safety?

## Scope of this decision

Synthesize the resolved scope/runtime/import/storage tickets into a proposed implementation-ready spec and phased plan for user review. Do not install or implement. The proposal must state:

- Local canonical schema and atomic-save/recovery behavior; stable IDs, course isolation, material revisions, and bounded It projection.
- How user-selected files are ingested through the agent/CLI path, not an invented browser-to-filesystem API; PDF extraction dependency and failure behavior; paste alternative; size/page limits; source locators; explicit confirmation of extracted topics and deadlines.
- Typed actions and validated result contract for import confirmation, mistake capture, guide generation, and basic priorities. Local action deduplication, pending/running/succeeded/failed states, stale-result handling, revision checks, and no automatic retry of uncertain model processing.
- Review sections and source references, gaps and stale indicators, instructional safeguards, and explicit separation of sample material from live model generation. No claimed correctness guarantee, fabricated citations, grades, or university sync.
- One active agent and explicit handoff only at idle boundaries, preserving records while not claiming context migration. Early DSH round-trip spike, a small timebox, documented manual pull behavior, and a verified Claude Code fallback; no custom unattended watcher that purports to inject Harness turns.
- Privacy/data-flow notice, no secrets in pages, no external-write tools in the demo, supervised runtime, auto-wake/network exposure off. Installation/authentication remains separately approved.
- Small vertical slices, testable acceptance criteria, failure-mode rehearsal and honest offline/sample fallback labeling, plus stretch/deferred scope.

## Acceptance of this planning ticket

Create linked draft spec/build-plan artifacts, obtain the user's explicit agreement or revisions, then record the answer here and close the ticket. Only after the user confirms the complete plan may the planning objective be marked complete. Unknown runtime behavior remains an explicit early implementation gate, not a false claim of verification.

## Comments

Draft [spec](../spec.md) and [build plan](../build-plan.md) were produced but NOT approved. The user asked whether It already handles this with its own database, adding conditional approval only if that assumption were wrong. The assumption is correct, so the condition is not met and approval must not be inferred.

PI recommendation revised toward the smaller [It-native storage proposal](../it-native-revision.md): reuse It's local durable state/database and action queue, keep originals/extracted sources as local files, and remove the separate SQLite persistence layer. This revisits the earlier records-ownership decision explicitly rather than silently changing it. The user subsequently explicitly requested revision to reuse whatever It provides. The spec/build plan have now been rewritten with It-native durable state, file actions, queue/progress and existing agent routes; final whole-plan review remains pending. Re-reading the primary page contract also confirmed direct File action support and the 32 KiB action metadata limit; the revised spec distinguishes the ≤24 KiB raw paste action from larger attached/local text files.

## Answer

The user explicitly selected “Approve revised plan” for the final It-native specification/build sequence: reuse It's local database/state, file uploads, queue and supported agent connections; preserve the existing vanilla HTML design; add only academic extraction/validation and the study loop; verify DSH first with a tested Claude Code fallback; supervise the demo. Relative build targets total about 9 hours plus contingency, not a guarantee.

Approved artifacts: [implementation specification](../spec.md) and [phased build plan](../build-plan.md). They cover confirmed scope, generic course records, size/validation/source contracts, privacy/safety boundaries, failure/recovery behavior, actual-agent verification gates, and ordered vertical slices.

No in-scope planning questions remain. Runtime unknowns are deliberately assigned early pass/fail implementation gates; their success is not claimed. Planning approval does not install It, start services, authenticate an agent, transmit documents, or authorize implementation. Those require a separate start request and applicable operation approvals. Close this decision and the planning map; hand off the approved plan.
