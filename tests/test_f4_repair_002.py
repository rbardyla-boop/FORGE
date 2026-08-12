from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.f4_support import basic_repo, init_project, patch_file, run_forge


def authority() -> dict:
    return {
        'objective': 'Add safe_divide without breaking divide',
        'deliverables': ['calc.py'],
        'success_criteria': [{
            'id': 'SC_001',
            'statement': 'safe_divide behavior passes final acceptance',
            'check_ids': ['CHK_ACCEPT'],
        }],
        'scope': {'allowed_paths': ['calc.py'], 'forbidden_paths': ['acceptance.py']},
        'checks': [
            {'id': 'CHK_PREFLIGHT', 'required': True, 'preflight': True, 'argv': ['python3', '-m', 'py_compile', 'calc.py', 'acceptance.py']},
            {'id': 'CHK_ACCEPT', 'required': True, 'preflight': False, 'argv': ['python3', 'acceptance.py']},
        ],
        'terminal_states': ['PASS', 'REPAIR_REQUIRED', 'BLOCKED_EXTERNAL'],
        'non_goals': ['No AI builder'],
        'forbidden_actions': ['Do not modify acceptance.py'],
    }


class ForgeF4Repair002Tests(unittest.TestCase):
    def test_known_good_new_behavior_patch_is_admitted_and_runs_all_required_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f4-r2-') as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            (root / 'calc.py').write_text('def divide(a, b):\n    return a / b\n')
            (root / 'acceptance.py').write_text(
                'from calc import divide, safe_divide\n'
                'assert divide(8, 2) == 4\n'
                'assert safe_divide(8, 2) == 4\n'
                'assert safe_divide(1, 0) is None\n'
            )
            import subprocess
            subprocess.run(['git', '-C', str(root), 'add', 'calc.py', 'acceptance.py'], check=True)
            subprocess.run(['git', '-C', str(root), 'commit', '-m', 'safe-divide baseline'], check=True, capture_output=True)
            init_project(root)
            source = root / 'authority-r2.json'
            source.write_text(json.dumps(authority(), indent=2, sort_keys=True) + '\n')
            self.assertEqual(run_forge(root, 'contract', 'create', 'U-0001', '--file', str(source)).returncode, 0)
            self.assertEqual(run_forge(root, 'contract', 'freeze', 'U-0001').returncode, 0)
            doctor = run_forge(root, 'doctor', 'U-0001')
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            d = json.loads(doctor.stdout)
            self.assertEqual(d['acceptance_checks_deferred'], ['CHK_ACCEPT'])
            patch = patch_file(
                base,
                root,
                'calc.py',
                'def divide(a, b):\n    return a / b\n\ndef safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n',
                'good.patch',
            )
            result = run_forge(root, 'unit', 'run', 'U-0001', '--patch', str(patch))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['terminal_state'], 'CANDIDATE_VERIFIED')
            self.assertEqual([c['id'] for c in report['required_checks']], ['CHK_PREFLIGHT', 'CHK_ACCEPT'])
            self.assertTrue(all(c['exit_code'] == 0 for c in report['required_checks']))


if __name__ == '__main__':
    unittest.main()
