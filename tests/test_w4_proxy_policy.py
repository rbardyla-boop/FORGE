from __future__ import annotations

from pathlib import Path
import stat
import tempfile
import unittest

from forge_core.w4_proxy_policy import (
    FORBIDDEN_PROXY_ARGS,
    OFFICIAL_DEFAULT_UPSTREAM,
    PROXY_PORT,
    ForgeW4ProxyPolicyError,
    build_live_proxy_argv,
    inspect_proxy_executable,
    verify_live_proxy_manifest,
)


class ForgeW4ProxyPolicyTests(unittest.TestCase):
    def make_proxy(self, base: Path) -> Path:
        path = (base / "codex-responses-api-proxy").resolve()
        path.write_bytes(b"fixture official-proxy binary placeholder\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def test_b16_live_proxy_policy_freezes_official_default_openai_endpoint(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-proxy-") as tmp:
            path = self.make_proxy(Path(tmp))
            manifest = inspect_proxy_executable(path)
            argv = build_live_proxy_argv(path)
            self.assertEqual(manifest["expected_default_upstream"], "https://api.openai.com/v1/responses")
            self.assertEqual(OFFICIAL_DEFAULT_UPSTREAM, "https://api.openai.com/v1/responses")
            self.assertEqual(argv, [str(path), "--port", str(PROXY_PORT)])
            self.assertNotIn("--upstream-url", argv)

    def test_b17_live_proxy_policy_exposes_no_tls_disable_or_endpoint_override_surface(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-proxy-") as tmp:
            path = self.make_proxy(Path(tmp))
            argv = build_live_proxy_argv(path)
            rendered = " ".join(argv).lower()
            for forbidden in (
                "--upstream-url",
                "--dump-dir",
                "--http-shutdown",
                "--server-info",
                "insecure",
                "no-verify",
                "tls-skip",
                "http://api.openai.com",
            ):
                self.assertNotIn(forbidden, rendered)
            self.assertTrue(FORBIDDEN_PROXY_ARGS.isdisjoint(argv))

    def test_proxy_executable_requires_absolute_regular_non_symlink_executable(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-proxy-") as tmp:
            base = Path(tmp); path = self.make_proxy(base)
            link = (base / "proxy-link").resolve(strict=False)
            link.symlink_to(path)
            with self.assertRaisesRegex(ForgeW4ProxyPolicyError, "symlink"):
                inspect_proxy_executable(link)
            with self.assertRaisesRegex(ForgeW4ProxyPolicyError, "absolute"):
                inspect_proxy_executable(Path("relative-proxy"))

    def test_proxy_manifest_detects_binary_replacement(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-proxy-") as tmp:
            path = self.make_proxy(Path(tmp))
            manifest = inspect_proxy_executable(path)
            path.write_bytes(path.read_bytes() + b"replacement\n")
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            with self.assertRaisesRegex(ForgeW4ProxyPolicyError, "no longer matches"):
                verify_live_proxy_manifest(path, manifest)


if __name__ == "__main__":
    unittest.main()
