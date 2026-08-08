# AiCIV Product Layer for Hermes

This directory contains the AiCIV-native product layer that turns a pinned Hermes Agent distribution into an AiCIV workspace while preserving Hermes as the runtime substrate.

## Architecture

```text
                           HUMAN
                             │
                AiCIV Living Record shell
                             │
             ┌───────────────┴────────────────┐
             │                                │
       AiCIV workspace                 Hermes native surfaces
  Now / Needs You / Results          Sessions / Files / Cron /
 Projects / Activity / References     Skills / Models / System
             │                                │
             └───────────────┬────────────────┘
                             │
                        Hermes Agent
                   tools / skills / memory /
                 sessions / browser / channels
                             │
                    substantial voice work
                             │
                        Presence Gateway
                             │
                     durable primary AiCIV
```

Hermes is not being reduced to a chat backend. Its existing capabilities remain available. AiCIV adds the collaboration, continuity, truth, project and result semantics that should surround those capabilities.

## Current tranche

The first product tranche contains:

- Living Record brand constitution and dashboard theme;
- AiCIV wordmark shell injection;
- real dateline rail with live Hermes session count or a blank centre;
- root `/` override with AiCIV Now;
- meaning-first cockpit sidebar;
- Presence readiness/token bridge using multi-body identity v2;
- durable Presence work/result display and cancellation-request semantics;
- Projects;
- Activity;
- shared References;
- Chat durable-work context injection;
- Sessions object-context injection;
- mandatory public disclosure;
- executable brand lint;
- focused truth/continuity tests;
- safe installer into an existing Hermes home.

This is a foundation, not the end of the Portal parity work. Planned tranches include structured decision responses, Hermes/Kanban activity projection, semantic Teams, browser co-control/evidence, richer global search, contextual shared-object actions, real web voice media, mobile/Reachy client manifest integration, and branded-distribution core controls where Hermes extension points are insufficient.

## Install into a Hermes home

From the repository root:

```bash
python aiciv/install.py
```

Dry run:

```bash
python aiciv/install.py --dry-run
```

The installer:

1. backs up an existing AiCIV theme/plugin copy;
2. installs `brand/themes/aiciv-living-record.yaml` into `~/.hermes/dashboard-themes/`;
3. installs the workspace plugin into `~/.hermes/plugins/aiciv-workspace/`;
4. selects `dashboard.theme: aiciv-living-record` in Hermes config when PyYAML is available;
5. removes a dashboard font override that would violate the one-family brand rule.

Restart the dashboard or rescan plugins after installation.

## Environment

The workspace operates without Presence configured; voice/durable job sections will report unavailable rather than invent data.

For Presence integration:

```bash
export PRESENCE_GATEWAY_URL="https://presence.example.com"
export PRESENCE_GATEWAY_API_KEY="..."
export AICIV_CIV_NAME="Synth"
export AICIV_HUMAN_NAME="Corey"
```

The browser never receives `PRESENCE_GATEWAY_API_KEY`.

Voice identity from Hermes Web is server-derived:

```text
participantName = Synth:Corey:hermes-web
continuityKey   = Synth:Corey
surface         = hermes-web
```

The realtime surface changes across Portal/mobile/Reachy/watch. The durable relationship key does not.

## State ownership

| Object | Authority |
|---|---|
| Hermes sessions/runtime/tools/skills/cron | Hermes |
| Presence jobs/results/receipts | Presence Gateway |
| AiCIV project relationships | AiCIV workspace plugin |
| AiCIV shared references | AiCIV workspace plugin |
| AiCIV product activity | AiCIV workspace plugin/projectors |
| Human↔AiCIV continuity | Presence identity contract |

Do not copy authoritative bodies merely to make the UI convenient. Store references and relationships instead.

## Trust semantics

These are product invariants:

```text
request accepted != work completed
cancel requested != cancelled
evidence saved != job succeeded
voice connection lifetime != durable job lifetime
durable job lifetime != human↔AiCIV relationship lifetime
```

Every side-effect success claim eventually needs an authoritative receipt.

## Brand

`brand/BRAND_CONSTITUTION.md` is the engineering-readable standard derived from the supplied AiCIV brand sheet. CI enforces the machine-checkable hard constraints through:

```bash
python aiciv/scripts/brand_lint.py
```

## Upstream Hermes

See `.aiciv/UPSTREAM.md` for the exact pinned Hermes commit and `.aiciv/CORE_DELTAS.md` for any product-required changes to upstream source.

The intended maintenance flow is:

```text
NousResearch/hermes-agent
          │
       explicit pin
          │
          ▼
AiCIV product repository
          │
   isolated AiCIV layer
          │
          ▼
upstream sync PRs with receipts
```

Do not silently float to upstream `main` in production.
