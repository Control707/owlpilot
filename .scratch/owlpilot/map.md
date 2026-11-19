# OwlPilot — Personal academic co-pilot

Labels: wayfinder:map
Status: resolved — approved specification and phased build plan delivered

## Destination

An implementation-ready specification and phased build plan for a personal-use, local-first OwlPilot that preserves the supplied HTML design, uses It for page-to-agent interactions, and replaces mock features incrementally. This map plans the work; it does not authorize installation or implementation.

## Notes

- Follow Matt Pocock's Wayfinder, Grilling, and Domain Modeling instructions. They are not registered Harness skills in this session; the upstream instructions were read directly at https://github.com/mattpocock/skills/tree/main/skills/engineering/wayfinder and the corresponding grilling/domain-modeling directories.
- Tracker: local Markdown, following https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md.
- Original design/reference: [OwlPilot prototype](../../owlpilot_academic_co_pilot.html). Preserve it during planning.
- Find live tickets in the sibling `issues/` directory, ordered by number; choose an open, unclaimed ticket only when all `Blocked by` tickets are resolved. The map does not duplicate open ticket bodies.
- Confirmed by user: local hackathon demo and personal use, not a hosted service or distributed product; retain current design; use It as a separately installed interaction runtime.
- Build budget: under 24 hours. Must-work stage flow: supplied course material → log a mistake → source-grounded review guide; daily priorities may stay simple. Favor a verified narrow demo over feature breadth.
- DSH preferred, with separately configured Claude Code as an alternative; one active agent, common interaction/data contract, no promised mid-task handoff. Pick the stage route after an early integration test.
- Resolve human decisions through actual user answers, not agent assumptions. Questions downstream of unsettled facts wait for research.
- Research findings must distinguish documented support from local verification. No installations, service starts, university logins, or external actions during charting.
- This folder is not yet an established project Git checkout. Research is read-only; no research branches or upstream issues are created.
- Local prerequisite check: `it`, `codex`, and `bun` are not on this session's PATH. `claude`, `node`, `python3`, and `git` are available. Availability is not proof of authentication or a working integration.

## Decisions so far

- [Choose the first useful study loop and its boundaries](issues/01-study-loop-scope.md): personal-use, files-first priorities → mistake log → personalized review; retain other screens as explicit demos and enforce the prototype's safety boundaries.
- [Establish It's page, action, and persistence contracts](issues/02-it-runtime-research.md): single-file publication is supported; persistence must change; DSH requires explicit CLI consumption rather than an assumed automatic add-on. Documentation/source verified, not runtime-tested.
- [Choose the agent that will own OwlPilot's live interactions](issues/03-agent-runtime-choice.md): DSH preferred with Claude Code alternative; local, under-24-hour hackathon demo; verify the stage agent early and keep the must-work flow narrow.
- [Define the first course-material import contract](issues/04-course-import-contract.md): subject-independent design, one demo course; text-based PDF/Markdown/text/paste; confirm extracted topics/deadlines and separate sample data; defer OCR.
- [Choose durable ownership of OwlPilot's academic data](issues/05-durable-state-ownership.md): revised at the user's request to reuse It's local durable state/database for compact records and its file/action/progress infrastructure; keep source documents locally; no second database. Provider excerpt disclosure and supervised/auto-wake-off choices remain.

- [Agree the implementation contract and hackathon build sequence](issues/06-hackathon-spec-and-verification.md): user approved the It-native [spec](spec.md) and [build plan](build-plan.md), with early real-agent verification gates and an approximately 9-hour target plus contingency.

## Not yet specified

None for this planning destination. All decision tickets are resolved. Installation, runtime verification and feature implementation are future work governed by the approved build gates, not completed work or hidden planning assumptions.

## Out of scope

- Installing It, changing the HTML, or implementing the application during this planning map.
- A hosted multi-user service, commercial distribution, or embedding It in a product offered to others.
- Live university integrations as a prerequisite for the first usable release.
- Making every prototype screen live in the first release.
- Performing external writes or graded academic actions during planning.
