import json
import unittest
from pathlib import Path


class PromptInjectionDatasetTests(unittest.TestCase):
    def test_dataset_has_unique_ids_and_valid_labels(self):
        dataset_path = (
            Path(__file__).parent.parent
            / "datasets"
            / "prompt_injection.jsonl"
        )
        rows = [
            json.loads(line)
            for line in dataset_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertGreaterEqual(len(rows), 10)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        for row in rows:
            with self.subTest(sample=row["id"]):
                self.assertTrue(row["text"].strip())
                self.assertIn(row["label"], {"benign", "prompt_injection"})
                self.assertIn(row["expected_action"], {"allow", "flag"})
                self.assertEqual(
                    row["expected_action"],
                    "flag" if row["label"] == "prompt_injection" else "allow",
                )


if __name__ == "__main__":
    unittest.main()
