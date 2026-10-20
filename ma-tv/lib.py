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
import signal
import string
import subprocess
import sys
import traceback
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


class Cancelled(Stop):
    """L'utilisateur a refusé une commande : ce n'est pas un échec (aucun retour arrière automatique)."""


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
    """Fusionne `patch` dans .local/ma-tv.json (fichier privé, droits 600, écriture atomique)."""
    LOCAL.mkdir(exist_ok=True)
    current = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
    temp = CONFIG_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(merge(current, patch), indent=2, ensure_ascii=False) + '\n')
    temp.chmod(0o600)
    temp.replace(CONFIG_FILE)


def identity(cfg, create=False):
    """Identité de l'app propre à Alexis : lue, ou créée UNE fois (premier build, create=True).

    Le package ID suit la règle Tizen (10 caractères [0-9A-Za-z]). Ne jamais le changer après la première
    installation : la TV verrait une autre app et les préférences seraient perdues. Si l'identité a disparu
    alors qu'une version a déjà été signée ou installée, on s'arrête au lieu d'en inventer une autre.
    """
    ident = get(cfg, 'identity', {}) or {}
    package, app = ident.get('package') or '', ident.get('app') or ''
    if package and app:
        if not re.fullmatch(r'[0-9A-Za-z]{10}', package) or not app.startswith(package + '.'):
            raise Stop('Identité d\'app invalide dans .local/ma-tv.json (package « ' + package + ' », app « ' + app + ' »).')
        return ident
    already = get(cfg, 'sign.author_sha256') or list((LOCAL / 'releases').glob('*.wgt'))
    if not create or already:
        raise Stop('Identité d\'app absente de .local/ma-tv.json' + (' alors qu\'une version a déjà été signée/installée : '
                   'restaurer .local/ma-tv.json depuis la sauvegarde (sinon la TV verrait une 2e app).' if already else '.'))
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


def run(command, timeout=120, check=True, show=True, secret=None, input_text=None, env=None, with_code=False):
    """Lance une commande en l'affichant d'abord (« $ … »). `secret` est masqué dans l'affichage et le journal.

    En cas de délai dépassé, tout le groupe de processus est tué (le CLI tizen lance un Java enfant).
    with_code=True renvoie (code, sortie) au lieu de la sortie seule.
    """
    shown = ' '.join(shlex.quote(str(c)) for c in command)
    if secret:
        shown = shown.replace(secret, '[masqué]')
    if show:
        log('$ ' + shown)
    proc = subprocess.Popen([str(c) for c in command], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                            env={**os.environ, **(env or {})}, start_new_session=True)
    try:
        output, _ = proc.communicate(input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise Stop('Délai dépassé (' + str(timeout) + ' s) : ' + shown)
    output = output or ''
    if secret:
        output = output.replace(secret, '[masqué]')
    if show and output.strip():
        for line in output.rstrip().splitlines():
            log('  ' + line)
    if check and proc.returncode:
        raise Stop('Commande en échec (code ' + str(proc.returncode) + ') : ' + shown)
    return (proc.returncode, output) if with_code else output


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
            return json.loads(response.read().decode(), strict=False)  # la TV renvoie des sauts de ligne bruts
    except OSError as error:
        hint = ' Si Node/Python ne joignent pas la TV mais curl oui : autoriser « Réseau local » pour le terminal ' \
               '(Réglages Système → Confidentialité et sécurité).' if 'route to host' in str(error) else ''
        raise Stop('La TV ne répond pas sur ' + url + ' (' + str(error) + '). Est-elle allumée, écran actif ?' + hint)


def mac_ip_towards(host):
    """IP locale du Mac sur l'interface qui mène à la TV (lecture locale, aucun paquet envoyé)."""
    out = subprocess.run(['route', '-n', 'get', host], text=True, capture_output=True).stdout
    match = re.search(r'interface:\s*(\S+)', out)
    if not match:
        return None
    return subprocess.run(['ipconfig', 'getifaddr', match.group(1)], text=True, capture_output=True).stdout.strip() or None


def guard_tv(cfg, need_developer=True):
    """Garde-fou avant toute commande vers la TV : bon modèle, bon appareil, mode développeur pointé sur ce Mac."""
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
            raise Stop('Le mode développeur de la TV est désactivé (Applications → 12345, voir ma-tv/docs/procedure.md).')
        live, saved = mac_ip_towards(tv_host(cfg)), get(cfg, 'mac_ip')
        if live and saved and live != saved:
            raise Stop('L\'IP du Mac a changé (enregistrée ' + saved + ', actuelle ' + live + ') : mettre à jour "mac_ip" '
                       'dans .local/ma-tv.json et « Host PC IP » sur la TV (12345), ou réserver l\'IP du Mac sur la box.')
        mine = live or saved
        if device.get('developerIP') != mine:
            raise Stop('La TV attend le Mac ' + str(device.get('developerIP')) + ', or ce Mac est ' + str(mine)
                       + ' : corriger « Host PC IP » sur la TV (Applications → 12345).')
    return device


def main_guard(fn):
    try:
        fn()
    except Stop as stop:
        log('ARRÊT : ' + str(stop))
        sys.exit(2)
    except KeyboardInterrupt:
        log('ARRÊT : interrompu (Ctrl-C).')
        sys.exit(130)
    except Exception:
        log('ARRÊT INATTENDU (bug ou changement imprévu en amont) :\n' + traceback.format_exc())
        sys.exit(3)
