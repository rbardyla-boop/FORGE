from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.test_f3 import create_contract, init_project, make_repo, required, run_forge
from forge_core.doctor import ENVIRONMENT_READY, FORGE_CANNOT_VERIFY, PROJECT_BASELINE_FAILURE


def phased(check_id: str, argv: list[str], preflight: bool) -> dict:
    return {'id': check_id, 'required': True, 'preflight': preflight, 'argv': argv}


class ForgeF3Repair002Tests(unittest.TestCase):
    def test_doctor_runs_preflight_and_defers_acceptance(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f3-r2-') as tmp:
            root = make_repo(Path(tmp), {
                'preflight.py': "print('preflight-ok')\n",
                'accept.py': 'import sys\nsys.exit(23)\n',
            })
            init_project(root)
            create_contract(root, [
                phased('CHK_PREFLIGHT', ['python3', 'preflight.py'], True),
                phased('CHK_ACCEPT', ['python3', 'accept.py'], False),
            ])
            result = run_forge(root, 'doctor', 'U-0001')
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['classification'], ENVIRONMENT_READY)
            self.assertEqual([c['id'] for c in report['checks']], ['CHK_PREFLIGHT'])
            self.assertEqual(report['acceptance_checks_deferred'], ['CHK_ACCEPT'])

    def test_red_preflight_still_blocks_baseline(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f3-r2-') as tmp:
            root = make_repo(Path(tmp), {'preflight.py': 'import sys\nsys.exit(9)\n'})
            init_project(root)
            create_contract(root, [phased('CHK_PREFLIGHT', ['python3', 'preflight.py'], True)])
            result = run_forge(root, 'doctor', 'U-0001')
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report['classification'], PROJECT_BASELINE_FAILURE)

    def test_no_preflight_required_check_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f3-r2-') as tmp:
            root = make_repo(Path(tmp), {'accept.py': "print('future')\n"})
            init_project(root)
            create_contract(root, [phased('CHK_ACCEPT', ['python3', 'accept.py'], False)])
            result = run_forge(root, 'doctor', 'U-0001')
            self.assertEqual(result.returncode, 4)
            report = json.loads(result.stdout)
            self.assertEqual(report['classification'], FORGE_CANNOT_VERIFY)
            self.assertEqual(report['reason_code'], 'NO_PREFLIGHT_REQUIRED_CHECK')
            self.assertEqual(report['acceptance_checks_deferred'], ['CHK_ACCEPT'])


if __name__ == '__main__':
    unittest.main()
