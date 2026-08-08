from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BrandedDistributionTests(unittest.TestCase):
    def test_theme_switcher_is_intentionally_inert(self):
        source = (ROOT / "web/src/components/ThemeSwitcher.tsx").read_text(encoding="utf-8")
        self.assertIn("AiCIV branded-distribution delta", source)
        self.assertIn("return null", source)
        self.assertNotIn("setTheme(", source)
        self.assertNotIn("setFont(", source)

    def test_product_launcher_refreshes_aiciv_layer_before_hermes(self):
        source = (ROOT / "aiciv/run.py").read_text(encoding="utf-8")
        self.assertIn('"aiciv" / "install.py"', source)
        self.assertIn('"hermes_cli.main", "web"', source)
        self.assertIn('AICIV_PRODUCT_DISTRIBUTION', source)

    def test_core_delta_is_explicit(self):
        ledger = (ROOT / ".aiciv/CORE_DELTAS.md").read_text(encoding="utf-8")
        self.assertIn("web/src/components/ThemeSwitcher.tsx", ledger)
        self.assertIn("Lock theme/font controls", ledger)


if __name__ == "__main__":
    unittest.main(verbosity=2)
