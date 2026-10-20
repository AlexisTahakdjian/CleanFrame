// ma-tv : client DevTools minimal (WebSocket natif de Node, aucune dépendance npm).
// Pilote Chromium 76 (moteur de Tizen 6.0) ou le Chrome de référence, en local uniquement.
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const pause = ms => new Promise(r => setTimeout(r, ms));

function freePort() {
  return new Promise((resolve, reject) => {
    const srv = createServer();
    srv.listen(0, '127.0.0.1', () => { const { port } = srv.address(); srv.close(() => resolve(port)); });
    srv.on('error', reject);
  });
}

export async function launch(executable, { modern = false, profileRoot } = {}) {
  const port = await freePort();
  const profile = mkdtempSync(join(profileRoot || tmpdir(), 'ma-tv-profile-'));
  const args = [
    '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-background-networking', '--disable-component-update', '--disable-sync', '--mute-audio',
    '--hide-scrollbars', '--force-device-scale-factor=1', '--window-size=1920,1080',
    // Profil jetable, DevTools sur la boucle locale, aucune résolution DNS hors 127.0.0.1 (navigateur ancien).
    '--user-data-dir=' + profile, '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=' + port,
    '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1', 'about:blank',
  ];
  const child = spawn(executable, args, { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  child.stderr.on('data', d => { stderr += d; if (stderr.length > 20000) stderr = stderr.slice(-20000); });
  let version;
  for (let i = 0; i < 120 && !version; i++) {
    try { version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); } catch { await pause(250); }
  }
  if (!version) { child.kill(); throw Error('Navigateur non joignable (' + executable + ')\n' + stderr.slice(-2000)); }
  const browser = await connect(version.webSocketDebuggerUrl);
  return {
    port, version, browser, child,
    async newPage() {
      const { browserContextId } = await browser.send('Target.createBrowserContext');
      const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank', browserContextId });
      const page = await connect(`ws://127.0.0.1:${port}/devtools/page/${targetId}`);
      page.close = async () => {
        page.socket.close();
        await browser.send('Target.closeTarget', { targetId }).catch(() => {});
        await browser.send('Target.disposeBrowserContext', { browserContextId }).catch(() => {});
      };
      return page;
    },
    async close() {
      browser.socket.close();
      child.kill('SIGTERM');
      await pause(300);
      try { rmSync(profile, { recursive: true, force: true }); } catch {}
    },
  };
}

export function connect(url) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    let id = 0;
    const pending = new Map(), listeners = new Map();
    const api = {
      socket,
      send(method, params = {}) {
        return new Promise((res, rej) => {
          const n = ++id;
          pending.set(n, { res, rej, method });
          socket.send(JSON.stringify({ id: n, method, params }));
        });
      },
      on(event, fn) { if (!listeners.has(event)) listeners.set(event, []); listeners.get(event).push(fn); },
      async evaluate(expression, { awaitPromise = true, timeout = 20000 } = {}) {
        const run = api.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true });
        const result = await Promise.race([run, pause(timeout).then(() => ({ timedOut: true }))]);
        if (result.timedOut) throw Error('Délai dépassé : ' + expression.slice(0, 120));
        if (result.exceptionDetails) {
          const d = result.exceptionDetails;
          throw Error('Exception page : ' + (d.exception && d.exception.description || d.text));
        }
        return result.result.value;
      },
      async waitFor(expression, timeout = 15000, every = 50) {
        const end = Date.now() + timeout;
        while (Date.now() < end) {
          try { if (await api.evaluate(expression)) return true; } catch {}
          await pause(every);
        }
        throw Error('Condition non atteinte en ' + timeout + ' ms : ' + expression);
      },
    };
    socket.addEventListener('open', () => resolve(api));
    socket.addEventListener('error', e => reject(Error('WebSocket DevTools : ' + (e.message || url))));
    socket.addEventListener('message', ev => {
      const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString());
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id); pending.delete(msg.id);
        if (msg.error) p.rej(Error(p.method + ' : ' + msg.error.message)); else p.res(msg.result);
      } else if (msg.method && listeners.has(msg.method)) {
        for (const fn of listeners.get(msg.method)) fn(msg.params);
      }
    });
  });
}

// Touches de la télécommande Samsung (guide Samsung « Remote Control ») envoyées comme de vrais keydown/keyup.
export const REMOTE = {
  left: [37, 'ArrowLeft'], up: [38, 'ArrowUp'], right: [39, 'ArrowRight'], down: [40, 'ArrowDown'],
  ok: [13, 'Enter'], back: [10009, 'XF86Back'], exit: [10182, 'XF86Exit'],
  red: [403, 'ColorF0Red'], green: [404, 'ColorF1Green'], yellow: [405, 'ColorF2Yellow'], blue: [406, 'ColorF3Blue'],
  play: [415, 'MediaPlay'], pause: [19, 'MediaPause'], playpause: [10252, 'MediaPlayPause'], stop: [413, 'MediaStop'],
  rewind: [412, 'MediaRewind'], forward: [417, 'MediaFastForward'], one: [49, '1'], zero: [48, '0'],
  chup: [427, 'ChannelUp'], chdown: [428, 'ChannelDown'], escape: [27, 'Escape'], backspace: [8, 'Backspace'],
};

export async function key(page, name, { hold = 0, repeat = 0 } = {}) {
  const [code, keyName] = REMOTE[name];
  const base = { windowsVirtualKeyCode: code, nativeVirtualKeyCode: code, key: keyName, code: keyName };
  await page.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', ...base });
  for (let i = 0; i < repeat; i++) {
    await pause(hold / Math.max(1, repeat));
    await page.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', autoRepeat: true, ...base });
  }
  if (!repeat && hold) await pause(hold);
  await page.send('Input.dispatchKeyEvent', { type: 'keyUp', ...base });
}
