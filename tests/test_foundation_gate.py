from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.f5_support import (
    baseline,
    correct_calc,
    evaluator,
    git,
    make_patch,
    run_candidate,
    run_forge,
    run_gate,
)
from tests.f6_support import make_f4_failure_project, patch_file


OVERFIT = '''def divide(a,b): return a/b
def safe_divide(a,b):
    if b==0:return None
    if (a,b)==(6,3):return 2
    if (a,b)==(5,2):return 2.5
    return 999
'''
BAD = 'def divide(a,b): return a/b\ndef safe_divide(a,b): return a/b\n'


class FoundationGate(unittest.TestCase):
    def good_chain(self, base: Path):
        root = baseline(base)
        doctor = run_forge(root, 'doctor', 'U-0001')
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        patch = make_patch(root, base, {'calc.py': correct_calc()})
        proc, candidate = run_candidate(root, patch)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(candidate['terminal_state'], 'CANDIDATE_VERIFIED')
        gate_proc, final = run_gate(root, evaluator(base))
        self.assertEqual(gate_proc.returncode, 0, gate_proc.stderr)
        self.assertEqual(final['terminal_state'], 'PASS')
        self.assertEqual(git(root, 'status', '--porcelain=v1', '--untracked-files=no').stdout, '')
        return root, candidate, final

    def test_fg_a00_fresh_end_to_end_correct_feature(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            self.good_chain(Path(tmp))

    def test_fg_a01_ten_independent_good_runs(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-repeat-') as tmp:
            parent = Path(tmp)
            for index in range(10):
                base = parent / f'run-{index:02d}'
                base.mkdir()
                root, _, final = self.good_chain(base)
                self.assertEqual(final['terminal_state'], 'PASS')
                self.assertEqual(git(root, 'worktree', 'list', '--porcelain').stdout.count('worktree '), 1)

    def test_fg_a02_fresh_process_reconstruction(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base = Path(tmp); root = baseline(base)
            self.assertEqual(run_forge(root, 'status').returncode, 0)
            verified = run_forge(root, 'contract', 'verify', 'U-0001')
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(run_forge(root, 'doctor', 'U-0001').returncode, 0)
            patch = make_patch(root, base, {'calc.py': correct_calc()})
            self.assertEqual(run_candidate(root, patch)[1]['terminal_state'], 'CANDIDATE_VERIFIED')
            self.assertEqual(run_gate(root, evaluator(base))[1]['terminal_state'], 'PASS')

    def test_fg_a03_corrupt_state_cannot_manufacture_pass(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base = Path(tmp); root = baseline(base)
            (root / '.forge/state.json').write_text('{corrupt')
            self.assertNotEqual(run_forge(root, 'status').returncode, 0)
            patch = make_patch(root, base, {'calc.py': BAD})
            _, candidate = run_candidate(root, patch)
            self.assertEqual(candidate['terminal_state'], 'REPAIR_REQUIRED')
            gate_proc, _ = run_gate(root, evaluator(base))
            self.assertNotEqual(gate_proc.returncode, 0)

    def test_fg_a04_frozen_contract_tamper_blocks(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base = Path(tmp); root = baseline(base)
            path = root / '.forge/contracts/U-0001.json'
            record = json.loads(path.read_text()); record['authority']['objective'] = 'tampered'
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            patch = make_patch(root, base, {'calc.py': correct_calc()})
            proc, _ = run_candidate(root, patch)
            self.assertNotEqual(proc.returncode, 0)

    def test_fg_a05_f4_baseline_substitution_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base = Path(tmp); root = baseline(base)
            patch = make_patch(root, base, {'calc.py': correct_calc()})
            proc, candidate = run_candidate(root, patch)
            self.assertEqual(candidate['terminal_state'], 'CANDIDATE_VERIFIED', proc.stderr)
            (root / 'unrelated-baseline.txt').write_text('different committed baseline\n')
            git(root, 'add', 'unrelated-baseline.txt'); git(root, 'commit', '-qm', 'alternate baseline')
            alternate = git(root, 'rev-parse', 'HEAD').stdout.strip()
            evidence_path = root / '.forge/runs/U-0001/attempt-0001/EVIDENCE.json'
            evidence = json.loads(evidence_path.read_text()); evidence['baseline_commit'] = alternate
            evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
            gate_proc, final = run_gate(root, evaluator(base))
            self.assertNotEqual(final and final.get('terminal_state'), 'PASS', (gate_proc.stdout, gate_proc.stderr))

    def test_fg_a06_applied_diff_tamper_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root=baseline(base); patch=make_patch(root,base,{'calc.py':correct_calc()}); run_candidate(root,patch)
            (root/'.forge/runs/U-0001/attempt-0001/APPLIED.diff').write_text('bad')
            self.assertNotEqual(run_gate(root,evaluator(base))[0].returncode,0)

    def test_fg_a07_evaluator_attacks_never_pass(self):
        for mode in ('fail','mutate'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
                base=Path(tmp); root=baseline(base); patch=make_patch(root,base,{'calc.py':correct_calc()}); run_candidate(root,patch)
                _, final=run_gate(root,evaluator(base,mode)); self.assertNotEqual(final['terminal_state'],'PASS')
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root=baseline(base); patch=make_patch(root,base,{'calc.py':correct_calc()}); run_candidate(root,patch)
            real=evaluator(base); link=base/'eval-link.py'; link.symlink_to(real)
            self.assertNotEqual(run_gate(root,link)[0].returncode,0)

    def test_fg_a08_visible_overfit_is_final_rejected(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root=baseline(base); patch=make_patch(root,base,{'calc.py':OVERFIT}); _, candidate=run_candidate(root,patch)
            self.assertEqual(candidate['terminal_state'],'CANDIDATE_VERIFIED')
            self.assertEqual(run_gate(root,evaluator(base))[1]['terminal_state'],'REPAIR_REQUIRED')

    def test_fg_a09_external_dependency_never_passes(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root=baseline(base); patch=make_patch(root,base,{'calc.py':correct_calc('# EXTERNAL_ME\n')}); _, candidate=run_candidate(root,patch)
            self.assertEqual(candidate['terminal_state'],'BLOCKED_EXTERNAL')

    def test_fg_a10_locked_regression_recurrence_blocks_candidate(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root,_=make_f4_failure_project(base,accepted_feature_values=('off',)); patch=patch_file(base,root,'feature.txt','on\n')
            _, result=run_candidate(root,patch); self.assertEqual(result['terminal_state'],'REPAIR_REQUIRED'); self.assertEqual(result['reason_code'],'LOCKED_REGRESSION_FAILED')

    def test_fg_a11_deleted_locked_failure_cannot_disappear(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root,_=make_f4_failure_project(base,accepted_feature_values=('off',)); shutil.rmtree(root/'.forge/failures/FAIL-F6L')
            patch=patch_file(base,root,'feature.txt','on\n'); _, result=run_candidate(root,patch)
            self.assertNotEqual(result['terminal_state'],'CANDIDATE_VERIFIED', result)

    def test_fg_a12_locked_failure_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root,_=make_f4_failure_project(base,accepted_feature_values=('off','on'))
            stored=root/'.forge/failures/FAIL-F6L/evaluators/PERMANENT_EVALUATION.py'; stored.write_text('raise SystemExit(0)\n')
            patch=patch_file(base,root,'feature.txt','on\n'); _, result=run_candidate(root,patch)
            self.assertEqual(result['terminal_state'],'REPAIR_REQUIRED')

    def test_fg_a13_required_check_failure_has_no_final_path(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root=baseline(base); patch=make_patch(root,base,{'calc.py':BAD}); _, result=run_candidate(root,patch)
            self.assertEqual(result['terminal_state'],'REPAIR_REQUIRED'); self.assertNotEqual(run_gate(root,evaluator(base))[0].returncode,0)

    def test_fg_a14_gate_refuses_missing_non_candidate(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root=baseline(base); self.assertNotEqual(run_gate(root,evaluator(base))[0].returncode,0)

    def test_fg_a15_final_evidence_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            base=Path(tmp); root=baseline(base); patch=make_patch(root,base,{'calc.py':correct_calc()}); run_candidate(root,patch); ev=evaluator(base)
            first,_=run_gate(root,ev); final_path=root/'.forge/runs/U-0001/attempt-0001/FINAL_EVALUATION.json'; before=final_path.read_bytes(); second,_=run_gate(root,ev)
            self.assertEqual(first.returncode,0); self.assertNotEqual(second.returncode,0); self.assertEqual(final_path.read_bytes(),before)

    def test_fg_a16_no_builder_merge_deploy_autonomy_cli(self):
        with tempfile.TemporaryDirectory(prefix='forge-fg-') as tmp:
            root=Path(tmp); help_result=run_forge(root,'--help'); self.assertEqual(help_result.returncode,0)
            text=help_result.stdout.lower()
            for forbidden in ('build','builder','merge','deploy','swarm','autonomous'):
                self.assertNotIn(forbidden,text)


if __name__ == '__main__':
    unittest.main()
