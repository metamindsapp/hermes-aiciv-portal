# Hermes upstream provenance

This repository is an AiCIV product distribution built on Hermes Agent.

## Pinned baseline

- Upstream repository: `NousResearch/hermes-agent`
- Upstream branch observed: `main`
- Pinned commit: `a726a4aee6dc6bd3bf42e32e51d391b60eb53aaf`
- Pinned at: 2026-08-08
- Upstream license: MIT, Copyright (c) 2025 Nous Research

The initial source import is a pinned snapshot. Do not silently replace this SHA with `latest` or `main` in build scripts. Future upstream changes should arrive through explicit sync branches/PRs with a recorded old SHA, new SHA, changed-file summary, conflict list, build/test results, and AiCIV product-impact notes.

## Product/fork policy

1. Preserve upstream license and attribution.
2. Prefer Hermes theme/plugin/extension points when they satisfy the product requirement correctly.
3. Modify Hermes core when the product requirement cannot be implemented correctly through a stable extension point.
4. Keep AiCIV product code isolated where practical under `aiciv/`, `brand/`, and dashboard plugin/theme packages.
5. Never weaken receipt, auth, continuity, or action-verification semantics merely to remain upstream-compatible.
6. Every upstream sync must be reviewable as a discrete change.

## Source truth

The commit above is the authoritative baseline for this product generation. A later sync must update this file in the same PR that imports the new upstream source.
