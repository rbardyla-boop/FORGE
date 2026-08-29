from __future__ import annotations

from pathlib import Path
import tempfile
import tomllib
import unittest

from forge_core.w4_codex_config import (
    ALLOWED_BASE_URL,
    CAPABILITY_ENV,
    PROVIDER_ID,
    ForgeW4CodexConfigError,
    create_codex_home,
    render_config,
    validate_config_bytes,
)


class ForgeW4CodexConfigTests(unittest.TestCase):
    def test_b24_generated_codex_home_has_no_auth_json(self):
        with tempfile.TemporaryDirectory(prefix="forge-w4-config-") as tmp:
            report = create_codex_home(Path(tmp), model="fixture-model")
            codex_home = Path(report["codex_home"])
            self.assertTrue((codex_home / "config.toml").is_file())
            self.assertFalse((codex_home / "auth.json").exists())
            self.assertFalse(report["auth_json_present"])

    def test_b25_config_contains_only_frozen_forge_broker_provider(self):
        data = render_config(model="fixture-model")
        parsed = validate_config_bytes(data, model="fixture-model")
        self.assertEqual(parsed["model_provider"], PROVIDER_ID)
        self.assertEqual(set(parsed["model_providers"]), {PROVIDER_ID})
        provider = parsed["model_providers"][PROVIDER_ID]
        self.assertEqual(provider["base_url"], ALLOWED_BASE_URL)
        self.assertEqual(provider["env_key"], CAPABILITY_ENV)
        self.assertEqual(provider["wire_api"], "responses")
        self.assertFalse(provider["requires_openai_auth"])
        self.assertNotIn("OPENAI_API_KEY", data.decode())
        self.assertNotIn("CODEX_API_KEY", data.decode())

    def test_b26_repository_or_caller_cannot_change_broker_base_url(self):
        for bad in (
            "http://attacker.invalid/v1",
            "https://api.openai.com/v1",
            "http://forge-broker:8080/v1?x=1",
            "http://user:pass@forge-broker:8080/v1",
            "http://forge-broker:8081/v1",
        ):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ForgeW4CodexConfigError, "base URL"):
                    render_config(model="fixture-model", base_url=bad)

    def test_b26_config_validator_rejects_added_project_controlled_keys(self):
        original = render_config(model="fixture-model")
        modified = original + b'\n[mcp_servers.attacker]\ncommand = "sh"\n'
        with self.assertRaisesRegex(ForgeW4CodexConfigError, "unauthorized keys"):
            validate_config_bytes(modified, model="fixture-model")

    def test_b27_arbitrary_config_override_surface_is_not_generated(self):
        text = render_config(model="fixture-model").decode()
        for forbidden in (
            "experimental_bearer_token",
            "http_headers",
            "env_http_headers",
            "query_params",
            "mcp_servers",
            "plugins",
            "profile =",
            "profiles.",
            "auth.json",
        ):
            self.assertNotIn(forbidden, text)
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["approval_policy"], "never")
        self.assertEqual(parsed["sandbox_mode"], "workspace-write")

    def test_untrusted_model_syntax_is_rejected(self):
        for model in ("", "../../secret", 'bad"\n[mcp_servers.x]', " model", "x" * 200):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ForgeW4CodexConfigError, "model identifier"):
                    render_config(model=model)


if __name__ == "__main__":
    unittest.main()
