from tests.f4_support import *


class ForgeF4Tests2(unittest.TestCase):
    def test_out_of_scope_patch_is_repair_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])], allowed=["feature.txt"])
            patch = patch_file(base, root, "outside.txt", "changed\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["reason_code"], "SCOPE_VIOLATION")
            self.assertEqual(report["scope_violations"][0]["reason"], "OUTSIDE_ALLOWED_PATHS")

    def test_forbidden_path_patch_is_repair_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(
                root,
                [required(["python3", "check.py"])],
                allowed=["*.txt"],
                forbidden=["secret.txt"],
            )
            patch = patch_file(base, root, "secret.txt", "changed\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["scope_violations"][0]["reason"], "MATCHES_FORBIDDEN_PATH")

    def test_required_check_failure_is_repair_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "mode.txt", "fail\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "REQUIRED_CHECK_FAILED")
            self.assertEqual(report["required_checks"][0]["exit_code"], 9)

    def test_explicit_external_blocker_is_terminal_blocked_external(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "mode.txt", "external\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 5)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "BLOCKED_EXTERNAL")
            self.assertEqual(report["reason_code"], "EXTERNAL_DEPENDENCY_REPORTED")

    def test_timeout_after_patch_is_repair_required_verification_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "mode.txt", "slow\n")
            report, code = run_unit_attempt(root, "U-0001", patch, timeout_seconds=0.1)
            self.assertEqual(code, 3)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "VERIFICATION_FAILURE")
            self.assertEqual(report["required_checks"][0]["reason_code"], "CHECK_TIMEOUT")

    def test_check_mutating_state_beyond_patch_is_repair_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            original_guard = (root / "guard.txt").read_bytes()
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "mode.txt", "mutate\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["reason_code"], "VERIFICATION_FAILURE")
            self.assertEqual(
                report["required_checks"][0]["reason_code"], "CHECK_MUTATED_PATCHED_STATE"
            )
            self.assertEqual((root / "guard.txt").read_bytes(), original_guard)


if __name__ == "__main__":
    unittest.main()
