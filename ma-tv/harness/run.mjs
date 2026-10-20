// ma-tv : recette automatique du paquet construit (dist/ma-tv/stage), dans Chromium 76 (moteur de Tizen 6.0)
// et dans le Chrome récent de référence (mise en page voulue par l'auteur). Aucun contact avec la TV.
//
// Usage : node ma-tv/harness/run.mjs [--engine m76|modern|both] [--throttle 4] [--runs 5] [--only motif] [--no-shots]
// Sortie : .local/qa/ma-tv/<horodatage>/report.json, summary.md et captures PNG. Code de sortie 1 si un test échoue.
import { createServer } from 'node:http';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { launch, key } from './cdp.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const STAGE = join(ROOT, 'dist/ma-tv/stage');
const arg = (name, fallback) => { const i = process.argv.indexOf('--' + name); return i > 0 ? process.argv[i + 1] : fallback; };
const flag = name => process.argv.includes('--' + name);
const merge = (a, b) => { const o = { ...a }; for (const [k, v] of Object.entries(b || {})) o[k] = v && typeof v === 'object' && !Array.isArray(v) && typeof o[k] === 'object' ? merge(o[k], v) : v; return o; };
const cfg = merge(JSON.parse(readFileSync(join(ROOT, 'ma-tv/config.example.json'))),
  existsSync(join(ROOT, '.local/ma-tv.json')) ? JSON.parse(readFileSync(join(ROOT, '.local/ma-tv.json'))) : {});
const ENGINES = { m76: process.env.CLEANFRAME_CHROMIUM76 || resolve(ROOT, cfg.chromium76), modern: process.env.CLEANFRAME_CHROME_REFERENCE || resolve(ROOT, cfg.chrome_reference) };
const which = arg('engine', 'both'), THROTTLE = Number(arg('throttle', 4)), RUNS = Number(arg('runs', 5)), ONLY = arg('only', '');
const SHOTS = !flag('no-shots');
const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const OUT = join(ROOT, '.local/qa/ma-tv', stamp);
mkdirSync(OUT, { recursive: true });
const pageInit = readFileSync(join(ROOT, 'ma-tv/harness/page-init.js'), 'utf8');
const SELF = (cfg.identity && cfg.identity.app) || 'test.CleanFrame';
const pause = ms => new Promise(r => setTimeout(r, ms));
if (!existsSync(join(STAGE, 'index.html'))) { console.error('Construire d\'abord : python3 ma-tv/build.py'); process.exit(2); }

// Catalogue imitant une TV française : les apps par défaut, quelques chaînes, l'app elle-même et des services système.
const CATALOG = [
  { id: 'org.tizen.netflix-app', name: 'Netflix' }, { id: '9Ur5IzDKqV.TizenYouTube', name: 'YouTube' },
  { id: 'org.tizen.primevideo', name: 'Prime Video' }, { id: 'MCmYXNxgcu.DisneyPlus', name: 'Disney+' },
  { id: 'Ahp5YrtsWm.francetvpluzz', name: 'france.tv' }, { id: 'kIciSQlYEM.tf1', name: 'TF1+' },
  { id: '3201606009684', name: 'Molotov' }, { id: SELF, name: 'CleanFrame' },
  { id: 'AbCdEf1234.worker', name: 'Background worker' }, { id: 'org.tizen.browser', name: 'Internet' },
];
const SYSTEM = ['com.samsung.tv.csfs', 'com.samsung.tv.coba.setting'];

// ---------- Serveur local (boucle locale uniquement) ----------
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.xml': 'application/xml', '.txt': 'text/plain', '.md': 'text/plain' };
const server = createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (path === '/favicon.ico') { res.writeHead(204); res.end(); return; } // requête propre au navigateur de bureau, pas à la TV
  const file = normalize(join(STAGE, path === '/' ? 'index.html' : path));
  if (!file.startsWith(STAGE) || !existsSync(file)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
  res.end(readFileSync(file));
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const BASE = 'http://127.0.0.1:' + server.address().port;

// ---------- Rapport ----------
const report = { date: new Date().toISOString(), base: 'dist/ma-tv/stage', throttle: THROTTLE, engines: {}, checks: [], errors: [], warnings: [], timings: {}, geometry: {}, unknownApi: [] };
let scenario = '', engineName = '';
function check(name, pass, detail) {
  report.checks.push({ engine: engineName, scenario, name, pass: !!pass, ...(pass ? {} : { detail }) });
  if (!pass) console.log(`  ✗ [${engineName}] ${scenario} — ${name}` + (detail !== undefined ? ' : ' + JSON.stringify(detail).slice(0, 300) : ''));
}

async function openApp(engine, test = {}, { throttle = 1 } = {}) {
  const page = await engine.newPage();
  page.errors = []; page.warnings = [];
  const err = (kind, text) => { const e = { engine: engineName, scenario, kind, text: String(text).slice(0, 600) }; page.errors.push(e); report.errors.push(e); };
  page.on('Runtime.exceptionThrown', p => err('exception', (p.exceptionDetails.exception && p.exceptionDetails.exception.description) || p.exceptionDetails.text));
  page.on('Runtime.consoleAPICalled', p => {
    const text = p.args.map(a => a.value !== undefined ? a.value : a.description).join(' ');
    if (p.type === 'error' || p.type === 'assert') err('console.' + p.type, text);
    else if (p.type === 'warning') { page.warnings.push(text); report.warnings.push({ engine: engineName, scenario, text }); }
  });
  page.on('Log.entryAdded', p => { if (p.entry.level === 'error') err('log', p.entry.text + (p.entry.url ? ' ' + p.entry.url : '')); });
  page.on('Network.requestWillBeSent', p => { if (!p.request.url.startsWith(BASE) && !p.request.url.startsWith('data:')) err('réseau externe', p.request.url); });
  page.on('Network.responseReceived', p => { if (p.response.status >= 400) err('http ' + p.response.status, p.response.url); });
  page.on('Network.loadingFailed', p => { if (p.errorText !== 'net::ERR_ABORTED' && !p.canceled) err('chargement', p.errorText); });
  for (const domain of ['Runtime', 'Log', 'Network', 'Page']) await page.send(domain + '.enable');
  await page.send('Network.setCacheDisabled', { cacheDisabled: true });
  await page.send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
  if (throttle > 1) await page.send('Emulation.setCPUThrottlingRate', { rate: throttle });
  const settings = { mock: true, catalog: CATALOG, system: SYSTEM, selfId: SELF, seed: null, ...test };
  await page.send('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__maTvTest = ' + JSON.stringify(settings) + ';\n' + pageInit });
  const t0 = Date.now();
  await page.send('Page.navigate', { url: BASE + '/index.html' });
  await page.waitFor('window.__readyAt > 0', 30000);
  page.wallMs = Date.now() - t0;
  await page.send('Emulation.setCPUThrottlingRate', { rate: 1 });
  await settle(page);
  return page;
}
const settle = async (page, ms = 450) => { await page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))'); await pause(ms); };
const where = page => page.evaluate('ShoreQA.where()');
const state = page => page.evaluate('ShoreQA.state()');
async function press(page, ...names) { for (const n of names) { await key(page, n); await settle(page, 220); } }
const tvCalls = page => page.evaluate('window.__tv ? window.__tv.calls : []');

const GEOMETRY = `(function () {
  var sel = ['[data-action]', '.label', '.u-label', '.clock', '.cap-title', '.cap-line', '.settings-title', '.setting-choice', '.settings-group',
    '.er-name', '.eo', '.btn', '.u', '.msg-acts', '.state', '.caption', '.mark', '.monogram', '.settings-group-copy', '.app-focus-name', '.util-focus-label'];
  var els = document.querySelectorAll(sel.map(function (s) { return '#stage ' + s; }).join(',')), out = {}, seen = {}, i, el, cs, r, k, cls;
  for (i = 0; i < els.length; i++) {
    el = els[i];
    if (!el.getClientRects().length) continue;
    cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    r = el.getBoundingClientRect();
    cls = (el.getAttribute('class') || '').replace(/\\bis-[\\w-]+/g, '').replace(/\\s+/g, ' ').trim();
    k = (el.getAttribute('data-action') || el.tagName.toLowerCase()) + '|' + cls;
    seen[k] = (seen[k] || 0) + 1; k += '#' + seen[k];
    out[k] = { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height),
      cut: (cs.overflow === 'hidden' || cs.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 1,
      text: (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 40) };
  }
  return { items: out, where: window.ShoreQA ? ShoreQA.where() : null };
}())`;

// Écrans parcourus pour la comparaison de mise en page et les captures.
const SCENES = [
  ['accueil-dock', async p => {}],
  ['accueil-dock-icones', async p => { await p.evaluate("ShoreQA.look({ apps: 'icons' })"); }],
  ['accueil-dock-texte', async p => { await p.evaluate("ShoreQA.look({ apps: 'text' })"); }],
  ['accueil-controles', async p => { await press(p, 'up'); }],
  ['accueil-liste', async p => { await p.evaluate("ShoreQA.look({ layout: 'list' })"); }],
  ['accueil-liste-texte', async p => { await p.evaluate("ShoreQA.look({ layout: 'list', apps: 'text' })"); }],
  ['accueil-liste-controles', async p => { await p.evaluate("ShoreQA.look({ layout: 'list' })"); await settle(p); await press(p, 'right'); }],
  ['accueil-fond-sombre', async p => { await p.evaluate("ShoreQA.look({ bg: 'dark' })"); }],
  ['accueil-fond-clair', async p => { await p.evaluate("ShoreQA.look({ bg: 'light' })"); }],
  ['quitter', async p => { await press(p, 'back'); }],
  ['toutes-les-apps', async p => { await p.evaluate("ShoreQA.scene('apps')"); await p.waitFor('ShoreQA.state().catalog.loaded'); }],
  ['reglages', async p => { await p.evaluate("ShoreQA.scene('settings')"); }],
  ['apparence', async p => { await p.evaluate("ShoreQA.scene('appearance')"); }],
  ['editeur', async p => { await p.evaluate("ShoreQA.scene('editor')"); await p.waitFor('ShoreQA.state().catalog.loaded'); }],
];

async function sceneSweep(engine) {
  report.geometry[engineName] = {};
  for (const [name, setup] of SCENES) {
    if (ONLY && !name.includes(ONLY) && !'scenes'.includes(ONLY)) continue;
    scenario = 'écran ' + name;
    const page = await openApp(engine);
    try {
      await setup(page); await page.waitFor('ShoreQA.ready()', 15000); await settle(page, 600);
      const geo = await page.evaluate(GEOMETRY);
      report.geometry[engineName][name] = geo;
      check('un seul focus visible', geo.where && geo.where.focusCount === 1, geo.where);
      check('aucune erreur', page.errors.length === 0, page.errors);
      if (SHOTS) {
        const shot = await page.send('Page.captureScreenshot', { format: 'png' });
        writeFileSync(join(OUT, `${engineName}-${name}.png`), Buffer.from(shot.data, 'base64'));
      }
    } catch (e) { check('écran atteint', false, e.message); }
    finally { await page.close(); }
  }
}

// Scénarios fonctionnels (télécommande, cas d'échec, cycle de vie).
const FLOWS = [
  ['moteur-et-touches', async engine => {
    const p = await openApp(engine);
    await p.evaluate("window.__keys = []; document.addEventListener('keydown', function (e) { __keys.push(e.keyCode); }, true); true");
    for (const k of ['left', 'up', 'right', 'down', 'ok', 'back']) await key(p, k);
    const codes = await p.evaluate('__keys');
    check('keyCode reçus identiques (37, 38, 39, 40, 13, 10009)', JSON.stringify(codes) === '[37,38,39,40,13,10009]', codes);
    await p.close();
  }],
  ['navigation-accueil', async engine => {
    const p = await openApp(engine);
    const start = (await state(p)).selected;
    await press(p, 'right'); const s1 = await state(p);
    check('Droite change l\'app sélectionnée', s1.selected !== start, [start, s1.selected]);
    await press(p, 'left');
    check('Gauche revient', (await state(p)).selected === start);
    await press(p, 'left', 'left', 'left');
    check('pas de bouclage au bord gauche', (await state(p)).selected === start);
    await press(p, 'up'); let w = await where(p);
    check('Haut ouvre les contrôles', w.zone === 'util' && w.focusCount === 1, w);
    const actions = await p.evaluate('ShoreQA.actions()');
    check('Art Mode absent des contrôles', !actions.includes('util.art'), actions);
    await press(p, 'right', 'left', 'down'); w = await where(p);
    check('Bas revient aux apps', w.zone === 'apps' && w.focusCount === 1, w);
    await press(p, 'back'); w = await where(p);
    check('Retour à l\'accueil ouvre « Leave Home? »', w.view === 'message', w);
    await press(p, 'back'); w = await where(p);
    check('Retour ferme le message', w.view === 'home' && w.focusCount === 1, w);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['niveaux-retour', async engine => {
    const p = await openApp(engine);
    await press(p, 'up', 'right'); // contrôle Settings (Art masqué : All apps, Settings)
    let w = await where(p);
    await press(p, 'ok'); w = await where(p);
    check('OK sur Settings ouvre les réglages', w.view === 'settings', w);
    await press(p, 'ok'); w = await where(p);
    const depth = w.view;
    await press(p, 'back'); w = await where(p);
    check('Retour remonte d\'un niveau', depth === 'settings' || w.view === 'settings', [depth, w.view]);
    await press(p, 'back'); w = await where(p);
    check('Retour revient à l\'accueil', w.view === 'home' && w.focusCount === 1, w);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['lancement-app', async engine => {
    const p = await openApp(engine);
    const sel = (await state(p)).selected;
    await press(p, 'ok'); await pause(200);
    const calls = await tvCalls(p);
    check('OK lance l\'app sélectionnée (tizen.application.launch)', calls.some(c => c.method === 'launch'), calls);
    check('Netflix par défaut, ID de la config locale', calls[0] && calls[0].id === 'org.tizen.netflix-app', [sel, calls]);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['appui-tenu-ok', async engine => {
    const p = await openApp(engine);
    await key(p, 'ok', { hold: 1000, repeat: 8 }); await settle(p);
    const calls = (await tvCalls(p)).filter(c => c.method === 'launch');
    check('OK maintenu = un seul lancement', calls.length === 1, calls);
    await p.close();
  }],
  ['app-absente', async engine => {
    const p = await openApp(engine, { catalog: CATALOG.filter(a => a.id !== 'org.tizen.netflix-app') });
    await press(p, 'ok'); await settle(p, 400);
    let w = await where(p);
    check('message propre si l\'app n\'est pas installée', w.view === 'message', w);
    await press(p, 'back'); w = await where(p);
    check('Retour ferme le message, focus restauré', w.view === 'home' && w.focusCount === 1, w);
    await press(p, 'right', 'ok'); await pause(300);
    check('les touches remarchent après l\'échec', (await tvCalls(p)).filter(c => c.method === 'launch').length === 2);
    check('aucune erreur console', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['lancement-muet', async engine => {
    const p = await openApp(engine, { launch: 'silent' });
    await press(p, 'ok'); await pause(8600); await settle(p);
    let w = await where(p);
    check('après 8 s sans réponse : message « The TV did not respond »', w.view === 'message', w);
    await press(p, 'back', 'right'); w = await where(p);
    check('les touches remarchent', w.view === 'home' && w.focusCount === 1, w);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['catalogue-en-echec', async engine => {
    const p = await openApp(engine, { catalogMode: 'fail' });
    await p.evaluate("ShoreQA.scene('apps')"); await settle(p, 500);
    let s = await state(p);
    check('erreur de catalogue lisible', !!s.catalog.error, s.catalog);
    await p.evaluate("__tv.catalogMode = 'ok'; true");
    await press(p, 'ok'); await settle(p, 500);
    s = await state(p);
    check('« Try again » recharge le catalogue', s.catalog.loaded && !s.catalog.error, s.catalog);
    check('l\'app ne se liste pas elle-même', !s.catalog.ids.includes(SELF), s.catalog.ids);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['samsung-home', async engine => {
    const p = await openApp(engine);
    await press(p, 'back', 'right', 'ok'); await pause(300);
    const calls = await tvCalls(p);
    check('« Samsung Home » lance l\'ID système configuré', calls.some(c => c.id === 'com.samsung.tv.csfs'), calls);
    await p.close();
  }],
  ['sans-api-tizen', async engine => {
    const p = await openApp(engine, { mock: false });
    await press(p, 'ok'); await settle(p, 300);
    const w = await where(p);
    check('navigateur sans tizen : message, pas d\'exception', w.view === 'message' && p.errors.length === 0, [w, p.errors]);
    await p.close();
  }],
  ['touches-non-gerees', async engine => {
    const p = await openApp(engine);
    const before = JSON.stringify(await where(p));
    for (const k of ['red', 'green', 'yellow', 'blue', 'play', 'pause', 'playpause', 'stop', 'rewind', 'forward', 'one', 'zero', 'chup', 'chdown', 'exit']) await key(p, k);
    await settle(p);
    check('couleurs, médias, chiffres, chaînes, Exit : sans effet', JSON.stringify(await where(p)) === before);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['rafale-de-touches', async engine => {
    const p = await openApp(engine, {}, {});
    for (let i = 0; i < 30; i++) { await key(p, i % 2 ? 'left' : 'right'); await pause(15); }
    await key(p, 'right', { hold: 1500, repeat: 40 });
    await settle(p, 600);
    const w = await where(p);
    check('rafales et flèche maintenue : un seul focus, pas de blocage', w.focusCount === 1 && w.view === 'home', w);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['masquage-reprise', async engine => {
    const p = await openApp(engine);
    await p.evaluate('__setHidden(true); true'); await pause(300);
    await p.evaluate('__setHidden(false); true'); await settle(p);
    const w = await where(p);
    check('reprise (retour d\'une autre app / veille) : focus et accueil intacts', w.view === 'home' && w.focusCount === 1, w);
    await press(p, 'right');
    check('première touche après reprise traitée', (await where(p)).focusCount === 1);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
  ['persistance', async engine => {
    const p = await openApp(engine);
    await p.evaluate("ShoreQA.look({ layout: 'list', bg: 'dark' })"); await settle(p);
    await p.send('Page.reload', { ignoreCache: true });
    await p.waitFor('window.__readyAt > 0', 30000); await settle(p);
    const s = await state(p);
    check('réglages conservés après relance', s.committed.layout === 'list' && s.committed.bg === 'dark', s.committed);
    check('aucune erreur', p.errors.length === 0, p.errors);
    await p.close();
  }],
];

async function startup(engine) {
  scenario = 'démarrage';
  const ready = [], fcp = [];
  for (let i = 0; i < RUNS; i++) {
    const p = await openApp(engine, {}, { throttle: THROTTLE });
    const m = await p.evaluate("({ ready: __readyAt, fcp: (performance.getEntriesByType('paint').filter(function (e) { return e.name === 'first-contentful-paint'; })[0] || {}).startTime || 0 })");
    ready.push(Math.round(m.ready)); fcp.push(Math.round(m.fcp));
    check('aucune erreur au démarrage à froid (essai ' + (i + 1) + ')', p.errors.length === 0, p.errors);
    await p.close();
  }
  const med = a => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
  report.timings[engineName] = { throttle: THROTTLE, readyMs: ready, fcpMs: fcp, readyMedian: med(ready), fcpMedian: med(fcp) };
  // Le critère « < 2 s » vaut sur la TV. Tant que le bridage n'est pas calibré sur une mesure réelle
  // (harness.calibrated_throttle dans .local/ma-tv.json), la valeur est rapportée sans juger.
  const calibrated = cfg.harness && cfg.harness.calibrated_throttle;
  if (calibrated && Number(calibrated) === THROTTLE) check(`écran prêt médian < 2000 ms (bridage calibré ÷${THROTTLE})`, med(ready) < 2000, ready);
  else report.timings[engineName].note = 'non vérifié : bridage non calibré sur la TV';
}

function compareGeometry() {
  const a = report.geometry.m76, b = report.geometry.modern;
  if (!a || !b) return;
  engineName = 'm76 vs moderne';
  for (const name of Object.keys(a)) {
    if (!b[name]) continue;
    scenario = 'mise en page ' + name;
    const A = a[name].items, B = b[name].items, diffs = [], missing = [], cut = [];
    for (const k of Object.keys(B)) {
      if (!A[k]) { missing.push(k); continue; }
      const d = Math.max(Math.abs(A[k].x - B[k].x), Math.abs(A[k].y - B[k].y), Math.abs(A[k].w - B[k].w), Math.abs(A[k].h - B[k].h));
      if (d > 4) diffs.push({ k, m76: A[k], ref: B[k], d });
      if (A[k].cut && !B[k].cut) cut.push({ k, text: A[k].text });
    }
    check('éléments présents comme dans la référence', missing.length === 0, missing.slice(0, 12));
    check('positions et tailles à ±4 px de la référence', diffs.length === 0, diffs.slice(0, 8).map(x => ({ k: x.k, d: x.d, m76: [x.m76.x, x.m76.y, x.m76.w, x.m76.h], ref: [x.ref.x, x.ref.y, x.ref.w, x.ref.h] })));
    check('aucun texte coupé en plus', cut.length === 0, cut);
  }
}

// ---------- Exécution ----------
const order = which === 'both' ? ['modern', 'm76'] : [which];
for (const name of order) {
  engineName = name;
  if (!existsSync(ENGINES[name])) { check('navigateur présent', false, ENGINES[name]); continue; }
  const engine = await launch(ENGINES[name], { modern: name === 'modern', profileRoot: join(ROOT, '.local') });
  report.engines[name] = engine.version.Browser;
  console.log(`\n== ${name} : ${engine.version.Browser} (V8 ${engine.version['V8-Version']})`);
  scenario = 'moteur';
  if (name === 'm76') check('moteur = Chromium 76.0.3809 (Tizen 6.0 : 76.0.3809.146)', /\/76\.0\.3809\./.test(engine.version.Browser), engine.version.Browser);
  try {
    await sceneSweep(engine);
    for (const [flowName, fn] of FLOWS) {
      if (ONLY && !flowName.includes(ONLY)) continue;
      scenario = flowName;
      try { await fn(engine); } catch (e) { check('scénario exécuté', false, e.message); }
    }
    if (!ONLY || 'démarrage'.includes(ONLY)) await startup(engine);
    const unknown = new Set();
    // Une page de plus pour collecter les accès hors API imitée pendant un parcours complet.
    scenario = 'api-tizen';
    const p = await openApp(engine);
    await press(p, 'right', 'up', 'right', 'ok', 'back', 'back', 'ok');
    (await p.evaluate('__tv.unknown')).forEach(x => unknown.add(x));
    await p.close();
    report.unknownApi.push({ engine: name, accesses: [...unknown] });
    check('aucun accès à une API Tizen non imitée', unknown.size === 0, [...unknown]);
  } finally { await engine.close(); }
}
compareGeometry();
server.close();

const failed = report.checks.filter(c => !c.pass);
writeFileSync(join(OUT, 'report.json'), JSON.stringify(report, null, 2));
const lines = [`# Recette ma-tv — ${report.date}`, '', `Moteurs : ${Object.entries(report.engines).map(([k, v]) => k + ' = ' + v).join(' ; ')}`,
  `Bridage CPU pour le démarrage : ÷${THROTTLE}`, '',
  `**${report.checks.length - failed.length} / ${report.checks.length} vérifications réussies**, ${report.errors.length} erreur(s) console/réseau.`, ''];
for (const [k, v] of Object.entries(report.timings)) lines.push(`- Démarrage ${k} : écran prêt médian ${v.readyMedian} ms (${v.readyMs.join(', ')}), FCP médian ${v.fcpMedian} ms`);
if (failed.length) { lines.push('', '## Échecs'); for (const f of failed) lines.push(`- [${f.engine}] ${f.scenario} — ${f.name} : \`${JSON.stringify(f.detail).slice(0, 400)}\``); }
if (report.errors.length) { lines.push('', '## Erreurs'); for (const e of report.errors.slice(0, 50)) lines.push(`- [${e.engine}] ${e.scenario} — ${e.kind} : ${e.text}`); }
writeFileSync(join(OUT, 'summary.md'), lines.join('\n') + '\n');
console.log('\n' + lines.slice(4).join('\n'));
console.log('\nRapport : ' + OUT.replace(ROOT + '/', ''));
process.exit(failed.length ? 1 : 0);
