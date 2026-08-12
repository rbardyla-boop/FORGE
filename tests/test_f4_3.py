from tests.f4_support import *


class ForgeF4Tests3(unittest.TestCase):
    def test_checker_restage_of_same_patched_path_is_detected_by_exact_diff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "restage.py"])])
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "VERIFICATION_FAILURE")
            self.assertEqual(
                report["required_checks"][0]["reason_code"],
                "CHECK_MUTATED_PATCHED_STATE",
            )

    def test_patch_introducing_external_symlink_is_rejected_before_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            external = base / "external-target.txt"
            external.write_text("external-original\n")
            root = basic_repo(base)
            (root / "internal.txt").write_text("internal\n")
            (root / "link").symlink_to("internal.txt")
            (root / "symlink_check.py").write_text(
                "from pathlib import Path\n"
                "import os\n"
                "if os.readlink('link').startswith('/'):\n"
                "    Path('link').write_text('escaped-write\\n')\n"
            )
            git(root, "add", "internal.txt", "link", "symlink_check.py")
            committed = git(root, "commit", "-m", "add safe symlink fixture")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            init_project(root)
            create_contract(
                root,
                [required(["python3", "symlink_check.py"])],
                allowed=["link"],
            )

            link = root / "link"
            link.unlink()
            link.symlink_to(external)
            patch_bytes = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "diff",
                    "--binary",
                    "--full-index",
                    "--no-ext-diff",
                    "--no-renames",
                    "--",
                    "link",
                ],
                capture_output=True,
                check=True,
            ).stdout
            link.unlink()
            link.symlink_to("internal.txt")
            self.assertEqual(
                git(root, "status", "--porcelain=v1", "--untracked-files=no").stdout, ""
            )
            patch = base / "symlink.patch"
            patch.write_bytes(patch_bytes)

            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "TRACKED_SYMLINK_ESCAPE")
            self.assertEqual(report["required_checks"], [])
            self.assertEqual(external.read_text(), "external-original\n")

    def test_single_star_scope_does_not_cross_directory_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            nested = root / "root/sub/x.txt"
            nested.parent.mkdir(parents=True)
            nested.write_text("before\n")
            git(root, "add", "root/sub/x.txt")
            committed = git(root, "commit", "-m", "add nested fixture")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            init_project(root)
            create_contract(
                root,
                [required(["python3", "check.py"])],
                allowed=["root/*.txt"],
            )
            patch = patch_file(base, root, "root/sub/x.txt", "after\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["reason_code"], "SCOPE_VIOLATION")
            self.assertEqual(
                report["scope_violations"],
                [{"path": "root/sub/x.txt", "reason": "OUTSIDE_ALLOWED_PATHS"}],
            )

    def test_contract_change_during_attempt_forces_repair_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "mutate_contract.py"])])
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(
                root,
                "unit",
                "run",
                "U-0001",
                "--patch",
                str(patch),
                env_extra={"F4_OPERATOR_ROOT": str(root)},
            )
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "CONTRACT_CHANGED_DURING_ATTEMPT")
            self.assertFalse(report["contract_postcondition_unchanged"])
            self.assertEqual(report["completion_authority"], "harness")

    def test_empty_patch_is_repair_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = base / "empty.patch"
            patch.write_bytes(b"")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3)
            report = json.loads(result.stdout)
            self.assertEqual(report["reason_code"], "EMPTY_PATCH")

    def test_second_attempt_is_refused_without_overwriting_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "feature.txt", "on\n")
            first = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(first.returncode, 0, first.stderr)
            evidence_path = attempt_dir(root) / "EVIDENCE.json"
            before = evidence_path.read_bytes()
            second = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(second.returncode, 2)
            self.assertIn("attempt already exists", second.stderr)
            self.assertEqual(evidence_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
