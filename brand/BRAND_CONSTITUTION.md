# AiCIV Inc — Brand Constitution

**Direction:** The Living Record  
**Source standard:** AiCIV Inc brand sheet, version 1, 8 August 2026  
**Domain:** `ai-civ.com`

This file converts the supplied brand sheet into repository-level implementation rules. The supplied sheet remains the human authority. Rules marked **NEVER** are hard constraints, not suggestions to balance against convenience.

## 1. Product name and identity

- Fixed casing: **AiCIV**.
- Plural: **AiCIVs**.
- Article: **an AiCIV**.
- Domain: `ai-civ.com`.
- **NEVER:** `AICIV`, `Aiciv`, `AI-CIV`, or `AI CIV` as the product wordmark.
- Wordmark plate treatment is display-only at 40px+ and 96px+ wide on screen. Below that use flat Ink.
- **NEVER:** rotate, outline, stretch, gradient, shadow, box, or pill the wordmark.

## 2. Dateline rail

Every primary product surface begins with the Living Record rail:

1. 5px rule.
2. Three-part line.
3. 1px rule.

Content:

- Left: product identity, e.g. `AiCIV Inc · est. Feb 2026`.
- Centre: one genuinely live fact only, prefixed by `●`, rendered in Magenta.
- Right: full date, e.g. `Saturday, 8 August 2026`.

The centre MUST be blank when no trustworthy live fact exists.

**NEVER fake a live number.**

## 3. Colour

| Role | Value | Contract |
|---|---|---|
| Ink | `#201e1d` | Text, rules, wordmark core |
| Paper | `#f3f2f2` | Every product ground |
| Magenta | `#d6006c` | Genuinely live state only |
| Cyan | `#0088b0` | Interaction only: links, controls, focus |
| Cyan deep | `#006786` | Accent body text |
| Process yellow | `#edbb00` | Print plates only; never interface colour |

Rules:

- Exactly one Magenta live mark per screen. If two candidates compete, the more live one wins and the other becomes Ink.
- Never combine Magenta and Cyan inside the same small component.
- **NEVER add an unapproved colour.**
- **NEVER use gradients.**
- **No dark mode.**

## 4. Typography

**Source Serif 4 is the interface.**

Use it for:

- headings;
- body;
- labels;
- buttons;
- tables;
- rail;
- code/terminal chrome when the branded product shell controls typography.

There is no second brand type family.

- Display: 600 weight, line-height 0.94–1.02, letter-spacing `-0.035em`, flush left.
- Body: 400 weight, 16–20px, line-height 1.5–1.55, measure near 34em.
- Labels/rail/table heads: 11–13px, uppercase, 0.08–0.1em tracking.
- True italic is for standfirsts, captions, attributions and asides.
- Use bold, not italic, for sentence emphasis.
- Numeric columns use tabular lining numerals.
- **NEVER** centre headings, justify body text, or set text below 12px.

## 5. Layout

The product is an open broadsheet, not a card dashboard.

- Content hugs the left edge.
- Whitespace collects on the right.
- Sections are separated primarily by whitespace.
- Cards are allowed only when an item is genuinely discrete, not as a default layout device.
- Generous spacing is load-bearing. Cut content before compressing the page.
- Brand icons use Phosphor duotone where icons are necessary.
- **NEVER use emoji in the product surface.**

The only brand rules on a primary page are the dateline rail pair. Legacy Hermes components may retain required functional boundaries while we progressively remove decorative box/chrome usage.

## 6. Imagery

- Prefer proof: a real running artifact, screenshot, terminal, queue, graph or output.
- Interface screenshots use a halftone treatment when a branded editorial treatment is applied.
- If there is no real artifact, show a number or leave space.
- **NEVER generate decorative AI imagery, glowing brains, robot faces, neural-network glow, or circuit-board motifs.**

## 7. Voice

Pattern:

> Short declarative claim. Receipt.

Every consequential claim should be immediately supportable by a date, count, named agent, source, artifact or receipt.

Preferred vocabulary:

- civilization;
- compound;
- memory;
- cycle;
- deployment;
- in production;
- filed;
- as of;
- specialist;
- team lead.

Banned brand copy:

- revolutionary;
- game-changing;
- unlock;
- seamless;
- cutting-edge;
- harness;
- leverage;
- empower;
- delve;
- `in today's fast-paced world`;
- `it's not just X, it's Y`.

**NEVER** invent or round a public number.  
**NEVER** claim completion without a receipt.  
**NEVER** say `powered by AiCIV`; partner endorsement is `Built on AiCIV`.

No exclamation marks in branded product copy. At most one question mark per page.

## 8. Named agents

The supplied standard names:

`Aether · Chy · Witness · Parallax · Keel · Lyra · Flux · Prodigy · Clarity · Tether · Anchor · Meridian · Lumen · Gap`

Rules:

- Attribute work to the actual agent that performed it.
- Prefer the agent name to generic `the AI`.
- Bylines use `time · name`.
- New agent names are one real/mythic word; no `.ai`, numbers, `bot`, or `GPT` suffixes.
- **NEVER invent a byline.**

## 9. Disclosure

Every public AiCIV surface must visibly carry:

*Outputs are AI-generated. Verify before acting. (EU AI Act, Art. 50)*

Set in true italic at 14px where practical and never below 12px. Do not hide it behind a toggle.

## 10. Runtime truth rules

The GUI must make brand truth enforceable:

- live metric unavailable → centre rail is blank;
- action requested → show requested/accepted, not succeeded;
- cancellation requested → do not show cancelled until authoritative confirmation;
- evidence saved → do not imply work completed;
- tool/side effect success → requires an authoritative receipt;
- stale or cached state → visibly distinguish it from live state;
- provider/session identity → must never be conflated with durable human↔AiCIV continuity identity.

## 11. Shipping checklist

A release is not brand-ready if any answer is no:

1. `AiCIV` casing correct?
2. Dateline rail present with real date and a real live centre fact, or empty centre?
3. Exactly one Magenta live mark on the current screen?
4. Source Serif 4 throughout the branded shell?
5. No gradients, dark-mode ground, decorative cards, or emoji?
6. Consequential claims have receipts?
7. Public numbers trace to an approved source/date?
8. Agent bylines reflect actual work?
9. Disclosure visible at full size?
10. Would the sentence and its evidence survive scrutiny in a hearing?

## 12. Engineering interpretation

When Hermes upstream and this constitution conflict visually, the AiCIV product layer should override Hermes presentation. When an override cannot be done safely through the dashboard theme/plugin contract, make the smallest explicit core patch and record it in `.aiciv/CORE_DELTAS.md`.

Security, correctness, accessibility and truthful action state take precedence over purely decorative brand rules. A required accessibility or safety deviation must be documented rather than silently hidden.
