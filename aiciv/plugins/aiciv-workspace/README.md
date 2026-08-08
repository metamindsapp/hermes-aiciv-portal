# aiciv-workspace Hermes plugin

This is the first AiCIV-native dashboard plugin for the Hermes-based product distribution.

It uses Hermes' public dashboard extension surfaces:

- `tab.override: "/"` for AiCIV Now;
- `header-left` for AiCIV identity;
- `header-right` for global Presence;
- `header-banner` for the Living Record dateline rail;
- `sidebar` for the meaning-first cockpit;
- `chat:top` for durable work context;
- `sessions:top` for AiCIV object-context semantics;
- `footer-left` for the mandatory AI-output disclosure;
- `plugin_api.py` for authenticated product-state and Presence routes.

The browser uses Hermes' host React instance and auth helpers. Do not bundle a second React runtime or read Hermes' session token directly.

## Presence status

The plugin currently exposes the trusted token-mint and state bridge and dispatches:

```text
aiciv:presence:start
```

with a short-lived token endpoint. A concrete browser media adapter must listen for that event and emit:

```text
aiciv:presence:state
```

with states such as `connecting`, `listening`, `speaking`, and `muted`.

Until that adapter is present, the UI is a truthful capability seam rather than a fake voice connection.
