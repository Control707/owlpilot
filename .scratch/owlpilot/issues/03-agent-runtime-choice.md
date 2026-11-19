# Choose the agent that will own OwlPilot's live interactions

Type: grilling
Labels: wayfinder:grilling
Status: resolved
Assignee: lead
Blocked by: 02
Parent: [OwlPilot — Personal academic co-pilot](../map.md)

## Question

Given verified It compatibility and locally available tools, which agent app should own OwlPilot's live interactions, and what page responsiveness and session-lifecycle behavior must the first release support?

## Context

The prototype mentions Codex CLI, but Codex is not on the current PATH. Claude Code is available on PATH; authentication has not been checked. The current conversation is in DeepSeek Harness, whose automatic action-delivery support must not be inferred. Use the runtime research before recommending a route; the user chooses the app and any later installation separately.

## Comments

User response to runtime/lifecycle questions: “I'm not sure I want to use DSH perosnally but I want to be able to switch agents to allow others to use claude code if they want to”. The preference for personal DSH use is ambiguous and needs confirmation; agent choice must not be silently recorded as settled. User explicitly prioritizes a hackathon demo that works well and can be built quickly; no fixed session-lifecycle behavior was selected. Prefer reuse of It's documented integrations over a custom multi-agent platform. Supporting selection of separately configured agents is distinct from promising seamless in-flight conversation handoff.

The mention of others using OwlPilot also needs a scope check against the earlier personal-use decision and It's distribution/product restrictions before packaging or redistribution; no public distribution is authorized by this response.

## Answer

The user confirmed the following refined plan:

- DSH is the preferred personal agent; separately configured Claude Code must remain an alternative.
- Keep a common page/action/data contract and one active agent at a time. Do not promise seamless mid-task conversation switching.
- Select the actual demo route after an early end-to-end integration test; DSH is preferred, not a hard requirement for the live demo. It has no verified DSH automatic-delivery adapter today.
- Local hackathon demo first, using It as a separately installed tool. Public distribution, bundled installers, and hosting are deferred; licensing must be checked before any later audience change.
- Less than 24 hours remains for the build (relative budget, not a fixed calendar deadline).
- The must-work stage flow is supplied course material → log a mistake → source-grounded review guide. Daily priorities may remain simple.

The earlier lifecycle question did not receive a specific answer. Conservatively propose a supervised live demo session, without installing or enabling unattended wake; confirm this in the implementation-readiness review. Agent selection is an interface/operating choice, not permission to install an app, start a service, contact a model, or bypass Harness approvals.

### Planning consequence

Use the existing It CLI/page bridge rather than build a custom multi-agent platform. An initial integration spike must prove publication → action receipt → agent result → durable visible update, including actual DSH limitations. If that cannot be made reliable within the agreed small spike budget, use separately configured Claude Code for the stage demo, without claiming DSH support is finished. The exact timebox and verification criteria belong in the implementation plan.
