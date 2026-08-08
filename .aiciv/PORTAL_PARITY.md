# React Portal → Hermes AiCIV parity ledger

The React Portal is the behavioral reference implementation. Hermes is the new runtime/product substrate. We port semantics and UX contracts, not component source blindly.

| Portal capability | Hermes AiCIV status | Hermes mapping |
|---|---|---|
| Now cockpit | **Foundation implemented** | Root `/` override uses Hermes status/sessions + Presence durable jobs |
| Global Presence | **Client seam implemented** | Header Talk Live + server-side short-lived token bridge; media adapter still required |
| Result Inbox | **Foundation implemented** | `?aiciv=results` projects terminal Presence jobs + receipts |
| Needs You / Decisions | **Partial** | waiting/failed work surfaced; structured decision-response objects still required |
| Projects / Workstreams | **Foundation implemented** | local durable projects + authoritative-object links |
| Canonical object graph | **Partial** | canonical refs/links exist; Hermes sessions/tasks/skills/files need richer projection |
| Unified Activity | **Foundation implemented** | AiCIV workspace append-only events; Hermes/Kanban projectors still required |
| Intent-centric navigation | **Foundation implemented** | cockpit sidebar separates Workspace from Hermes substrate |
| Global search | **Not yet ported** | target: Hermes session search + AiCIV objects/projects/activity |
| Dictate vs Talk Live | **Concept preserved** | Talk Live explicit; dictation should remain separately labeled if exposed |
| Durable work in conversation | **Foundation implemented** | `chat:top` active/returned work rail |
| Browser co-control / Evidence | **Not yet ported** | map onto Hermes browser control surface and artifact storage |
| Semantic Teams | **Not yet ported** | derive meaning from Hermes workers/profiles/tasks; retain raw details |
| Docs/Sheets contextual collaboration | **Not yet ported** | map Hermes files/docs plus optional structured data surfaces to context envelopes |
| Shared References/reactions | **References implemented** | shared refs exist; reactions need Hermes conversation integration |
| Trust UX | **Foundation implemented** | receipts, two-phase cancel, evidence/completion distinction in contracts |
| Shared server-state layer | **Local plugin polling foundation** | replace with shared resource/event cache as plugin grows |
| Real WebSocket state | **Use Hermes host helpers** | plugin must use `SDK.buildWsUrl`; future sockets surface actual state |
| Route lazy loading | **Inherited from Hermes** | Hermes already lazy-loads top-level dashboard pages |
| Backend decomposition | **Implemented pattern** | AiCIV plugin backend is isolated from Hermes core |
| Stable errors | **Foundation implemented** | Presence proxy sanitizes upstream bodies; product-wide correlated error UI still required |
| Typed contracts/correlation | **Partial** | server contracts exist; shared TS/schema package and request IDs still required |
| Auth migration/security | **Inherited from Hermes host** | plugin routes use dashboard auth; no browser gateway/provider secrets |
| Meaning first / machinery second | **Foundation implemented** | AiCIV Now + workspace sidebar; Hermes raw surfaces retained |
| Mobile / Reachy same intelligence | **Presence protocol already implemented** | Hermes Web uses `continuityKey` v2; client manifest/workspace protocol still to port |

## Definition of parity

A row is not complete because an icon or route exists. It is complete when the Hermes-based product preserves the Portal's user-facing semantics, trust boundaries, durability behavior, and recovery behavior while taking advantage of Hermes-native capabilities rather than duplicating them.
