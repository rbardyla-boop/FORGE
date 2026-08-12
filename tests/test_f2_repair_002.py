from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.test_f2 import contract_path, init_project, run_forge, valid_authority, write_authority


class ForgeF2Repair002Tests(unittest.TestCase):
    def test_explicit_acceptance_phase_is_persisted_and_digest_bound(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f2-r2-') as tmp:
            root = Path(tmp) / 'demo'; root.mkdir(); init_project(root)
            auth = valid_authority()
            auth['checks'][0]['preflight'] = False
            source = write_authority(root, auth)
            self.assertEqual(run_forge(root, 'contract', 'create', 'U-0001', '--file', str(source)).returncode, 0)
            frozen = run_forge(root, 'contract', 'freeze', 'U-0001')
            self.assertEqual(frozen.returncode, 0, frozen.stderr)
            record = json.loads(contract_path(root).read_text())
            self.assertFalse(record['authority']['checks'][0]['preflight'])
            record['authority']['checks'][0]['preflight'] = True
            contract_path(root).write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            verify = run_forge(root, 'contract', 'verify', 'U-0001')
            self.assertEqual(verify.returncode, 2)
            self.assertIn('digest mismatch', verify.stderr)

    def test_advisory_check_cannot_claim_preflight(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f2-r2-') as tmp:
            root = Path(tmp) / 'demo'; root.mkdir(); init_project(root)
            auth = valid_authority()
            auth['checks'][0].update(required=False, preflight=True)
            source = write_authority(root, auth)
            result = run_forge(root, 'contract', 'create', 'U-0001', '--file', str(source))
            self.assertEqual(result.returncode, 2)
            self.assertIn('advisory checks may not claim preflight authority', result.stderr)

    def test_legacy_frozen_contract_without_preflight_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f2-r2-') as tmp:
            root = Path(tmp) / 'demo'; root.mkdir(); init_project(root)
            source = write_authority(root, valid_authority())
            self.assertEqual(run_forge(root, 'contract', 'create', 'U-0001', '--file', str(source)).returncode, 0)
            path = contract_path(root)
            record = json.loads(path.read_text())
            record['authority']['checks'][0].pop('preflight', None)
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            frozen = run_forge(root, 'contract', 'freeze', 'U-0001')
            self.assertEqual(frozen.returncode, 0, frozen.stderr)
            stored = json.loads(path.read_text())
            self.assertNotIn('preflight', stored['authority']['checks'][0])
            self.assertEqual(run_forge(root, 'contract', 'verify', 'U-0001').returncode, 0)
            self.assertEqual(run_forge(root, 'contract', 'ready', 'U-0001').returncode, 0)

    def test_legacy_advisory_check_remains_valid_and_normalizes_non_preflight(self) -> None:
        with tempfile.TemporaryDirectory(prefix='forge-f2-r2-') as tmp:
            root = Path(tmp) / 'demo'; root.mkdir(); init_project(root)
            auth = valid_authority()
            auth['checks'].append({'id': 'CHK_ADV', 'required': False, 'argv': ['python3', '-c', 'print(1)']})
            source = write_authority(root, auth)
            result = run_forge(root, 'contract', 'create', 'U-0001', '--file', str(source))
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(contract_path(root).read_text())
            advisory = next(c for c in record['authority']['checks'] if c['id'] == 'CHK_ADV')
            self.assertFalse(advisory['preflight'])


if __name__ == '__main__':
    unittest.main()
