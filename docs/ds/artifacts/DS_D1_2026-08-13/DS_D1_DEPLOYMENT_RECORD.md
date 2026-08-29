# DS-D1 — Production Deployment + Terminal Verification

Date: **2026-08-13**

Terminal ruling: **DS_D1_DEPLOYMENT_PASS**

## Frozen release

- Source candidate: `bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc`
- Release boundary: **Option B** — DS-00 excluded.
- Public artifact: 302 files plus `_UPLOAD_MANIFEST.json`.
- Artifact SHA-256: `6221cb59c694ce0fc9261ba1f38975fbb8dcdd282bceb78bce967d48ae74c794`
- Upload manifest SHA-256: `d97efc86b8ba5992dd95bd6b3b990c42b58008386ccdbcaea7b7e23c31528c02`

## Deployment receipt

- Target: Cloudflare Worker `wild-hat-6257`, custom domain `clovelearn.io`.
- Deployment command used an isolated config-free directory with the exact
  asset tree, `--keep-vars`, `--strict`, and no routes/domains/bindings flags.
- Previous active version / rollback predecessor:
  `e4770db3-8e6d-4ea3-a365-7a485b8830c1`
- Previous deployment: `46de7bfe-4351-45f9-8dd0-ca5799baab17`
- New active version: `53c7c021-96a5-495b-b622-16bd1b368967`
- New deployment: `662f9820-b551-449e-9647-8f1961052436`
- New version reached 100% traffic.
- Version view reported `bindings: []`, compatibility date `2026-08-13`,
  and only the authorized `/index.html → /deck.html` redirect.

## Production verification

Exact bytes from the Worker origin (`wild-hat-6257.rbardyla.workers.dev`):

| Surface | Status | SHA-256 |
|---|---:|---|
| `/` | 200 | `dbd4909507f349c54ad637d498031227fadac0f09d08657f401d58feb3d16c16` |
| `/research/` | 200 | `2a507cf1d64cde66105a484011363e4f62e7c321b79a502dfa2c822ae48e77ec` |
| `/_UPLOAD_MANIFEST.json` | 200 | `d97efc86b8ba5992dd95bd6b3b990c42b58008386ccdbcaea7b7e23c31528c02` |
| `/research/research.css` | 200 | `407b584209954fb2ef9a52cac3a34afe312a997e2f09a53f701b7dd219e15e01` |
| `/arcade/city/` | 200 | `74d2053d79b0db1d041e7dac4e34dbd6f7e8e2874f2bcd70fb10c6a9b5614f2b` |
| `/robots.txt` | 200 | `52a672b0ca8e3704f016f01003882c6f0f2189179fc0f1f3ebdc887d43273046` |
| `/digital-stewardship-00.html` | 404 | empty body |

The custom domain served the same authorized payloads after the documented
Cloudflare edge transformations: managed robots content, font-face
replacement, a hidden challenge link, and challenge JavaScript. These were
normalized out for comparison and were unchanged from the pre-deploy snapshot.
Custom-domain security headers were also unchanged from pre-deploy. The
Worker-origin headers match the frozen `_headers` artifact (`DENY`,
`strict-origin-when-cross-origin`, and the frozen Permissions-Policy).

`GET /index.html` returned the expected `302` to `/deck.html`. The custom
domain remained live, proving the custom-domain route was not detached.

## Regression and rollback

- Targeted release-boundary regression: **17/17 PASS**.
- Rollback predecessor was captured and remained available.
- Rollback was not executed because all hard gates passed.
- No repair, source edit, binding edit, secret edit, or route edit occurred
  during DS-D1.

## Verification-grinder record

- Claim: the publicly served release is the authorized 302-file artifact.
- Check: immutable rebuild/hash → production snapshot → asset-only deploy →
  origin byte verification → custom-domain normalized verification → config,
  header, route, and regression checks.
- Criteria: exact artifact identity; 100% deployment; required statuses; DS-00
  404; no bindings; headers/config unchanged; targeted tests pass.
- Verdict: **PASS — DS_D1_DEPLOYMENT_PASS**.
- Credit: proves production deployment and served-artifact identity under the
  disclosed Cloudflare edge transformations.
- Gap: human usability remains `NOT_CLAIMED`; the planned DS-D2 public replay
  may now use the live endpoint.
- Stop/continue: stop deployment work. Continue only with DS-D2 or a separately
  authorized repair; do not mutate this release during replay.
- Maturity: **M3 — production-deployed and terminally smoke-verified**.
