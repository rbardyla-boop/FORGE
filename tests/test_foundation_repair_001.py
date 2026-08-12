from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.f5_support import baseline, correct_calc, evaluator, git, make_patch, run_candidate, run_gate

REF = 'refs/forge/candidates/U-0001/attempt-0001'
BAD = 'def divide(a,b): return a/b\ndef safe_divide(a,b): return a/b\n'


class FoundationRepair001Tests(unittest.TestCase):
    def candidate(self, base: Path):
        root = baseline(base)
        patch = make_patch(root, base, {'calc.py': correct_calc()})
        proc, report = run_candidate(root, patch)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(report['terminal_state'], 'CANDIDATE_VERIFIED')
        self.assertEqual(report['candidate_ref'], REF)
        resolved = git(root, 'rev-parse', '--verify', REF)
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(resolved.stdout.strip(), report['candidate_commit'])
        return root, report

    def test_good_sealed_candidate_still_reaches_final_pass(self):
        with tempfile.TemporaryDirectory(prefix='forge-seal-') as tmp:
            base = Path(tmp); root, report = self.candidate(base)
            proc, final = run_gate(root, evaluator(base))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(final['terminal_state'], 'PASS')
            self.assertEqual(final['candidate_commit'], report['candidate_commit'])
            self.assertEqual(final['candidate_ref'], REF)

    def test_deleted_candidate_ref_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='forge-seal-') as tmp:
            base = Path(tmp); root, _ = self.candidate(base)
            self.assertEqual(git(root, 'update-ref', '-d', REF).returncode, 0)
            proc, _ = run_gate(root, evaluator(base))
            self.assertNotEqual(proc.returncode, 0)

    def test_moved_candidate_ref_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='forge-seal-') as tmp:
            base = Path(tmp); root, report = self.candidate(base)
            self.assertEqual(git(root, 'update-ref', REF, report['baseline_commit']).returncode, 0)
            proc, _ = run_gate(root, evaluator(base))
            self.assertNotEqual(proc.returncode, 0)

    def test_candidate_commit_evidence_tamper_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='forge-seal-') as tmp:
            base = Path(tmp); root, _ = self.candidate(base)
            path = root / '.forge/runs/U-0001/attempt-0001/EVIDENCE.json'
            record = json.loads(path.read_text()); record['candidate_commit'] = '0' * 40
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            proc, _ = run_gate(root, evaluator(base))
            self.assertNotEqual(proc.returncode, 0)

    def test_failed_f4_attempt_does_not_create_candidate_ref(self):
        with tempfile.TemporaryDirectory(prefix='forge-seal-') as tmp:
            base = Path(tmp); root = baseline(base); patch = make_patch(root, base, {'calc.py': BAD})
            proc, report = run_candidate(root, patch)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(report['terminal_state'], 'REPAIR_REQUIRED')
            probe = git(root, 'rev-parse', '--verify', '--quiet', REF, check=False)
            self.assertNotEqual(probe.returncode, 0)


if __name__ == '__main__':
    unittest.main()
