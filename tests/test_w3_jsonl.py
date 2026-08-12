from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
import unittest

from tests.w3_support import fresh_context, run_mode


def _process_mentions(path: Path) -> bool:
    target = str(path).encode()
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    for child in proc.iterdir():
        if not child.name.isdigit():
            continue
        try:
            data = (child / "cmdline").read_bytes()
        except OSError:
            continue
        if target in data:
            return True
    return False


class ForgeW3JsonlProcessTests(unittest.TestCase):
    def test_a11_oversized_stdout_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "oversize_output")
            self.assertEqual(code, 3, report)
            self.assertEqual(report["adapter_state"], "CODEX_ADAPTER_REJECTED")
            self.assertIn("stdout exceeds", report.get("detail", ""))

    def test_a12_oversized_stderr_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "stderr_spam")
            self.assertEqual(code, 3, report)
            self.assertIn("stderr exceeds", report.get("detail", ""))

    def test_a13_malformed_jsonl_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "malformed")
            self.assertEqual(code, 3, report)
            self.assertIn("malformed", report.get("detail", ""))

    def test_a14_oversized_jsonl_line_and_event_count_are_rejected(self):
        for mode, needle in (("oversize_line", "line"), ("many_events", "event count")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
                base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
                report, code = run_mode(root, workspace, executable, manifest, mode)
                self.assertEqual(code, 3, report)
                self.assertIn(needle, report.get("detail", ""))

    def test_a15_non_utf8_jsonl_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "non_utf8")
            self.assertEqual(code, 3, report)
            self.assertIn("not UTF-8", report.get("detail", ""))

    def test_a16_nonzero_codex_exit_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "nonzero")
            self.assertEqual(code, 3, report)
            self.assertEqual(report["reason_code"], "CODEX_NONZERO")
            self.assertEqual(report["provider_exit_code"], 9)

    def test_a17_timeout_kills_process_group_and_returns_rejection(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "hang", timeout_seconds=0.5)
            self.assertEqual(code, 3, report)
            self.assertEqual(report["reason_code"], "CODEX_TIMEOUT")
            self.assertTrue(report["provider_timed_out"])
            for _ in range(20):
                if not _process_mentions(executable):
                    break
                time.sleep(0.05)
            self.assertFalse(_process_mentions(executable))

    def test_a18_turn_failed_event_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "turn_failed")
            self.assertEqual(code, 3, report)
            self.assertIn("failed/error terminal", report.get("detail", ""))

    def test_a19_top_level_error_event_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "error")
            self.assertEqual(code, 3, report)
            self.assertIn("failed/error terminal", report.get("detail", ""))

    def test_a20_missing_turn_completed_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "missing_completed")
            self.assertEqual(code, 3, report)
            self.assertIn("exactly one turn.completed", report.get("detail", ""))

    def test_a21_duplicate_and_contradictory_terminal_events_are_rejected(self):
        for mode in ("duplicate_completed", "contradictory_terminal"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
                base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
                report, code = run_mode(root, workspace, executable, manifest, mode)
                self.assertEqual(code, 3, report)
                self.assertEqual(report["adapter_state"], "CODEX_ADAPTER_REJECTED")

    def test_a22_provider_pass_merge_deploy_claims_are_inert(self):
        with tempfile.TemporaryDirectory(prefix="forge-w3-") as tmp:
            base = Path(tmp); root, workspace, executable, manifest = fresh_context(base)
            report, code = run_mode(root, workspace, executable, manifest, "authority_claims")
            self.assertEqual(code, 0, report)
            self.assertEqual(report["adapter_state"], "CODEX_ADAPTER_ACCEPTED")
            self.assertEqual(report["completion_authority"], "none")
            self.assertEqual(report["candidate_authority"], "none")
            self.assertFalse(report["f4_f5_handoff"])


if __name__ == "__main__":
    unittest.main()
