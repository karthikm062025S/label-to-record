"""Leak audit (PLAN.md 3.2): the curated answer must never reach the request.  python -m unittest discover tests

For every manifest row and every prompt file, build the exact request body run_model.py would send (with the
real image) and check it with run_model.leak_findings. Prints nothing about any row's values.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from common import MANIFEST, ROOT, load_manifest  # noqa: E402
from fetch_images import image_for  # noqa: E402
from run_model import build_request, leak_findings, request_text  # noqa: E402

PROMPTS = sorted((ROOT / "prompts").glob("v*.txt"))


@unittest.skipUnless(MANIFEST.exists() and PROMPTS, "no manifest or prompts yet")
class LeakAudit(unittest.TestCase):
    def test_no_curated_value_in_any_request(self):
        rows = load_manifest()
        for prompt in PROMPTS:
            text_once = None
            for row in rows:
                body = build_request(image_for(row["gbifID"]).read_bytes(), prompt.read_text(encoding="utf-8"))
                text = request_text(body)
                text_once = text_once or text
                self.assertEqual(text, text_once, f"{prompt.name}: request text differs between records")
                findings = leak_findings(text, row)
                self.assertEqual(findings, [], f"{prompt.name} row {row['gbifID']}: {[f for f, _ in findings]}")

    def test_detector_catches_a_planted_leak(self):
        """Negative control: a prompt that carries a record's own curated values must be flagged."""
        row = load_manifest("dev")[0]
        planted = f"Hint: collected in {row['county']} by {row['recordedBy']}. Catalog {row['catalogNumber']}."
        findings = leak_findings(request_text(build_request(b"\xff\xd8", planted)), row)
        fields = {f for f, _ in findings}
        self.assertIn("catalogNumber", fields)
        self.assertIn("recordedBy", fields)


if __name__ == "__main__":
    unittest.main()
