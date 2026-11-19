# Proposed simplification — It-native hackathon storage

Status: ARCHITECTURE REVISION APPROVED — user requested “yes revise the plan to use whatever it can from https://github.com/Aaryan-Kapoor/it”. Supersedes the separate SQLite/domain-database recommendation. The revised spec/build plan await final whole-plan review before implementation.

## Why change

The user correctly asked whether It already supplies a database. Yes: its local Convex backend persists published pages, agent state, per-page It.store values, actions, and uploaded action files. A separate SQLite store is not required for persistence or switching the agent operating on the same page. Earlier research identified these capabilities, but the initial draft over-weighted long-term independence relative to the under-24-hour demo budget.

Source: https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/addons/skill/more/page.md

## Recommended revised architecture

- Existing vanilla HTML design + It's injected action/state bridge.
- It agent state is canonical for compact course facts, mistakes, guides, source-reference metadata, and bounded request/result status. Use stable IDs and revision-checked state patches; preserve `_page` UI drafts.
- Original course documents and extracted source text remain in a workspace-local, gitignored material folder, with checksums and locators referenced in state. No second database, server, or custom scheduler.
- A small optional Python helper handles text-PDF extraction and deterministic JSON/source/schema validation. It does not own a parallel database or recreate It's queue. Agent performs model generation through the existing configured provider.
- Page file inputs can submit actual File objects with `It.action`; agent retrieves them using installed CLI help (`it save` route documented upstream). Validate downloaded files before extraction. Local conversation-supplied paths remain an alternative. This is documented support, not a passed runtime upload test.
- Page state holds selected concise excerpts and current results, not full documents or unlimited history. Bound agent projection to approximately 128 KiB and reserve room for drafts below It's combined 512 KiB limit. Warn before full; explicit archival/export rather than silent deletion.
- All action JSON metadata must stay below It's 32 KiB per-action limit. Page paste input budget is at most 24 KiB UTF-8 with envelope margin. Larger text up to the original proposed 100,000-byte local-file limit must travel as a file attachment or local import, not a raw text action. Earlier draft conflated these paths.
- It.store values each stay under 32 KiB. Larger domain records belong in bounded agent state rather than a single It.store value.
- Reuse It's action queue, acknowledgments and revision conflicts. Keep only minimal application processing status keyed by action ID in agent state to prevent reapplying a completed action. Do not promise exactly-once model calls or transactionality across unrelated CLI operations; uncertain running work requires explicit recovery, not automatic regeneration.
- Agent switching means one supervised consumer at idle, operating the same page/state and material directory; it does not automatically migrate conversation context. Verify page ownership/identity before handoff using installed help. DSH fallback limitations remain unchanged.
- Simple manual state export plus a copy of the material folder is adequate for the demo; restore requires validation and explicit trusted confirmation. No elaborate migration/backup framework.

## Unchanged

One-course demo, subject-independent schema, source confirmation/citations, sample/real separation, existing visual design, personal/local audience, selected-provider excerpt disclosure, supervised runtime/auto-wake off, deterministic action validation, no external-write handlers, DSH-first integration spike and verified Claude Code fallback, honest failure labeling.

## Trade-off accepted if approved

Compact domain records now depend directly on It's state/data lifecycle and size limits. Independent academic database ownership is deferred, not promised. Keep local sources and simple exports so later migration is possible. A later larger/multi-user product may warrant its own database, but it is not needed to validate this demo.
