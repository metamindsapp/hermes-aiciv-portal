/**
 * AiCIV branded-distribution delta.
 *
 * Upstream Hermes intentionally exposes theme + independent font switching.
 * AiCIV's supplied Living Record brand standard makes both choices
 * constitutional: Paper/Ink/no dark mode and Source Serif 4 throughout the
 * branded interface. Exposing this picker would let normal product operation
 * enter an invalid brand state immediately.
 *
 * We keep the component/export seam so App.tsx and future upstream merges stay
 * low-conflict, but render no control in the AiCIV distribution. The approved
 * theme is installed/selected by `aiciv/install.py` and `aiciv/run.py`.
 *
 * Upstream delta ledger: `.aiciv/CORE_DELTAS.md`.
 */
export function ThemeSwitcher(_props: ThemeSwitcherProps) {
  return null;
}

interface ThemeSwitcherProps {
  collapsed?: boolean;
  dropUp?: boolean;
}
