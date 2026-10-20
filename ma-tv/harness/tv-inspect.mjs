// ma-tv : recette sur la vraie TV via son inspecteur (après `python3 ma-tv/tv.py debug`, qui ouvre le tunnel).
// Recharge l'app N fois et relève : erreurs console/réseau, temps jusqu'à l'écran prêt, moteur réel, viewport,
// polices, état du polyfill gap. Mesures sous inspecteur = un peu plus lentes : la mesure finale « < 2 s »
// se fait hors debug (chronomètre / vidéo), voir ma-tv/docs/procedure.md.
// Usage : node ma-tv/harness/tv-inspect.mjs --port <port> [--reloads 3] [--keys]
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { connect, key } from './cdp.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const arg = (n, d) => { const i = process.argv.indexOf('--' + n); return i > 0 ? process.argv[i + 1] : d; };
const port = arg('port'), reloads = Number(arg('reloads', 3)), withKeys = process.argv.includes('--keys');
if (!port) { console.error('Usage : node ma-tv/harness/tv-inspect.mjs --port <port>'); process.exit(2); }
const pause = ms => new Promise(r => setTimeout(r, ms));
const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
const target = targets.find(t => t.type === 'page' || t.webSocketDebuggerUrl);
if (!target) { console.error('Aucune page inspectable sur la TV.'); process.exit(2); }
const page = await connect(target.webSocketDebuggerUrl.replace(/^ws:\/\/[^/]+/, `ws://127.0.0.1:${port}`));
const errors = [], runs = [];
let run = 0;
page.on('Runtime.exceptionThrown', p => errors.push({ run, kind: 'exception', text: (p.exceptionDetails.exception || {}).description || p.exceptionDetails.text }));
page.on('Runtime.consoleAPICalled', p => { if (p.type === 'error' || p.type === 'assert') errors.push({ run, kind: 'console.' + p.type, text: p.args.map(a => a.value ?? a.description).join(' ') }); });
page.on('Log.entryAdded', p => { if (p.entry.level === 'error') errors.push({ run, kind: 'log', text: p.entry.text + ' ' + (p.entry.url || '') }); });
page.on('Network.loadingFailed', p => { if (p.errorText !== 'net::ERR_ABORTED') errors.push({ run, kind: 'chargement', text: p.errorText }); });
for (const d of ['Runtime', 'Log', 'Network', 'Page']) await page.send(d + '.enable').catch(() => {});

const probe = `({ ua: navigator.userAgent, w: innerWidth, h: innerHeight, sw: screen.width, sh: screen.height, dpr: devicePixelRatio,
  gap: window.CleanFrameCompat ? CleanFrameCompat.flexGap : 'natif', fonts: document.fonts ? document.fonts.check('500 32px Manrope') : null,
  ready: !!(window.ShoreQA && ShoreQA.ready && ShoreQA.ready()), where: window.ShoreQA ? ShoreQA.where() : null,
  fcp: ((performance.getEntriesByType('paint').filter(function (e) { return e.name === 'first-contentful-paint'; })[0]) || {}).startTime || 0,
  now: performance.now() })`;

for (run = 1; run <= reloads; run++) {
  await page.send('Page.reload', { ignoreCache: true });
  const t0 = Date.now();
  let m;
  for (let i = 0; i < 400; i++) {
    await pause(50);
    try { m = await page.evaluate(probe, { timeout: 3000 }); if (m.ready) break; } catch {}
  }
  runs.push({ run, readyAfterReloadMs: Date.now() - t0, pageNowAtReady: m && Math.round(m.now), fcp: m && Math.round(m.fcp), probe: m });
  console.log(`essai ${run} : écran prêt ≈ ${m && Math.round(m.now)} ms (horloge page), FCP ${m && Math.round(m.fcp)} ms, focus ${m && m.where && m.where.focusCount}`);
  await pause(1500);
}
if (withKeys) {
  // Touches injectées par l'inspecteur (ne remplacent pas la recette à la télécommande physique).
  for (const k of ['right', 'left', 'up', 'right', 'left', 'down', 'back', 'back']) { await key(page, k); await pause(400); }
  runs.push({ keys: await page.evaluate('ShoreQA.where()') });
}
const out = join(ROOT, '.local/qa/ma-tv/tv-' + new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '.json');
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({ runs, errors }, null, 2));
const last = runs.find(r => r.probe) || {};
console.log(`\nMoteur : ${last.probe && last.probe.ua}`);
console.log(`Viewport : ${last.probe && last.probe.w}×${last.probe && last.probe.h} (écran ${last.probe && last.probe.sw}×${last.probe && last.probe.sh}, DPR ${last.probe && last.probe.dpr}) · gap : ${last.probe && last.probe.gap} · Manrope : ${last.probe && last.probe.fonts}`);
console.log(`${errors.length} erreur(s) console/réseau sur ${reloads} rechargement(s).` + (errors.length ? '\n' + errors.map(e => `- [${e.run}] ${e.kind} : ${e.text}`).join('\n') : ''));
console.log('Rapport : ' + out.replace(ROOT + '/', ''));
page.socket.close();
process.exit(errors.length ? 1 : 0);
