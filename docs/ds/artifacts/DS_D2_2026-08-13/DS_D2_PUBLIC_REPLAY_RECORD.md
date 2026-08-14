# DS-D2 — Post-deployment public replay

Date: **2026-08-13**

Terminal ruling: **DS_D2_PUBLIC_REPLAY_PASS**

## Bound release

- Candidate: `bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc`
- Release boundary: **Option B** — DS-00 excluded.
- Authorized artifact: 302 hashed entries; `_UPLOAD_MANIFEST.json` is served
  separately and is included in the frozen manifest check.
- Artifact SHA-256: `6221cb59c694ce0fc9261ba1f38975fbb8dcdd282bceb78bce967d48ae74c794`
- Upload manifest SHA-256: `d97efc86b8ba5992dd95bd6b3b990c42b58008386ccdbcaea7b7e23c31528c02`

## Production binding

- Worker: `wild-hat-6257`
- Custom domain: `https://clovelearn.io`
- Worker origin: `https://wild-hat-6257.rbardyla.workers.dev`
- Version: `53c7c021-96a5-495b-b622-16bd1b368967`
- Deployment: `662f9820-b551-449e-9647-8f1961052436`
- Traffic: **100%**
- Production writes during replay: **none**

## Public replay results

- Production metadata before/after replay: byte-identical.
- Production deployment list before/after replay: byte-identical.
- Full origin asset replay: **300/300 served non-redirect paths exact**.
- `/index.html`: **302 → `/deck.html`**, exact authorized redirect.
- `_headers` and `_redirects`: **404**, not public assets.
- Representative origin paths (`/`, `/research/`, CSS, JS, signals, arcade,
  robots, and manifest): exact status and SHA-256 matches.
- Custom-domain exact assets: match the Worker origin.
- Custom-domain HTML: matches origin after only the documented Cloudflare
  challenge, hidden-link, and font transformations are normalized.
- Custom-domain `robots.txt`: matches origin after the documented managed
  content block is normalized.
- DS-00 public paths: **14/14 returned 404 with empty bodies**.
- Browser navigation: root, Research, reload, repeat navigation, and a fresh
  context all passed.
- Research surface: one question input and one Investigate action present.
- Privacy/safety replay: zero external requests, zero external POSTs, no
  question submission, no forbidden DS markers, no browser errors.
- Isolation replay: same-context sentinel survived reload; fresh context saw
  no sentinel; cross-context leakage **false**.

## DS-X0 and claim boundary

DS-X0 private runtime task execution is **not claimed through the public
boundary** because DS-00 is deliberately excluded from the release. The public
replay instead verifies non-exposure, public navigation, isolation, privacy,
safety, and corruption-adjacent boundary properties. Human usability remains
`NOT_CLAIMED`.

## Verification-grinder record

- **Claim:** the live public system reproduces the authorized DS-D1 release
  properties through the real public boundary without mutating production.
- **Check:** immutable artifact/hash verification; full Worker-origin replay;
  custom-domain replay with only pre-disclosed edge normalization; public
  browser navigation/isolation/privacy checks; DS-00 non-exposure checks; and
  before/after production metadata comparison.
- **Criteria:** exact artifact identity; active version/deployment identity;
  unchanged production metadata; exact origin assets; expected redirect;
  custom-domain normalized equality; DS-00 404; clean browser replay; and no
  unexpected state or network leakage.
- **Verdict:** **PASS — `DS_D2_PUBLIC_REPLAY_PASS`**.
- **Credit:** proves that the deployed public boundary serves the authorized
  release and preserves its tested public safety/isolation properties.
- **Gap:** human usability is not claimed; DS-X0 private runtime execution is
  outside this public release because DS-00 is excluded.
- **Stop/continue:** DS engineering-release chain is terminal for this
  candidate. Do not mutate production or add another DS gate unless field
  evidence or a concrete defect justifies a new candidate.
- **Maturity:** **M3 — production-deployed and publicly replay-verified**.

Raw evidence was sealed before interpretation under:
`/tmp/clove-ds-d2-20260813-hGW3pH/RAW_EVIDENCE_SHA256SUMS.txt`

