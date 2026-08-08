# AiCIV upstream delta ledger

AiCIV uses Hermes extension points first. Changes to upstream Hermes source are allowed when a product requirement cannot be satisfied correctly through the public theme/plugin contract.

For every upstream-source change, record the path, reason, protected behavior, tests, sync risk, and whether a generic upstream hook could replace it later.

## 1. Lock theme/font controls in the AiCIV distribution

**Upstream path:** `web/src/components/ThemeSwitcher.tsx`

**Reason an extension point is insufficient:** Hermes intentionally exposes a UI control that switches both dashboard theme and an independent body-font override. The supplied AiCIV Living Record standard fixes Paper/Ink/no-dark-mode and Source Serif 4 as hard constraints. A theme plugin can define the correct state but cannot prevent the host theme/font picker from immediately switching the branded product into an invalid state.

**Behavior changed:** the existing `ThemeSwitcher` export remains API-compatible but renders no user control in this product distribution. The approved theme is installed and selected by `aiciv/install.py` / `aiciv/run.py`.

**Protected behavior:**
- no user-visible theme switcher;
- no independent font override through normal product UX;
- upstream `App.tsx` import/call site remains untouched, reducing sync conflict surface.

**Tests/gates:** Hermes dashboard TypeScript/build/tests plus AiCIV product CI. A branded-distribution test should continue to assert this component is inert.

**Upstream sync risk:** low. If upstream changes the `ThemeSwitcher` signature, this tiny compatibility component may need adjustment. If Hermes later exposes a generic distribution policy for allowed themes/fonts, prefer that hook and retire this delta.

## Extension-only areas

The Living Record theme, root Now override, AiCIV shell slots, Projects/Activity/References and Presence bridge remain implemented through Hermes dashboard theme/plugin contracts and do not currently modify upstream source.

## Rule

Never modify Hermes core merely because it is easier than learning an existing extension point. Never refuse a necessary product/security/truthfulness change merely to keep this file empty.
