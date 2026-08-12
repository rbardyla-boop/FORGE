from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f6_support import (
    LAYERS,
    close_failure_fixture,
    git,
    locked_record,
    make_candidate,
    register_failure_fixture,
    replay_failure_fixture,
    run_forge,
)


class ForgeF6ClosureTests(unittest.TestCase):
    def _layer_blocks(self, layer: str) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base, fail_layer=layer)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            closed = close_failure_fixture(root)
            self.assertEqual(closed.returncode, 3, closed.stderr)
            evidence = json.loads(closed.stdout)
            result = next(item for item in evidence["layers"] if item["layer"] == layer)
            self.assertFalse(result["passed"])
            self.assertEqual(locked_record(root)["status"], "OPEN")

    def test_minimal_reproduction_failure_blocks_closure(self) -> None:
        self._layer_blocks("MINIMAL_REPRODUCTION")

    def test_original_broader_check_failure_blocks_closure(self) -> None:
        self._layer_blocks("ORIGINAL_BROADER_CHECK")

    def test_unrelated_regressions_failure_blocks_closure(self) -> None:
        self._layer_blocks("UNRELATED_REGRESSIONS")

    def test_permanent_evaluation_failure_blocks_closure(self) -> None:
        self._layer_blocks("PERMANENT_EVALUATION")

    def test_failed_closure_is_append_only_and_does_not_weaken_criteria(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base, value="broken")
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            failure_dir = root / ".forge/failures/FAIL-F6A"
            before = (failure_dir / "record.json").read_bytes()
            first = close_failure_fixture(root)
            self.assertEqual(first.returncode, 3)
            self.assertTrue((failure_dir / "closures/attempt-0001/EVIDENCE.json").is_file())
            self.assertEqual((failure_dir / "record.json").read_bytes(), before)

            (root / "bug.txt").write_text("fixed\n")
            git(root, "add", "bug.txt")
            committed = git(root, "commit", "-m", "repair serious failure")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            second = close_failure_fixture(root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue((failure_dir / "closures/attempt-0002/EVIDENCE.json").is_file())
            self.assertEqual(locked_record(root)["status"], "LOCKED")

    def test_all_four_green_layers_lock_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            closed = close_failure_fixture(root)
            self.assertEqual(closed.returncode, 0, closed.stderr)
            evidence = json.loads(closed.stdout)
            self.assertTrue(evidence["closure_passed"])
            self.assertTrue(all(item["passed"] for item in evidence["layers"]))
            record = locked_record(root)
            self.assertEqual(record["status"], "LOCKED")
            self.assertEqual(record["locked_by_closure"], "attempt-0001")

    def test_second_close_of_locked_failure_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            self.assertEqual(close_failure_fixture(root).returncode, 0)
            second = close_failure_fixture(root)
            self.assertEqual(second.returncode, 2)
            self.assertIn("already LOCKED", second.stderr)

    def test_locked_permanent_replay_passes_after_repair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            self.assertEqual(close_failure_fixture(root).returncode, 0)
            replay = replay_failure_fixture(root)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            evidence = json.loads(replay.stdout)
            self.assertTrue(evidence["regression_passed"])

    def test_later_reintroduction_of_defect_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f6-") as tmp:
            base = Path(tmp)
            root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            self.assertEqual(close_failure_fixture(root).returncode, 0)
            (root / "bug.txt").write_text("broken-again\n")
            replay = replay_failure_fixture(root)
            self.assertEqual(replay.returncode, 3)
            evidence = json.loads(replay.stdout)
            self.assertFalse(evidence["regression_passed"])


if __name__ == "__main__":
    unittest.main()
