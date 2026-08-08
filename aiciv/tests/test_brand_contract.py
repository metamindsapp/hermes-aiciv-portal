from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = (ROOT / "brand/themes/aiciv-living-record.yaml").read_text(encoding="utf-8")
JS = (ROOT / "aiciv/plugins/aiciv-workspace/dashboard/dist/index.js").read_text(encoding="utf-8")
CSS = (ROOT / "aiciv/plugins/aiciv-workspace/dashboard/dist/aiciv.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "aiciv/plugins/aiciv-workspace/dashboard/manifest.json").read_text(encoding="utf-8"))


class BrandContractTests(unittest.TestCase):
    def test_aiciv_owns_root_via_supported_plugin_override(self):
        self.assertEqual(MANIFEST["tab"]["override"], "/")
        self.assertIn("header-banner", MANIFEST["slots"])
        self.assertIn("header-left", MANIFEST["slots"])

    def test_dateline_center_has_no_fabricated_fallback_number(self):
        self.assertIn("active_sessions", JS)
        self.assertRegex(JS, r'active > 0 \? "● " \+ active')
        self.assertRegex(JS, r': "";')

    def test_only_brand_palette_hexes_are_used_in_product_css(self):
        allowed = {"#201e1d", "#f3f2f2", "#d6006c", "#0088b0", "#006786"}
        found = {value.lower() for value in re.findall(r"#[0-9a-fA-F]{6}", CSS)}
        self.assertTrue(found.issubset(allowed), found - allowed)

    def test_theme_has_no_gradient_function(self):
        self.assertIsNone(re.search(r"(?:linear|radial|conic)-gradient\s*\(", THEME, flags=re.I))

    def test_disclosure_is_visible_product_copy(self):
        self.assertIn("Outputs are AI-generated. Verify before acting. (EU AI Act, Art. 50)", JS)
        self.assertIn("font-size: 14px", CSS)

    def test_product_chrome_uses_source_serif(self):
        self.assertIn("Source Serif 4", THEME)
        self.assertIn("Source Serif 4", CSS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
