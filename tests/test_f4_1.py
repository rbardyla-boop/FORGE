from tests.f4_support import *


class ForgeF4Tests1(unittest.TestCase):
    def test_green_patch_passes_and_evidence_binds_exact_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            original = (root / "feature.txt").read_bytes()
            init_project(root)
            frozen = create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "feature.txt", "on\n")
            patch_bytes = patch.read_bytes()
            baseline = git(root, "rev-parse", "HEAD").stdout.strip()
            worktrees_before = git(root, "worktree", "list", "--porcelain").stdout

            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "PASS")
            self.assertEqual(report["completion_authority"], "harness")
            self.assertTrue(report["contract_postcondition_unchanged"])
            self.assertEqual(report["contract_digest"], frozen["contract_digest"])
            self.assertEqual(report["baseline_commit"], baseline)
            self.assertEqual(
                report["input_patch_sha256"],
                "sha256:" + hashlib.sha256(patch_bytes).hexdigest(),
            )
            self.assertEqual(report["changed_paths"], ["feature.txt"])
            evidence = json.loads((attempt_dir(root) / "EVIDENCE.json").read_text())
            applied = (attempt_dir(root) / "APPLIED.diff").read_bytes()
            self.assertEqual(evidence, report)
            self.assertEqual(
                evidence["applied_diff_sha256"],
                "sha256:" + hashlib.sha256(applied).hexdigest(),
            )
            self.assertEqual(evidence["applied_diff_bytes"], len(applied))
            self.assertEqual((root / "feature.txt").read_bytes(), original)
            self.assertEqual(
                git(root, "worktree", "list", "--porcelain").stdout,
                worktrees_before,
            )

    def test_draft_contract_blocks_before_attempt_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])], freeze=False)
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 2)
            self.assertIn("DRAFT", result.stderr)
            self.assertFalse(attempt_dir(root).exists())

    def test_tampered_contract_blocks_before_attempt_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            contract = root / ".forge/contracts/U-0001.json"
            record = json.loads(contract.read_text())
            record["authority"]["objective"] = "tampered"
            contract.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 2)
            self.assertIn("digest mismatch", result.stderr)
            self.assertFalse(attempt_dir(root).exists())

    def test_non_ready_doctor_baseline_blocks_before_attempt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            (root / "mode.txt").write_text("fail\n")
            git(root, "add", "mode.txt")
            git(root, "commit", "-m", "red baseline")
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = patch_file(base, root, "feature.txt", "on\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 2)
            self.assertIn("Doctor prerequisite not ready", result.stderr)
            self.assertFalse(attempt_dir(root).exists())

    def test_symlinked_patch_input_is_rejected_before_attempt_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            real_patch = patch_file(base, root, "feature.txt", "on\n", "real.patch")
            link = base / "linked.patch"
            link.symlink_to(real_patch)
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(link))
            self.assertEqual(result.returncode, 2)
            self.assertIn("patch file must not be a symlink", result.stderr)
            self.assertFalse(attempt_dir(root).exists())

    def test_malformed_patch_is_repair_required_with_no_applied_diff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="forge-f4-") as tmp:
            base = Path(tmp)
            root = basic_repo(base)
            init_project(root)
            create_contract(root, [required(["python3", "check.py"])])
            patch = base / "bad.patch"
            patch.write_text("not a patch\n")
            result = run_forge(root, "unit", "run", "U-0001", "--patch", str(patch))
            self.assertEqual(result.returncode, 3, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["terminal_state"], "REPAIR_REQUIRED")
            self.assertEqual(report["reason_code"], "PATCH_APPLY_CHECK_FAILED")
            self.assertIsNone(report["applied_diff_sha256"])
            self.assertFalse((attempt_dir(root) / "APPLIED.diff").exists())


if __name__ == "__main__":
    unittest.main()
