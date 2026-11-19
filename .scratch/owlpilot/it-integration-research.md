# It integration research for OwlPilot

Status: documentation/source verified; not runtime tested.

Baseline: It 0.1.45, commit `3f243321f71c656dae1b51f97c556bbfb8eeeb18`, resolved from upstream master during this research. No install, publication, service, agent authentication, university access, or external writes were performed.

## Publication and page bridge

A single HTML file is directly publishable with `it create "OwlPilot" --id owlpilot --file owlpilot_academic_co_pilot.html --open` (example only, not run). A lone file becomes index.html; sidecar assets require directory publication. No project Git checkout is required. Republishing makes a new version and reloads displays; ordinary result updates should use state updates, not republishing.

It injects the runtime before page scripts. `It.action(name, data)` submits an action. `It.stage(key, value)` and `It.commit(name)` collect and submit choices together. Read initial/updated state using `It.onState`; do not assume synchronously populated `It.state`. Agent CLI state updates include `it state`, `it set`, and revision-checked `it patch ... --if-revision N`.

Treat actions as at-least-once and deduplicate action ids. `it actions` only lists; `it ack` marks processing complete. Waiting/add-on delivery and successful domain processing are distinct.

Sources:
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/addons/skill/SKILL.md
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/packages/cli/src/publish.ts
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/packages/runtime/src/it.ts

## Durable data and sandbox constraints

It owns local page versions, state, actions, and uploaded files, normally under its own ~/.it data home, using a local Convex backend. No hosted Convex subscription is required by this design.

Published-page localStorage/sessionStorage are in-document memory shims. IndexedDB, caches, cookies, and service workers are unavailable. OwlPilot's current browser localStorage persistence cannot be carried over unchanged.

`It.store.get/set` persists per-page choices/drafts across openings/displays through state's `_page` records. Read after state arrival. Concurrent writes are latest-saved-value-wins, not a promised CRDT. Limits: total page state 512 KB; individual store value 32 KB; at most 5,000 store values. File/Blob objects do not belong in the store. Bundled PDFs cannot be framed using iframe/embed/object; linking or page rendering needs a separate design.

Recommendation, not a user decision: keep canonical academic materials, extracted facts, citations, and generated guides in OwlPilot-owned local files/database; keep It state as a bounded UI projection and drafts. Decide backup, export, deletion, and synchronization guarantees before implementation.

Sources:
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/addons/skill/more/page.md
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/convex/state.ts

## Runtime and agent compatibility

The standalone binary bundles its runtime; Node/npm is not a standalone prerequisite. First setup downloads a checksum-pinned local backend of approximately 60 MB. A source build has different Node/npm requirements. macOS uses a login background service; the computer must stay on for interactions. Keep network access off initially unless explicitly needed. macOS/Windows coverage is less mature than daily Linux use according to the documentation.

Supported integrations include Claude Code, Codex, Pi, OpenCode, and Hermes; T3 Code uses Claude/Codex bridges. Experimental OpenClaw is not a standard setup choice. No DeepSeek Harness add-on was discovered or documented.

Any CLI-capable agent can use explicit `it wait --id owlpilot --timeout 100` or action listing/retrieval and acknowledgment. This is a pull/wait fallback, not automatic inbound delivery or wake-after-close. Without known session identity, explicitly name the page and verify ownership. `it actions --follow` observes waiting actions but is not a reliable action consumer. Publication/status output's `arrives.byItself` and next-step guidance must be verified in the eventual installed runtime.

Local check: `it`, `codex`, and `bun` are not on this session's PATH; `claude`, `node`, `python3`, and `git` are present. This does not prove any app's authentication or readiness.

Sources:
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/docs/install.md
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/docs/agents.md
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/addons/skill/more/waiting.md
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/addons/skill/more/actions.md

## Safety, privacy, and licensing

An It action is page-controlled data, not independently trustworthy authorization. Validate inputs, preserve exact proposed operations/revisions, reject stale approvals, and deduplicate. For uncertain external/destructive operations, seek confirmation through the trusted conversation. Source documents and model output are untrusted data, not instructions or executable HTML.

It is a one-person trust domain, not an isolation boundary between agents: enrolled agents can access all its pages. Local storage is unencrypted; never place provider credentials in page state or bundled files. Page scripts can contact the internet. The existing prototype imports Google Fonts, so eliminating network dependencies would require revisiting those assets.

Auto-wake is enabled by default for connected supported apps. Recommendation: explicitly disable it initially; do not adopt broad Full Access/Bypass permission defaults for convenience. It permission rules are not Harness approvals and do not override them.

Local-first storage does not imply on-device model processing. Decide whether academic excerpts may be sent to the chosen model provider. Automatic telemetry is enabled by default, and update checks/page resources may create network traffic. Installation changes PATH, data directories, background services, and agent integration settings, requiring separate authorization later.

The source-available license permits self-initiated personal use/modification but restricts hosted/managed service use, commercial incorporation, and distribution. Recheck exact terms for any future audience change.

Sources:
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/docs/what-it-protects.md
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/docs/network-and-privacy.md
- https://github.com/Aaryan-Kapoor/it/blob/3f243321f71c656dae1b51f97c556bbfb8eeeb18/docs/licensing.md

## Remaining decisions

- Which agent app owns actions and what responsiveness/session lifecycle is required?
- Which academic data is canonical outside It, and how are backup/recovery and state revisions handled?
- Which material formats and real-course scope enter the first import?
- Which model provider may receive which excerpts; what works without internet?
- What exact action permission matrix, source-attribution rules, and acceptance tests enforce the approved boundaries?
