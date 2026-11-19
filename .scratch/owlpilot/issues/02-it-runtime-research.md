# Establish It's page, action, and persistence contracts

Type: research
Labels: wayfinder:research
Status: resolved
Assignee: lead
Blocked by: none
Parent: [OwlPilot — Personal academic co-pilot](../map.md)

## Question

What exact supported mechanisms does It provide to publish an existing single-file HTML page, deliver its actions to an agent, update shared state, and preserve data across restarts? Which runtime prerequisites, agent compatibility limits, and approval/security constraints affect a personal OwlPilot?

## Research context

Read-only preliminary research is running in subagent `a721443f-b54c-473d-8f2a-636ebc84b25b`. It must cite upstream primary sources, distinguish documented support from tested behavior, and make no installs or source changes.

Local facts: `it`, `codex`, and `bun` are not on PATH; `claude`, `node`, `python3`, and `git` are available. Authentication and runtime operation are unverified. DeepSeek Harness is the current conversation host; native automatic action delivery must not be assumed.

## Evidence already checked

- https://github.com/Aaryan-Kapoor/it/blob/master/docs/agents.md: It brings no agent of its own; supported add-ons deliver actions, while other apps can use CLI action retrieval/waiting.
- https://github.com/Aaryan-Kapoor/it/blob/master/docs/licensing.md: individual use is documented, but hosted/managed service and product embedding are restricted.

## Comments

The workspace is not an established Git project. Record a local cited research report instead of pushing a throwaway research branch. No upstream issue or PR is authorized.

## Answer

Completed read-only research against It 0.1.45, commit `3f243321f71c656dae1b51f97c556bbfb8eeeb18`. See the [cited integration research](../it-integration-research.md) for evidence and exact contracts.

Single-file HTML publication and an injected page-action/state bridge are supported. Existing browser localStorage persistence must change because the published sandbox makes it ephemeral; It.store is durable but bounded, leaving domain-storage ownership to decide. No DSH add-on is documented/discovered: explicit CLI pull/wait is supported, not automatic Harness inbound turns or unattended wake. Supported agent apps offer stronger integration, subject to runtime verification. It supplies no model or university data integration. Actions are untrusted data rather than sufficient authorization; secrets must remain outside page state. Local storage does not imply local model processing. No installation or behavior was runtime-tested, and no agent app or persistence architecture was selected on the user's behalf.
