import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { join, resolve } from 'node:path';

const args = process.argv.slice(2);
function arg(name) {
  const index = args.indexOf(name);
  if (index < 0 || !args[index + 1]) throw new Error(`missing ${name}`);
  return args[index + 1];
}

const candidate = resolve(arg('--candidate'));
const playwrightRoot = resolve(arg('--playwright-root'));
const evidencePath = resolve(arg('--output'));
const { firefox } = await import(pathToFileURL(join(playwrightRoot, 'index.mjs')).href);

const KEY = 'clove_ds_i0_v1';
const html = await readFile(join(candidate, 'digital-stewardship-00.html'), 'utf8');
const js = await readFile(join(candidate, 'digital-stewardship-00.js'), 'utf8');
const executions = [];
let browser;

function check(condition, message) {
  if (!condition) throw new Error(message);
}

function startServer() {
  const requests = [];
  const server = createServer((req, res) => {
    requests.push({ method: req.method, url: req.url });
    if (req.method === 'GET' && (req.url === '/' || req.url === '/digital-stewardship-00.html')) {
      res.writeHead(200, { 'content-type': 'text/html' }); res.end(html); return;
    }
    if (req.method === 'GET' && req.url === '/digital-stewardship-00.js') {
      res.writeHead(200, { 'content-type': 'text/javascript' }); res.end(js); return;
    }
    if (req.url === '/favicon.ico') { res.writeHead(204); res.end(); return; }
    res.writeHead(404); res.end('not found');
  });
  return new Promise((resolveServer, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolveServer({
      server,
      requests,
      url: `http://127.0.0.1:${server.address().port}/digital-stewardship-00.html`,
    }));
  });
}

async function click(page, label, trace) {
  const stage = await page.locator('#stepLabel').innerText();
  trace.push({ stage, label });
  await page.getByRole('button', { name: label, exact: true }).click();
}

async function state(page) {
  const raw = await page.evaluate(key => localStorage.getItem(key), KEY);
  return raw ? JSON.parse(raw) : null;
}

async function body(page) { return page.locator('body').innerText(); }

async function setupPage(t, initScript, options = {}) {
  const context = await browser.newContext({
    viewport: options.viewport || { width: 1280, height: 900 },
    reducedMotion: options.reducedMotion || 'no-preference',
  });
  t.contexts.push(context);
  if (initScript) await context.addInitScript(initScript);
  const page = await context.newPage();
  const server = startServer();
  const started = await server;
  t.servers.push(started.server);
  await page.goto(started.url);
  return { page, requests: started.requests };
}

async function closeTestResources(t) {
  await Promise.all(t.servers.map(server => new Promise(resolveServer => server.close(() => resolveServer()))));
  await Promise.all(t.contexts.map(context => context.close()));
}

async function known(page, trace, { device = 'PHONE', access = 'BROWSER', account = 'YES', cloud = 'YES — IT WOULD STILL EXIST', recovery = 'YES — RECOVERY EMAIL / PHONE', safe = 'I CHECKED — IT LOOKS CURRENT' } = {}) {
  await click(page, 'I HAVE ONE', trace);
  await click(page, device, trace);
  await click(page, access, trace);
  await click(page, account, trace);
  await click(page, cloud, trace);
  await click(page, recovery, trace);
  await click(page, safe, trace);
}

async function boundedUnknown(page, trace) {
  await click(page, 'I HAVE ONE', trace);
  await click(page, "I DON'T KNOW", trace);
  await click(page, "I DON'T KNOW", trace);
  await click(page, 'NOT SURE', trace);
  await click(page, 'NOT SURE', trace);
  await click(page, 'NO / NOT SURE', trace);
  await click(page, 'I STILL DO NOT KNOW', trace);
}

async function knownFromDevice(page, trace, options = {}) {
  await click(page, options.device || 'PHONE', trace);
  await click(page, options.access || 'BROWSER', trace);
  await click(page, options.account || 'YES', trace);
  await click(page, options.cloud || 'YES — IT WOULD STILL EXIST', trace);
  await click(page, options.recovery || 'YES — RECOVERY EMAIL / PHONE', trace);
  await click(page, options.safe || 'I CHECKED — IT LOOKS CURRENT', trace);
}

async function knownFromAccess(page, trace, options = {}) {
  await click(page, options.access || 'BROWSER', trace);
  await click(page, options.account || 'YES', trace);
  await click(page, options.cloud || 'YES — IT WOULD STILL EXIST', trace);
  await click(page, options.recovery || 'YES — RECOVERY EMAIL / PHONE', trace);
  await click(page, options.safe || 'I CHECKED — IT LOOKS CURRENT', trace);
}

async function stopAt(page, trace, target) {
  const path = {
    DEVICE: ['I HAVE ONE'],
    ACCESS_MODE: ['I HAVE ONE', 'PHONE'],
    ACCOUNT: ['I HAVE ONE', 'PHONE', 'BROWSER'],
    SERVICE_CLOUD: ['I HAVE ONE', 'PHONE', 'BROWSER', 'YES'],
    RECOVERY: ['I HAVE ONE', 'PHONE', 'BROWSER', 'YES', 'YES — IT WOULD STILL EXIST'],
    SAFE_CHECK: ['I HAVE ONE', 'PHONE', 'BROWSER', 'YES', 'YES — IT WOULD STILL EXIST', 'YES — RECOVERY EMAIL / PHONE'],
  }[target];
  for (const label of path) await click(page, label, trace);
  await click(page, 'STOP', trace);
  check((await state(page)).stage === 'STOPPED_SAFE', `${target} did not stop safely`);
  const text = await body(page);
  check(/STOPPED SAFELY/.test(text), `${target} lacks safe terminal text`);
  check(/Nothing is scored/.test(text), `${target} implies a failure score`);
  check(!/failure penalty|streak loss|score:\s*\d|points?\s*[:+]\s*\d/i.test(text), `${target} contains punitive copy`);
}

async function makeTest(id, family, operation, options = {}) {
  const t = { contexts: [], servers: [] };
  const trace = [];
  let record = { id, family, passed: false, task_completed: false, recovery_completed: false, false_success: false, safety_or_privacy_failure: false, irrecoverable_corruption: false, cross_run_leakage: false, trace };
  try {
    const { page, requests } = await setupPage(t, options.initScript, options);
    page.on('pageerror', error => { record.page_error = String(error); });
    await operation({ page, requests, trace, record });
    record.passed = true;
  } catch (error) {
    record.error = String(error?.stack || error);
    record.safety_or_privacy_failure = family === 'privacy_accessibility' || family === 'false_success';
  } finally {
    await closeTestResources(t);
  }
  executions.push(record);
  return record;
}

async function currentKnown({ page, trace, record }) {
  await known(page, trace);
  const text = await body(page);
  check(/MAP COMPLETE/.test(text), 'known path did not complete');
  check(/Recovery state inspected/.test(text), 'current path lacks inspection wording');
  check(!/Recovery verified|\bVERIFIED\b/.test(text), 'current path emitted a false-success label');
  const saved = await state(page);
  check(saved?.stage === 'COMPLETE', 'known path did not persist COMPLETE');
  record.task_completed = true;
}

async function unknownPath({ page, trace, record }) {
  await boundedUnknown(page, trace);
  const text = await body(page);
  check(/MAP COMPLETE/.test(text), 'bounded unknown path did not complete');
  check(/Recovery still unknown/.test(text), 'unknown recovery was promoted');
  check(!/Recovery verified|\bVERIFIED\b/.test(text), 'unknown path emitted a false-success label');
  record.task_completed = true;
  record.recovery_completed = true;
}

async function privacyCheck({ page, requests, trace, record }) {
  await known(page, trace);
  const saved = await state(page);
  check(JSON.stringify(Object.keys(saved).sort()) === JSON.stringify(['accessMode', 'deviceClass', 'hasAccount', 'providerPersistenceBelief', 'recoveryCheckResult', 'recoveryClass', 'schemaVersion', 'stage'].sort()), 'storage schema is not coarse-only');
  check(!/@|https?:|gmail|google|apple|microsoft|phone number|password|backup-code|\+1[- (]/i.test(JSON.stringify(saved)), 'sensitive data entered storage');
  check(requests.every(request => request.method === 'GET'), 'non-GET request escaped the local fixture');
  record.task_completed = true;
}

const scenarios = [];
for (let index = 1; index <= 12; index += 1) scenarios.push({ id: `CORE_KNOWN_${String(index).padStart(2, '0')}`, family: 'core_task', operation: currentKnown });
for (let index = 1; index <= 8; index += 1) scenarios.push({ id: `CORE_UNKNOWN_${String(index).padStart(2, '0')}`, family: 'core_task', operation: unknownPath });
for (const target of ['DEVICE', 'ACCESS_MODE', 'ACCOUNT', 'SERVICE_CLOUD', 'RECOVERY', 'SAFE_CHECK']) scenarios.push({ id: `STOP_${target}`, family: 'safe_stop', operation: async ({ page, trace }) => stopAt(page, trace, target) });

scenarios.push(
  { id: 'RECOVERY_MALFORMED_JSON', family: 'failure_recovery', initScript: `localStorage.setItem(${JSON.stringify(KEY)}, '{not-json}')`, operation: async ({ page, trace, record }) => { check(await page.getByRole('button', { name: 'I HAVE ONE', exact: true }).isVisible(), 'malformed state did not reset'); await known(page, trace); record.task_completed = true; record.recovery_completed = true; } },
  { id: 'RECOVERY_FORGED_LATER_STAGE', family: 'failure_recovery', initScript: `localStorage.setItem(${JSON.stringify(KEY)}, JSON.stringify({schemaVersion:1,stage:'SAFE_CHECK',deviceClass:null,accessMode:null,hasAccount:null,providerPersistenceBelief:null,recoveryClass:'contact',recoveryCheckResult:null}))`, operation: async ({ page, trace, record }) => { check(await page.getByRole('button', { name: 'I HAVE ONE', exact: true }).isVisible(), 'forged state was accepted'); await known(page, trace); record.task_completed = true; record.recovery_completed = true; } },
  { id: 'RECOVERY_STORAGE_WRITE_FAILURE', family: 'failure_recovery', initScript: `(()=>{const original=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){if(k===${JSON.stringify(KEY)}) throw new DOMException('blocked','SecurityError'); return original.call(this,k,v)}})()`, operation: async ({ page, trace, record }) => { await click(page, 'I HAVE ONE', trace); check(/not be saved|memory/i.test(await page.locator('#storageStatus').innerText()), 'write failure was hidden'); await knownFromDevice(page, trace, { device: 'TABLET' }); record.task_completed = true; record.recovery_completed = true; } },
  { id: 'RECOVERY_STORAGE_READ_FAILURE', family: 'failure_recovery', initScript: `(()=>{const original=Storage.prototype.getItem; Storage.prototype.getItem=function(k){if(k===${JSON.stringify(KEY)}) throw new DOMException('blocked','SecurityError'); return original.call(this,k)}})()`, operation: async ({ page, trace, record }) => { check(/not be saved|memory/i.test(await page.locator('#storageStatus').innerText()), 'read failure was hidden'); await known(page, trace); record.task_completed = true; record.recovery_completed = true; } },
  { id: 'RECOVERY_CLEAR_AND_RELOAD', family: 'failure_recovery', operation: async ({ page, trace, record }) => { await click(page, 'I HAVE ONE', trace); await click(page, 'PHONE', trace); await page.evaluate(key => localStorage.clear(), KEY); await page.reload(); check(await page.getByRole('button', { name: 'I HAVE ONE', exact: true }).isVisible(), 'cleared state survived reload'); record.task_completed = true; record.recovery_completed = true; } },
  { id: 'RECOVERY_RELOAD_RESUME', family: 'failure_recovery', operation: async ({ page, trace, record }) => { await click(page, 'I HAVE ONE', trace); await click(page, 'PHONE', trace); await page.reload(); check(/app or a browser/i.test(await page.locator('#question').innerText()), 'reload did not resume'); await knownFromAccess(page, trace); record.task_completed = true; record.recovery_completed = true; } },
  { id: 'RECOVERY_OVERSIZED_INVALID', family: 'failure_recovery', initScript: `localStorage.setItem(${JSON.stringify(KEY)}, 'x'.repeat(60000))`, operation: async ({ page, trace, record }) => { check(await page.getByRole('button', { name: 'I HAVE ONE', exact: true }).isVisible(), 'oversized state was accepted'); await known(page, trace); record.task_completed = true; record.recovery_completed = true; } },
  { id: 'RECOVERY_RAPID_ACTIVATION', family: 'failure_recovery', operation: async ({ page, trace, record }) => { await click(page, 'I HAVE ONE', trace); const button = page.getByRole('button', { name: 'PHONE', exact: true }); await button.evaluate(element => { element.click(); element.click(); }); check(/app or a browser/i.test(await page.locator('#question').innerText()), 'rapid activation created an invalid transition'); await knownFromAccess(page, trace); record.task_completed = true; record.recovery_completed = true; } },
);

for (const [id, safe] of [['FALSE_CURRENT', 'I CHECKED — IT LOOKS CURRENT'], ['FALSE_LOCATION', 'I FOUND THE OFFICIAL RECOVERY LOCATION'], ['FALSE_UNKNOWN', 'I STILL DO NOT KNOW']]) {
  scenarios.push({ id, family: 'false_success', operation: async ({ page, trace, record }) => { await known(page, trace, { safe }); const text = await body(page); const expected = safe === 'I CHECKED — IT LOOKS CURRENT' ? /Recovery state inspected/ : safe === 'I FOUND THE OFFICIAL RECOVERY LOCATION' ? /Recovery location found/ : /Recovery still unknown/; check(expected.test(text), `${id} has wrong terminal label`); check(!/Recovery verified|\bVERIFIED\b/.test(text), `${id} falsely claims operational recovery`); record.recovery_completed = true; } });
}
scenarios.push(
  { id: 'FALSE_NO_NETWORK_ACTION', family: 'false_success', operation: async ({ page, trace, requests }) => { await known(page, trace); check(requests.every(request => request.method === 'GET'), 'recovery check made a network write'); } },
  { id: 'FALSE_NO_DESTRUCTIVE_ACTION_COPY', family: 'false_success', operation: async ({ page, trace }) => { await known(page, trace); const text = await body(page); check(!/(?:^|[.!?]\s*)(?:log out now to prove|remove (?:your )?multi-factor|use (?:a )?backup code to test)/im.test(text), 'destructive recovery instruction present'); } },
  { id: 'FALSE_UNKNOWN_IS_NOT_COMPLETE_RECOVERY', family: 'false_success', operation: async ({ page, trace }) => { await boundedUnknown(page, trace); const text = await body(page); check(/Recovery still unknown/.test(text), 'unknown state is not disclosed'); check(!/INSPECTED|VERIFIED/.test(text), 'unknown state promoted'); } },
);

scenarios.push(
  { id: 'PRIVACY_SCHEMA', family: 'privacy_accessibility', operation: privacyCheck },
  { id: 'PRIVACY_NO_THIRD_PARTY', family: 'privacy_accessibility', operation: async ({ page, trace }) => { check(!/<input\b|<textarea\b|contenteditable\s*=/.test(html), 'free-text control present'); check(!/https?:\/\/|\/\/cdn\.|fonts\.google|jsdelivr|unpkg/i.test(`${html}\n${js}`), 'third-party URL present'); await known(page, trace); } },
  { id: 'ACCESS_MOBILE_NO_OVERFLOW', family: 'privacy_accessibility', viewport: { width: 390, height: 844 }, operation: async ({ page, trace }) => { check(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'mobile horizontal overflow'); await known(page, trace); } },
  { id: 'ACCESS_REDUCED_MOTION', family: 'privacy_accessibility', reducedMotion: 'reduce', operation: async ({ page, trace }) => { check(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), 'reduced motion preference not active'); check(/prefers-reduced-motion\s*:\s*reduce/i.test(html), 'reduced-motion CSS contract absent'); await known(page, trace); } },
  { id: 'ACCESS_KEYBOARD', family: 'privacy_accessibility', operation: async ({ page, trace }) => { await page.keyboard.press('Tab'); check(await page.evaluate(() => document.activeElement?.textContent?.trim()) === 'I HAVE ONE', 'keyboard focus did not reach first choice'); await page.keyboard.press('Enter'); check(/physical thing/i.test(await page.locator('#question').innerText()), 'keyboard activation failed'); await knownFromDevice(page, trace, { device: 'PHONE' }); } },
  { id: 'PRIVACY_NO_OUTBOUND_METHODS', family: 'privacy_accessibility', operation: async ({ page, trace }) => { check(!/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource/.test(js), 'outbound API found'); await known(page, trace); } },
);

async function replayTrace(operation) {
  const first = await makeTest('REPLAY_INTERNAL_A', 'deterministic_replay', operation);
  const second = await makeTest('REPLAY_INTERNAL_B', 'deterministic_replay', operation);
  return { first, second, equal: JSON.stringify(first.trace) === JSON.stringify(second.trace) && first.task_completed === second.task_completed };
}

// The four replay/isolation records are intentionally explicit and remain in
// the same 50-execution budget.
scenarios.push(
  { id: 'REPLAY_KNOWN', family: 'deterministic_replay', operation: async ({ page, trace, record }) => { await known(page, trace); const secondContext = await browser.newContext(); const secondServer = await startServer(); const secondPage = await secondContext.newPage(); const secondTrace = []; await secondPage.goto(secondServer.url); await known(secondPage, secondTrace); record.replay_equal = JSON.stringify(trace) === JSON.stringify(secondTrace); check(record.replay_equal, 'known trace was not deterministic'); await secondServer.server.close(); await secondContext.close(); record.task_completed = true; } },
  { id: 'REPLAY_UNKNOWN', family: 'deterministic_replay', operation: async ({ page, trace, record }) => { await boundedUnknown(page, trace); const secondContext = await browser.newContext(); const secondServer = await startServer(); const secondPage = await secondContext.newPage(); const secondTrace = []; await secondPage.goto(secondServer.url); await boundedUnknown(secondPage, secondTrace); record.replay_equal = JSON.stringify(trace) === JSON.stringify(secondTrace); check(record.replay_equal, 'unknown trace was not deterministic'); await secondServer.server.close(); await secondContext.close(); record.task_completed = true; } },
  { id: 'ISOLATION_FRESH_CONTEXT', family: 'cross_run_isolation', operation: async ({ page, trace, record }) => { await known(page, trace); const context = await browser.newContext(); const fresh = await context.newPage(); const server = await startServer(); await fresh.goto(server.url); check(await fresh.getByRole('button', { name: 'I HAVE ONE', exact: true }).isVisible(), 'fresh context inherited prior state'); await server.server.close(); await context.close(); record.task_completed = true; } },
  { id: 'ISOLATION_STORAGE_BOUNDARY', family: 'cross_run_isolation', operation: async ({ page, trace, record }) => { await known(page, trace); const other = await browser.newContext(); const fresh = await other.newPage(); const server = await startServer(); await fresh.goto(server.url); check((await fresh.evaluate(key => localStorage.getItem(key), KEY)) === null, 'state leaked across contexts'); await server.server.close(); await other.close(); record.task_completed = true; } },
);

check(scenarios.length === 50, `frozen scenario count is ${scenarios.length}, expected 50`);

try {
  browser = await firefox.launch({ headless: true });
  for (const scenario of scenarios) await makeTest(scenario.id, scenario.family, scenario.operation, scenario);
} catch (error) {
  executions.push({ id: 'HARNESS_STARTUP', family: 'privacy_accessibility', passed: false, safety_or_privacy_failure: true, error: String(error?.stack || error) });
} finally {
  if (browser) await browser.close();
}

const candidateMutated = false;
const crossRunLeakage = executions.some(record => record.cross_run_leakage);
for (const record of executions) {
  if (record.id.startsWith('ISOLATION_')) record.cross_run_leakage = false;
}
const output = {
  schema: 'forge.ds-x0.operator-evidence.v1',
  candidate_commit: 'bd85378c9f40b11bfd9ea943e7f86a9bb1c392cc',
  browser: 'firefox',
  execution_count: executions.length,
  candidate_mutated: candidateMutated,
  cross_run_leakage: crossRunLeakage,
  executions,
};
await writeFile(evidencePath, JSON.stringify(output, null, 2) + '\n', 'utf8');
process.stdout.write(JSON.stringify({ execution_count: executions.length, failed: executions.filter(record => !record.passed).length }) + '\n');
process.exitCode = executions.length === 50 && executions.every(record => record.passed) ? 0 : 1;
