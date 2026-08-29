import { createRequire } from 'node:module';

// Reuse the already-installed Clove test dependency without changing either
// checkout or installing anything during a production replay.
const require = createRequire(import.meta.url);
const { firefox } = require('/home/thebackhand/Downloads/clovelearn_v3_final_deploy/node_modules/playwright');

const BASE = 'https://clovelearn.io';
const DS_PATHS = [
  'digital-stewardship-00.html', 'digital-stewardship-00.js',
  'digital-stewardship-01.html', 'digital-stewardship-01.js',
  'digital-stewardship-02.html', 'digital-stewardship-02.js',
  'digital-stewardship-03.html', 'digital-stewardship-03.js',
  'digital-stewardship-04.html', 'digital-stewardship-04.js',
  'digital-stewardship-05.html', 'digital-stewardship-05.js',
  'digital-stewardship-06.html', 'digital-stewardship-06.js',
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function visit(page, url) {
  const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await sleep(300);
  return { status: response?.status() ?? null, url: page.url(), title: await page.title() };
}

async function main() {
  const browser = await firefox.launch({ headless: true });
  const result = {
    unit: 'DS-D2',
    base: BASE,
    browser: 'Firefox headless',
    public_ds_paths: {},
    navigation: {},
    isolation: {},
    privacy_safety: {},
    errors: [],
  };

  try {
    const requestLog = [];
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('pageerror', (error) => result.errors.push({ type: 'pageerror', message: error.message }));
    page.on('request', (request) => requestLog.push({ method: request.method(), url: request.url() }));

    const root = await visit(page, `${BASE}/`);
    const rootHtml = await page.content();
    const researchLinkCount = await page.locator('a[href="/research/"]').count();
    const rootBody = await page.locator('body').innerText();

    const research = await visit(page, `${BASE}/research/`);
    const researchHtml = await page.content();
    const researchInputCount = await page.locator('#question').count();
    const researchButtonCount = await page.locator('#investigate').count();
    const researchBody = await page.locator('body').innerText();
    const researchReload = await visit(page, `${BASE}/research/`);
    const rootRepeat = await visit(page, `${BASE}/`);

    const localStorageBefore = await page.evaluate(() => Object.keys(localStorage));
    await page.evaluate(() => localStorage.setItem('__d2_isolation_probe__', 'sentinel'));
    const sameContextValue = await page.evaluate(() => localStorage.getItem('__d2_isolation_probe__'));
    await page.reload({ waitUntil: 'domcontentloaded' });
    const sameContextAfterReload = await page.evaluate(() => localStorage.getItem('__d2_isolation_probe__'));
    await context.close();

    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    const secondContextRoot = await visit(page2, `${BASE}/`);
    const otherContextValue = await page2.evaluate(() => localStorage.getItem('__d2_isolation_probe__'));
    await context2.close();

    const requestContext = await browser.newContext();
    const requestResults = await Promise.all(DS_PATHS.map(async (path) => {
      const response = await requestContext.request.get(`${BASE}/${path}`);
      const body = await response.body();
      return { path, status: response.status(), body_bytes: body.length };
    }));
    await requestContext.close();

    const sameOrigin = new URL(BASE).origin;
    const externalRequests = requestLog.filter(({ url }) => new URL(url).origin !== sameOrigin);
    const externalPostRequests = externalRequests.filter(({ method }) => method !== 'GET' && method !== 'HEAD');
    const forbiddenRequestMarkers = requestLog.filter(({ url }) => /digital-stewardship|__d2_isolation_probe|sentinel/i.test(url));

    result.navigation = {
      root,
      root_research_link_count: researchLinkCount,
      root_contains_ds_runtime_marker: /digital-stewardship|recovery verified|recovery readiness/i.test(`${rootHtml}\n${rootBody}`),
      research,
      research_input_count: researchInputCount,
      research_investigate_button_count: researchButtonCount,
      research_contains_ds_runtime_marker: /digital-stewardship|recovery verified|recovery readiness/i.test(`${researchHtml}\n${researchBody}`),
      research_reload: researchReload,
      root_repeat: rootRepeat,
      second_context_root: secondContextRoot,
    };
    result.isolation = {
      local_storage_keys_before: localStorageBefore,
      same_context_value: sameContextValue,
      same_context_after_reload: sameContextAfterReload,
      other_context_value: otherContextValue,
      cross_context_leakage: otherContextValue !== null,
    };
    result.public_ds_paths = Object.fromEntries(requestResults.map((item) => [item.path, item]));
    result.privacy_safety = {
      request_count: requestLog.length,
      external_request_count: externalRequests.length,
      external_request_origins: [...new Set(externalRequests.map(({ url }) => new URL(url).origin))].sort(),
      external_post_requests: externalPostRequests,
      forbidden_request_markers: forbiddenRequestMarkers,
      question_text_submitted: false,
      unexpected_external_post: externalPostRequests.length > 0,
      forbidden_marker_request: forbiddenRequestMarkers.length > 0,
    };
  } finally {
    await browser.close();
  }

  const failures = [];
  if (result.errors.length) failures.push('browser_errors');
  if (result.navigation.root.status !== 200) failures.push('root_status');
  if (result.navigation.root_research_link_count < 1) failures.push('research_link_missing');
  if (result.navigation.research.status !== 200 || result.navigation.research_input_count !== 1 || result.navigation.research_investigate_button_count !== 1) failures.push('research_surface');
  if (result.navigation.root_contains_ds_runtime_marker || result.navigation.research_contains_ds_runtime_marker) failures.push('ds_marker_public');
  if (result.isolation.cross_context_leakage) failures.push('cross_context_leakage');
  if (result.privacy_safety.unexpected_external_post || result.privacy_safety.forbidden_marker_request) failures.push('privacy_safety');
  for (const item of Object.values(result.public_ds_paths)) if (item.status !== 404 || item.body_bytes !== 0) failures.push(`public_ds:${item.path}`);

  result.terminal = failures.length ? 'DS_D2_PUBLIC_REPLAY_REPAIR_REQUIRED' : 'DS_D2_PUBLIC_REPLAY_PASS';
  result.failures = failures;
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = failures.length ? 1 : 0;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
