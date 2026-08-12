from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.f5_support import git, run_candidate, run_forge
from tests.f6_support import (
    close_failure_fixture,
    make_candidate,
    make_f4_failure_project,
    patch_file,
    register_failure_fixture,
    replay_failure_fixture,
)

REGISTERED = 'refs/forge/failures/registered/FAIL-F6A'
LOCKED = 'refs/forge/failures/locked/FAIL-F6A'
LOCKED_L = 'refs/forge/failures/locked/FAIL-F6L'


class FoundationRepair002Tests(unittest.TestCase):
    def test_registration_creates_registered_anchor(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base)
            self.assertEqual(registered.returncode, 0, registered.stderr)
            probe = git(root, 'rev-parse', '--verify', REGISTERED)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            verified = run_forge(root, 'failure', 'verify', 'FAIL-F6A')
            self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_successful_close_creates_locked_anchor(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            self.assertEqual(register_failure_fixture(root, base)[0].returncode, 0)
            closed = close_failure_fixture(root)
            self.assertEqual(closed.returncode, 0, closed.stderr)
            probe = git(root, 'rev-parse', '--verify', LOCKED)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertEqual(run_forge(root, 'failure', 'verify', 'FAIL-F6A').returncode, 0)

    def test_failed_close_creates_no_locked_anchor(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            registered, _, _ = register_failure_fixture(root, base, fail_layer='PERMANENT_EVALUATION')
            self.assertEqual(registered.returncode, 0, registered.stderr)
            closed = close_failure_fixture(root)
            self.assertEqual(closed.returncode, 3, closed.stderr)
            probe = git(root, 'rev-parse', '--verify', '--quiet', LOCKED, check=False)
            self.assertNotEqual(probe.returncode, 0)
            self.assertEqual(run_forge(root, 'failure', 'verify', 'FAIL-F6A').returncode, 0)

    def test_deleted_failure_directory_is_detected_from_registered_anchor(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            self.assertEqual(register_failure_fixture(root, base)[0].returncode, 0)
            shutil.rmtree(root / '.forge/failures/FAIL-F6A')
            verified = run_forge(root, 'failure', 'verify', 'FAIL-F6A')
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn('missing_records', verified.stderr)

    def test_deleted_registered_anchor_is_detected(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            self.assertEqual(register_failure_fixture(root, base)[0].returncode, 0)
            self.assertEqual(git(root, 'update-ref', '-d', REGISTERED).returncode, 0)
            verified = run_forge(root, 'failure', 'verify', 'FAIL-F6A')
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn('missing_anchors', verified.stderr)

    def test_deleted_locked_anchor_is_detected(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            self.assertEqual(register_failure_fixture(root, base)[0].returncode, 0)
            self.assertEqual(close_failure_fixture(root).returncode, 0)
            self.assertEqual(git(root, 'update-ref', '-d', LOCKED).returncode, 0)
            verified = run_forge(root, 'failure', 'verify', 'FAIL-F6A')
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn('missing locked anchor', verified.stderr)

    def test_moved_registered_anchor_is_detected(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            self.assertEqual(register_failure_fixture(root, base)[0].returncode, 0)
            head = git(root, 'rev-parse', 'HEAD').stdout.strip()
            self.assertEqual(git(root, 'update-ref', REGISTERED, head).returncode, 0)
            verified = run_forge(root, 'failure', 'verify', 'FAIL-F6A')
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn('does not resolve to a blob', verified.stderr)

    def test_locked_record_downgrade_with_locked_anchor_is_detected(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            self.assertEqual(register_failure_fixture(root, base)[0].returncode, 0)
            self.assertEqual(close_failure_fixture(root).returncode, 0)
            path = root / '.forge/failures/FAIL-F6A/record.json'
            record = json.loads(path.read_text())
            record['status'] = 'OPEN'; record['locked_by_closure'] = None
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            verified = run_forge(root, 'failure', 'verify', 'FAIL-F6A')
            self.assertNotEqual(verified.returncode, 0)
            self.assertIn('locked anchor exists for OPEN failure', verified.stderr)

    def test_normal_locked_replay_remains_green(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root = make_candidate(base)
            self.assertEqual(register_failure_fixture(root, base)[0].returncode, 0)
            self.assertEqual(close_failure_fixture(root).returncode, 0)
            replay = replay_failure_fixture(root)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertTrue(json.loads(replay.stdout)['regression_passed'])

    def test_fg_a11_deleted_locked_obligation_blocks_f4_preflight(self):
        with tempfile.TemporaryDirectory(prefix='forge-fa2-') as tmp:
            base = Path(tmp); root, _ = make_f4_failure_project(base, accepted_feature_values=('off',))
            self.assertEqual(git(root, 'rev-parse', '--verify', LOCKED_L).returncode, 0)
            shutil.rmtree(root / '.forge/failures/FAIL-F6L')
            patch = patch_file(base, root, 'feature.txt', 'on\n')
            proc, result = run_candidate(root, patch)
            self.assertNotEqual(proc.returncode, 0)
            if result is not None:
                self.assertNotEqual(result['terminal_state'], 'CANDIDATE_VERIFIED')
            self.assertIn('failure-anchor integrity preflight failed', proc.stderr)


if __name__ == '__main__':
    unittest.main()
