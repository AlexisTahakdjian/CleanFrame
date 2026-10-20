// ma-tv : télécommande réseau Samsung (canal samsung.remote.control, port 8002), pour saisir le code du mode
// développeur quand la Smart Remote n'a pas de chiffres. Touche la TV : à lancer seulement avec l'accord d'Alexis.
// 1re connexion : la TV affiche « Autoriser ? » ; le jeton reçu est gardé dans .local/ma-tv.json (tv.remote_token).
// Retirer le Mac plus tard : Paramètres → Général → Gestionnaire d'appareils externes → Gestionnaire de connexion.
// Usage : node ma-tv/tools/remote.mjs pair            (appairage, attend l'acceptation 90 s)
//         node ma-tv/tools/remote.mjs KEY_1 KEY_2 …   (envoi de touches)
// Client WebSocket minimal (node:https) : le certificat auto-signé de la TV est accepté pour cette seule connexion.
import { existsSync, readFileSync, writeFileSync, chmodSync } from 'node:fs';
import { request } from 'node:https';
import { randomBytes } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const CONFIG = join(ROOT, '.local/ma-tv.json');
const local = existsSync(CONFIG) ? JSON.parse(readFileSync(CONFIG, 'utf8')) : {};
const host = process.env.CLEANFRAME_TV_HOST || (local.tv && local.tv.host);
if (!host) { console.error('Adresse de la TV absente (.local/ma-tv.json → tv.host).'); process.exit(2); }
// --text "…" : saisie de texte dans le champ actif (SendInputString), par exemple une adresse IP avec ses points.
const textAt = process.argv.indexOf('--text'), text = textAt > 0 ? process.argv[textAt + 1] : null;
const keys = process.argv.slice(2).filter((k, i, all) => k !== 'pair' && k !== '--text' && all[i - 1] !== '--text');
if (keys.some(k => !/^KEY_[A-Z0-9_]+$/.test(k))) { console.error('Touches attendues : KEY_1, KEY_HOME, …'); process.exit(2); }
if (text !== null && !/^[0-9A-Za-z .:-]{1,64}$/.test(text)) { console.error('Texte refusé (chiffres, lettres, points).'); process.exit(2); }
const token = local.tv && local.tv.remote_token;
const path = '/api/v2/channels/samsung.remote.control?name=' + Buffer.from('CleanFrame Mac').toString('base64') + (token ? '&token=' + token : '');
const pause = ms => new Promise(r => setTimeout(r, ms));
console.log('$ connexion wss://' + host + ':8002' + path.replace(/token=[^&]+/, 'token=[masqué]') + (token ? '' : '  → accepter « Autoriser » sur la TV'));
const timer = setTimeout(() => { console.error('Pas de réponse en 90 s (demande refusée ou ignorée sur la TV ?).'); process.exit(1); }, 90000);

function frame(text) {
  const data = Buffer.from(text), mask = randomBytes(4);
  const head = data.length < 126 ? Buffer.from([0x81, 0x80 | data.length])
    : Buffer.concat([Buffer.from([0x81, 0x80 | 126]), Buffer.from([data.length >> 8, data.length & 255])]);
  return Buffer.concat([head, mask, Buffer.from(data.map((b, i) => b ^ mask[i % 4]))]);
}
function* frames(buffer) {
  let offset = 0;
  while (buffer.length - offset >= 2) {
    let len = buffer[offset + 1] & 127, start = offset + 2;
    if (len === 126) { len = buffer.readUInt16BE(offset + 2); start = offset + 4; }
    else if (len === 127) { len = Number(buffer.readBigUInt64BE(offset + 2)); start = offset + 10; }
    if (buffer.length < start + len) break;
    yield { op: buffer[offset] & 15, text: buffer.subarray(start, start + len).toString() };
    offset = start + len;
  }
  return offset;
}

const req = request({ host, port: 8002, path, rejectUnauthorized: false, headers: {
  Connection: 'Upgrade', Upgrade: 'websocket', 'Sec-WebSocket-Version': '13', 'Sec-WebSocket-Key': randomBytes(16).toString('base64') } });
req.on('response', res => { console.error('La TV a refusé la connexion : HTTP ' + res.statusCode); process.exit(1); });
req.on('error', e => { console.error('Connexion impossible : ' + e.message); process.exit(1); });
let imeOpen = false, connected = false;
req.on('upgrade', (res, socket) => {
  let pending = Buffer.alloc(0);
  socket.on('data', async chunk => {
    pending = Buffer.concat([pending, chunk]);
    for (const f of frames(pending)) {
      pending = Buffer.alloc(0); // messages courts : un message par paquet en pratique
      if (f.op !== 1) continue;
      const msg = JSON.parse(f.text);
      if (msg.event === 'ms.channel.unauthorized') { console.error('Refusé par la TV.'); process.exit(1); }
      if (msg.event === 'ms.remote.imeStart' || msg.event === 'ms.remote.imeUpdate') imeOpen = true;
      if (msg.event !== 'ms.channel.connect' || connected) { if (msg.event) console.log('  événement TV : ' + msg.event); continue; }
      connected = true;
      clearTimeout(timer);
      if (msg.data && msg.data.token && msg.data.token !== token) {
        local.tv = { ...(local.tv || {}), remote_token: msg.data.token };
        writeFileSync(CONFIG, JSON.stringify(local, null, 2) + '\n'); chmodSync(CONFIG, 0o600);
        console.log('Appairé : jeton enregistré dans .local/ma-tv.json.');
      } else console.log('Connecté.');
      for (const k of keys) {
        socket.write(frame(JSON.stringify({ method: 'ms.remote.control', params: { Cmd: 'Click', DataOfCmd: k, Option: 'false', TypeOfRemote: 'SendRemoteKey' } })));
        console.log('  touche ' + k);
        await pause(Number(process.env.REMOTE_DELAY_MS || 150));
      }
      if (text !== null) {
        // La TV n'accepte du texte que pendant une session de saisie (clavier ouvert, événement ms.remote.imeStart).
        for (let i = 0; i < 30 && !imeOpen; i++) await pause(100);
        if (!imeOpen) { console.error('La TV n\'a pas ouvert de saisie de texte (pas de ms.remote.imeStart) : texte non envoyé.'); socket.end(); process.exit(1); }
        socket.write(frame(JSON.stringify({ method: 'ms.remote.control', params: { Cmd: Buffer.from(text).toString('base64'), DataOfCmd: 'base64', TypeOfRemote: 'SendInputString' } })));
        console.log('  texte « ' + text + ' »');
        await pause(600);
        socket.write(frame(JSON.stringify({ method: 'ms.remote.control', params: { TypeOfRemote: 'SendInputEnd' } })));
        console.log('  fin de saisie');
      }
      await pause(1500); socket.end(); process.exit(0);
    }
  });
});
req.end();
