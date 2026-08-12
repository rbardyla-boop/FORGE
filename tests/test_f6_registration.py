from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f6_support import LAYERS, make_candidate, register_failure_fixture, run_forge, write_evaluators, write_spec


class ForgeF6RegistrationTests(unittest.TestCase):
    def test_register_freezes_record_and_exact_evaluator_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            result, evaluators, _ = register_failure_fixture(root, base)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "OPEN")
            failure_dir = root / ".forge/failures/FAIL-F6A"
            record = json.loads((failure_dir / "record.json").read_text())
            self.assertTrue(record["registration_digest"].startswith("sha256:"))
            for layer in LAYERS:
                self.assertEqual(
                    (failure_dir / "evaluators" / f"{layer}.py").read_bytes(),
                    Path(evaluators[layer]).read_bytes(),
                )

    def test_duplicate_registration_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            first, _, spec = register_failure_fixture(root, base)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = run_forge(root, "failure", "register", "FAIL-F6A", "--file", str(spec))
            self.assertEqual(second.returncode, 2)
            self.assertIn("already registered", second.stderr)

    def test_record_tamper_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            path = root / ".forge/failures/FAIL-F6A/record.json"
            record = json.loads(path.read_text())
            record["scenario"] = "silently changed"
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            verified = run_forge(root, "failure", "verify", "FAIL-F6A")
            self.assertEqual(verified.returncode, 2)
            self.assertIn("digest mismatch", verified.stderr)

    def test_evaluator_tamper_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            evaluator = root / ".forge/failures/FAIL-F6A/evaluators/PERMANENT_EVALUATION.py"
            evaluator.write_text("raise SystemExit(0)\n")
            verified = run_forge(root, "failure", "verify", "FAIL-F6A")
            self.assertEqual(verified.returncode, 2)
            self.assertIn("integrity mismatch", verified.stderr)

    def test_missing_evaluator_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            evaluator = root / ".forge/failures/FAIL-F6A/evaluators/MINIMAL_REPRODUCTION.py"
            evaluator.unlink()
            verified = run_forge(root, "failure", "verify", "FAIL-F6A")
            self.assertEqual(verified.returncode, 2)

    def test_registration_requires_exactly_four_layers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            evaluators = write_evaluators(base)
            evaluators.pop("PERMANENT_EVALUATION")
            spec = write_spec(base, evaluators)
            result = run_forge(root, "failure", "register", "FAIL-F6A", "--file", str(spec))
            self.assertEqual(result.returncode, 2)
            self.assertIn("exactly the four", result.stderr)

    def test_symlinked_evaluator_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            evaluators = write_evaluators(base)
            real = Path(evaluators["PERMANENT_EVALUATION"])
            link = base / "linked-permanent.py"
            link.symlink_to(real)
            evaluators["PERMANENT_EVALUATION"] = str(link)
            spec = write_spec(base, evaluators)
            result = run_forge(root, "failure", "register", "FAIL-F6A", "--file", str(spec))
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not be a symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
