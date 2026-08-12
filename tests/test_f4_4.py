from tests.f4_support import *


class ForgeF4Tests4(unittest.TestCase):
    def test_patch_text_claiming_pass_has_no_completion_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "mode.txt", "PASS\n")
            self.assertIn(b"PASS", patch.read_bytes())
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["completion_authority"], "harness")

    def test_advisory_check_is_skipped_and_cannot_block_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(
                root,
                [
                    required(["python3", "check.py"]),
                    advisory(["python3", "advisory.py"]),
                ],
            )
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "PASS")
            self.assertEqual(report["advisory_checks_skipped"], ["CHK_ADV"])
            self.assertEqual([r["id"] for r in report["required_checks"]], ["CHK_001"])

    def test_symlinked_runs_directory_is_rejected_before_attempt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            outside = base / "outside-runs"
            outside.mkdir()
            (root / ".forge/runs").symlink_to(outside, target_is_directory=True)
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 2)
            self.assertIn("runs directory is unsafe", result.stderr)
            self.assertEqual(list(outside.iterdir()), [])

    def test_build_remains_unauthorized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            result = run_forge(root, "build")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
