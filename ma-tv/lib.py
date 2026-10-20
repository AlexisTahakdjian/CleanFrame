"""ma-tv : outils communs (configuration, journal, commandes, garde-fous TV).

Tout ce qui est propre à la machine ou à la TV (IP, chemins, profil de certificat, identité de l'app)
vient de .local/ma-tv.json (ignoré par git), complété par des variables d'environnement CLEANFRAME_*.
Rien n'est écrit en dur ici. Bibliothèque standard Python uniquement (aucune dépendance à installer).
"""
from datetime import datetime
from pathlib import Path
import ipaddress
import json
import os
import re
import secrets
import shlex
import string
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
CONFIG_FILE = LOCAL / 'ma-tv.json'
EXAMPLE_FILE = ROOT / 'ma-tv' / 'config.example.json'
DIST = ROOT / 'dist' / 'ma-tv'

# Variables d'environnement qui remplacent une valeur de la configuration (clé pointée -> variable).
ENV = {
    'tv.host': 'CLEANFRAME_TV_HOST', 'tv.port': 'CLEANFRAME_TV_PORT', 'mac_ip': 'CLEANFRAME_MAC_IP',
    'sdk': 'CLEANFRAME_TIZEN_SDK', 'sign.profile': 'CLEANFRAME_SIGN_PROFILE',
    'chromium76': 'CLEANFRAME_CHROMIUM76', 'chrome_reference': 'CLEANFRAME_CHROME_REFERENCE',
}


class Stop(Exception):
    """Arrêt volontaire et propre d'une étape (garde-fou), avec un message pour l'utilisateur."""


def merge(base, extra):
    out = dict(base)
    for key, value in (extra or {}).items():
        out[key] = merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def get(cfg, dotted, default=None):
    node = cfg
    for part in dotted.split('.'):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def put(cfg, dotted, value):
    parts = dotted.split('.')
    node = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def load_config():
    cfg = json.loads(EXAMPLE_FILE.read_text())
    if CONFIG_FILE.exists():
        cfg = merge(cfg, json.loads(CONFIG_FILE.read_text()))
    for dotted, var in ENV.items():
        if os.environ.get(var):
            put(cfg, dotted, os.environ[var])
    return cfg


def save_local(patch):
    """Fusionne `patch` dans .local/ma-tv.json (fichier privé, droits 600)."""
    LOCAL.mkdir(exist_ok=True)
    current = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
    CONFIG_FILE.write_text(json.dumps(merge(current, patch), indent=2, ensure_ascii=False) + '\n')
    CONFIG_FILE.chmod(0o600)


def identity(cfg):
    """Identité de l'app propre à Alexis, générée une seule fois puis gardée stable.

    Le package ID suit la règle Tizen (10 caractères [0-9A-Za-z]). Ne jamais le changer après la première
    installation : la TV verrait une autre app et les préférences seraient perdues.
    """
    ident = get(cfg, 'identity', {}) or {}
    if not ident.get('package'):
        alphabet = string.ascii_letters + string.digits
        package = ''.join(secrets.choice(alphabet) for _ in range(10))
        name = ident.get('name') or 'CleanFrame'
        ident = {'package': package, 'app': package + '.' + re.sub(r'[^A-Za-z0-9]', '', name), 'name': name,
                 'widget_id': 'http://cleanframe.local/' + package}
        save_local({'identity': ident})
        log('Nouvelle identité d\'app générée : ' + ident['app'] + ' (enregistrée dans .local/ma-tv.json)')
    return ident


_log_file = None


def log(message):
    global _log_file
    if _log_file is None:
        (LOCAL / 'logs').mkdir(parents=True, exist_ok=True)
        _log_file = LOCAL / 'logs' / ('ma-tv-' + datetime.now().strftime('%Y%m%d') + '.log')
    line = datetime.now().strftime('%H:%M:%S') + ' ' + message
    print(message, flush=True)
    with open(_log_file, 'a') as f:
        f.write(line + '\n')


def run(command, timeout=120, check=True, show=True, secret=None, input_text=None):
    """Lance une commande en l'affichant d'abord (« $ … »). `secret` est masqué dans l'affichage et le journal."""
    shown = ' '.join(shlex.quote(str(c)) for c in command)
    if secret:
        shown = shown.replace(secret, '[masqué]')
    if show:
        log('$ ' + shown)
    try:
        result = subprocess.run([str(c) for c in command], text=True, capture_output=True, timeout=timeout, input=input_text)
    except subprocess.TimeoutExpired:
        raise Stop('Délai dépassé (' + str(timeout) + ' s) : ' + shown)
    output = (result.stdout or '') + (result.stderr or '')
    if secret:
        output = output.replace(secret, '[masqué]')
    if show and output.strip():
        for line in output.rstrip().splitlines():
            log('  ' + line)
    if check and result.returncode:
        raise Stop('Commande en échec (code ' + str(result.returncode) + ') : ' + shown)
    return output


def sdk_tool(cfg, name):
    sdk = Path(os.path.expanduser(get(cfg, 'sdk', '~/tizen-studio')))
    tool = {'tizen': sdk / 'tools/ide/bin/tizen', 'sdb': sdk / 'tools/sdb'}[name]
    if not tool.exists():
        raise Stop('Outil Samsung introuvable : ' + str(tool) + '. Renseigner "sdk" dans .local/ma-tv.json '
                   '(ou CLEANFRAME_TIZEN_SDK). Voir ma-tv/docs/procedure.md, étape « Outils Samsung ».')
    return tool


def tv_host(cfg):
    host = get(cfg, 'tv.host')
    if not host:
        raise Stop('Adresse de la TV absente : renseigner "tv": {"host": "…"} dans .local/ma-tv.json.')
    ipaddress.ip_address(host)
    return host


def serial(cfg):
    return tv_host(cfg) + ':' + str(get(cfg, 'tv.port', 26101))


def tv_api(cfg, timeout=5):
    """Lecture seule : GET http://<TV>:8001/api/v2/ (aucune écriture, aucun message à l'écran)."""
    url = 'http://' + tv_host(cfg) + ':8001/api/v2/'
    log('$ GET ' + url)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except Exception as error:
        raise Stop('La TV ne répond pas sur ' + url + ' (' + str(error) + '). Est-elle allumée, écran actif ?')


def mac_ip_towards(host):
    """IP locale du Mac sur l'interface qui mène à la TV (lecture locale, aucun paquet envoyé)."""
    out = subprocess.run(['route', '-n', 'get', host], text=True, capture_output=True).stdout
    match = re.search(r'interface:\s*(\S+)', out)
    if not match:
        return None
    return subprocess.run(['ipconfig', 'getifaddr', match.group(1)], text=True, capture_output=True).stdout.strip() or None


def guard_tv(cfg, need_developer=True):
    """Garde-fou avant toute commande qui touche la TV : bon modèle, bon appareil, mode développeur pointé sur ce Mac."""
    info = tv_api(cfg)
    device = info.get('device', {})
    expected_model = get(cfg, 'tv.model')
    if expected_model and device.get('modelName') != expected_model:
        raise Stop('Ce n\'est pas la TV attendue (' + str(device.get('modelName')) + ' au lieu de ' + expected_model + ').')
    expected_id = get(cfg, 'tv.udn')
    if expected_id and device.get('id') != expected_id:
        raise Stop('Identifiant réseau de la TV différent de celui enregistré : autre appareil à cette adresse ?')
    if need_developer:
        if device.get('developerMode') != '1':
            raise Stop('Le mode développeur de la TV est désactivé (Apps → Paramètres → 12345).')
        mine = get(cfg, 'mac_ip') or mac_ip_towards(tv_host(cfg))
        if device.get('developerIP') != mine:
            raise Stop('La TV attend le Mac ' + str(device.get('developerIP')) + ', or ce Mac est ' + str(mine)
                       + '. Corriger « Host PC IP » sur la TV (12345) ou réserver l\'IP du Mac sur la box.')
    return device


def confirm(cfg, what, args=None):
    """Pause d'accord si --confirm a été demandé ; sinon simple annonce (mise à jour automatique)."""
    if args is not None and getattr(args, 'confirm', False):
        answer = input('→ ' + what + ' : continuer ? [o/N] ').strip().lower()
        if answer not in ('o', 'oui', 'y', 'yes'):
            raise Stop('Arrêt demandé avant : ' + what)
    else:
        log('→ ' + what)


def main_guard(fn):
    try:
        fn()
    except Stop as stop:
        log('ARRÊT : ' + str(stop))
        sys.exit(2)
