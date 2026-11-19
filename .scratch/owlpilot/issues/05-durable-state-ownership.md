# Choose durable ownership of OwlPilot's academic data

Type: grilling
Labels: wayfinder:grilling
Status: resolved
Assignee: lead
Blocked by: 02, 03
Parent: [OwlPilot — Personal academic co-pilot](../map.md)

## Question

Should student course facts, mistakes, and generated review guides be stored through It's supported store, in OwlPilot-owned local files/database, or in a deliberately split model? What restart, export, deletion, and backup guarantees must the first release provide?

## Context

The standalone prototype saves to browser localStorage. Upstream research reports that published-page storage is ephemeral, so preserving that mechanism unchanged is not sufficient. Keeping data locally does not by itself mean an agent's model processes it on-device; the data-flow contract must distinguish local storage from model-provider transmission.

## Answer

The user explicitly selected all three recommended defaults:

- OwlPilot-owned local storage is canonical for supplied materials, confirmed course facts, mistakes, and guides. It holds bounded display state/drafts. Changing the active agent must not replace the academic records. Include simple local export/recovery in the implementation plan.
- The planned working app may send relevant course excerpts and mistake details to the selected agent's configured model provider to generate reviews. Show the active agent/data use; keep provider credentials outside pages. Prefer sample material in the demo where practical. This is agreement on the future data-flow design, not authorization to transmit any documents now or to change provider configuration.
- A supervised demo only: unattended auto-wake disabled; agent-unavailable requests remain visibly pending. No background autonomous operation is required for the first release.

### Superseding user-requested revision — It-native storage

During final review, the user correctly noted that It already has a database. After clarification they explicitly requested: “yes revise the plan to use whatever it can from https://github.com/Aaryan-Kapoor/it”. This supersedes the independent canonical-records database recommendation above, while retaining the approved provider-data-flow and supervised-runtime choices.

Use It's local durable agent state for compact course facts, mistakes, current guides and request status; It.store for UI drafts; existing action/file storage, delivery, progress and acknowledgments. Keep originals/extracted sources as gitignored local files, with stable IDs/checksums/locators. No separate SQLite database, web server, queue or agent daemon. A small PDF extraction/schema/source-validation helper remains app-specific. Switching agents on the same page preserves records but does not migrate conversation context. Accept It's size/lifecycle dependency for the hackathon; use bounded records and simple explicit exports rather than a parallel persistence framework.

See the [It-native revision](../it-native-revision.md) and revised [spec](../spec.md) for concrete limits and contracts. Original user selections remain above as historical context; the active architecture is this revision. Final whole-plan sign-off is still pending in the final decision ticket.
