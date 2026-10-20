"""ma-tv : construire le paquet .wgt (non signé) pour la TV d'Alexis, sans exécuter de code de l'auteur.

Étapes :
  1. barrières (refus si l'amont introduit quelque chose d'incompatible ou de risqué) ;
  2. copie de app/ dans dist/ma-tv/stage/ (mêmes exclusions que scripts/font_assets.py de l'auteur) ;
  3. adaptations Tizen 6.0 / Chromium 76 appliquées à la copie (les fichiers de l'auteur restent intacts) ;
  4. archive dist/ma-tv/CleanFrame-<version>-unsigned.wgt + rapport build.json.

Usage : python3 ma-tv/build.py [--required-version 6.5] [--check-only]
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as XML
import zipfile

import lib
from lib import Stop, log

APP = lib.ROOT / 'app'
STAGE = lib.DIST / 'stage'
NS = {'w': 'http://www.w3.org/ns/widgets', 't': 'http://tizen.org/ns/widgets'}

# Privilèges publics nécessaires et vérifiés pour Tizen 6.0. Tout ajout en amont arrête le build.
ALLOWED_PRIVILEGES = {
    'http://tizen.org/privilege/application.launch',
    'http://tizen.org/privilege/application.info',
    'http://tizen.org/privilege/tv.inputdevice',
}
# Adresses autorisées dans le code : uniquement des espaces de noms XML/Tizen, jamais du réseau.
URL_ALLOW = re.compile(r'https?://(?:www\.w3\.org|tizen\.org|samsung\.com/tv/metadata|cleanframe\.local)[^\s"\'<>)]*')

# Fonctions CSS absentes de Chromium 76 (sources : MDN browser-compat-data, caniuse) que nous ne savons pas
# convertir automatiquement : leur apparition en amont arrête la mise à jour.
CSS_BLOCKERS = [
    (r'(?<![\w-])aspect-ratio\s*:', 'aspect-ratio (Chrome 88)'),
    (r'(?<![\w-])inset-(?:inline|block)(?:-start|-end)?\s*:', 'inset-inline/block (Chrome 87)'),
    (r'[;{]\s*(?:translate|rotate|scale)\s*:', 'propriétés translate/rotate/scale (Chrome 104)'),
    (r'(?<![\w-])accent-color\s*:', 'accent-color (Chrome 93)'),
    (r'(?<![\w-])content-visibility\s*:', 'content-visibility (Chrome 85)'),
    (r'overflow(?:-[xy])?\s*:\s*clip', 'overflow: clip (Chrome 90)'),
    (r'(?<![\w-])container(?:-type|-name)?\s*:', 'container queries (Chrome 105)'),
    (r'@container|@layer|@property|@supports\s+selector\(', 'règle @ récente'),
    (r':(?:is|where|has)\(', 'sélecteur :is/:where/:has (Chrome 88+)'),
    (r'::marker', '::marker (Chrome 86)'),
    (r':focus-visible', ':focus-visible (Chrome 86)'),
    (r'(?<![\w-])(?:clamp|min|max)\(', 'clamp()/min()/max() (Chrome 79)'),
    (r'(?<![\w-])(?:color-mix|lab|lch|oklab|oklch|hwb)\(', 'couleurs CSS Color 4/5'),
    (r'\d(?:dvh|svh|lvh|dvw|svw|lvw|cqw|cqh|cqi|cqb)\b', 'unités viewport dynamiques / conteneur'),
    (r'(?<![\w-])text-(?:decoration-thickness|underline-offset)\s*:', 'text-decoration-thickness/underline-offset (Chrome 87)'),
    (r'(?<![\w-])scrollbar-gutter\s*:', 'scrollbar-gutter (Chrome 94)'),
    (r'(?<![\w$-])inset\s*:', 'inset (Chrome 87) non converti'),
    (r'&\s*[.:#\[>~+]', 'imbrication CSS (Chrome 112)'),
]
# Ignorées sans effet visible majeur en Chromium 76 (polices optionnelles) : signalées, acceptées.
CSS_ACCEPTED = [
    (r'(?<![\w-])size-adjust\s*:', 'size-adjust (Chrome 92)'),
    (r'(?<![\w-])(?:ascent|descent|line-gap)-override\s*:', '*-override (Chrome 87)'),
    (r'(?<![\w-])font-synthesis\s*:', 'font-synthesis (Chrome 97)'),
    (r'(?<![\w-])font-optical-sizing\s*:', 'font-optical-sizing (Chrome 79)'),
]
# JavaScript : syntaxe et API absentes de V8 7.6 / Chromium 76. Le chargement réel dans Chromium 76
# (ma-tv/harness) reste le juge final ; cette liste arrête tôt les cas connus.
JS_BLOCKERS = [
    (r'\?\.(?!\d)', 'chaînage optionnel ?. (Chrome 80)'),
    (r'\?\?', 'opérateur ?? (Chrome 80)'),
    (r'(?:\|\||&&)=', 'affectation logique (Chrome 85)'),
    (r'\.at\(', 'Array/String .at() (Chrome 92)'),
    (r'\.replaceAll\(', 'replaceAll (Chrome 85)'),
    (r'\.findLast(?:Index)?\(', 'findLast (Chrome 97)'),
    (r'\.to(?:Sorted|Reversed|Spliced)\(', 'toSorted/toReversed (Chrome 110)'),
    (r'Object\.hasOwn\(', 'Object.hasOwn (Chrome 93)'),
    (r'structuredClone\(', 'structuredClone (Chrome 98)'),
    (r'Promise\.any\(|AggregateError|WeakRef|FinalizationRegistry', 'Promise.any/WeakRef (Chrome 84-85)'),
    (r'AbortSignal\.(?:timeout|any)\(', 'AbortSignal.timeout (Chrome 103)'),
    (r'import\.meta|\bstatic\s*\{', 'syntaxe module/classe récente'),
    (r'#[A-Za-z_]\w*\s*(?:[=;(]|in\b)', 'membres privés de classe (Chrome 74-91)'),
    (r'\breplaceChildren\(', 'replaceChildren (Chrome 86)'),
]
NETWORK = re.compile(r'\bfetch\s*\(|XMLHttpRequest|\bWebSocket\s*\(|EventSource\s*\(|sendBeacon\s*\(|importScripts\s*\(|<access\b|allow-navigation|content-security-policy')
INDEX_ANCHOR = '<script src="device.js"></script>'
INJECT = ('<!-- ma-tv : réglages locaux et compatibilité Tizen 6.0 (injectés au build) -->\n'
          '<script src="ma-tv-config.js"></script>\n<script src="ma-tv-gap.js"></script>\n<script src="compat-tizen6.js"></script>\n')


def runtime_source(name):
    """Mêmes exclusions que scripts/font_assets.py (outils de rendu de l'auteur, jamais dans le widget)."""
    if name in ('grid.css', 'optics.js') or name.startswith(('assets/grid/', 'assets/vendor/', 'assets/private-fonts/')):
        return False
    if re.fullmatch(r'assets/wallpapers/[^/]+-glass-\d+\.png', name):
        return False
    base = Path(name).name
    if base == '.DS_Store' or base.startswith('._'):
        return False
    return not (base.startswith('PP') and Path(name).suffix.lower() in ('.ttf', '.otf', '.woff', '.woff2'))


def strip_css_comments(text):
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


def strip_js(text):
    """Retire commentaires et chaînes (approximation suffisante pour du code ES5 lisible)."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('//', i):
            j = text.find('\n', i); i = n if j < 0 else j; continue
        if text.startswith('/*', i):
            j = text.find('*/', i + 2); i = n if j < 0 else j + 2; continue
        if c in '\'"`':
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == '\\' else 1
            out.append(c + c); i = j + 1; continue
        out.append(c); i += 1
    return ''.join(out)


def gates(config_xml):
    """Barrières : retourne (erreurs, avertissements)."""
    errors, warnings = [], []
    if (lib.ROOT / 'scripts/native-home').exists():
        errors.append("scripts/native-home est présent (supprimé dans ma-tv, réintroduit par l'amont ?) : "
                      "outil d'écriture système de l'auteur, interdit sur cette TV.")
    root = XML.fromstring(config_xml)
    privileges = {p.get('name') for p in root.findall('t:privilege', NS)}
    extra = privileges - ALLOWED_PRIVILEGES
    if extra:
        errors.append('Nouveau(x) privilège(s) demandé(s) par l\'amont : ' + ', '.join(sorted(extra)))
    if root.findall('w:access', NS) or root.findall('t:allow-navigation', NS) or root.findall('t:content-security-policy', NS):
        errors.append('config.xml ouvre un accès réseau (<access>, allow-navigation ou CSP).')
    for path in sorted(APP.rglob('*')):
        name = path.relative_to(APP).as_posix()
        if not path.is_file() or not runtime_source(name) or path.suffix not in ('.js', '.html', '.css'):
            continue
        text = path.read_text(errors='replace')
        for url in re.findall(r'https?://[^\s"\'<>)]+', text):
            if not URL_ALLOW.match(url):
                errors.append(name + ' : adresse réseau ' + url)
        if path.suffix in ('.js', '.html') and NETWORK.search(strip_js(text) if path.suffix == '.js' else text):
            errors.append(name + ' : appel réseau (' + NETWORK.search(strip_js(text) if path.suffix == '.js' else text).group(0) + ')')
        if path.suffix == '.js':
            code = strip_js(text)
            for pattern, label in JS_BLOCKERS:
                if re.search(pattern, code):
                    errors.append(name + ' : ' + label)
    return errors, warnings


def expand_inset(match):
    values = match.group(2).split()
    important = match.group(3) or ''
    if not 1 <= len(values) <= 4:
        return match.group(0)
    top = values[0]; right = values[1] if len(values) > 1 else top
    bottom = values[2] if len(values) > 2 else top; left = values[3] if len(values) > 3 else right
    return match.group(1) + ';'.join(side + ':' + value + important for side, value in
                                     (('top', top), ('right', right), ('bottom', bottom), ('left', left)))


def adapt_css(text):
    """Conversions sûres pour Chromium 76 : `inset` → top/right/bottom/left ; `:focus-visible` → `:focus`
    (pas de souris sur la TV : le focus vient toujours de la télécommande)."""
    count = {}
    text, count['inset'] = re.subn(r'(^|[;{\s])inset\s*:\s*([^;}!]+?)\s*(!important)?\s*(?=[;}])', expand_inset, text)
    text, count[':focus-visible'] = re.subn(r':focus-visible', ':focus', text)
    return text, count


def css_findings(css_text, name):
    errors, warnings = [], []
    clean = strip_css_comments(css_text)
    for pattern, label in CSS_BLOCKERS:
        for m in re.finditer(pattern, clean):
            errors.append(name + ' : ' + label + ' → « ' + clean[max(0, m.start() - 30):m.end() + 20].strip() + ' »')
            break
    for pattern, label in CSS_ACCEPTED:
        if re.search(pattern, clean):
            warnings.append(name + ' : ' + label + ' ignoré par Chromium 76 (accepté)')
    return errors, warnings


def gap_selectors(css_texts):
    """Sélecteurs des règles qui déclarent un gap non nul (pour app/compat-tizen6.js)."""
    found = []
    for text in css_texts:
        text = strip_css_comments(text)
        for m in re.finditer(r'([^{}@;]+)\{([^{}]*)\}', text):
            body = m.group(2)
            if not re.search(r'(?<![\w-])(?:row-|column-)?gap\s*:\s*(?!0(?:px)?\s*[;}]|0(?:px)?\s*$)', body + ';'):
                continue
            for selector in m.group(1).split(','):
                selector = selector.strip()
                if selector and '::' not in selector and not selector.startswith(('from', 'to')) and not re.match(r'^\d', selector):
                    if selector not in found:
                        found.append(selector)
    return found


def overlay_config(source, cfg, ident, required_version):
    """config.xml de l'auteur + identité propre à Alexis + version de plateforme Tizen 6.0."""
    text = source
    replacements = [
        (r'(<widget\b[^>]*\bid=")[^"]*(")', ident['widget_id']),
        (r'(<tizen:application\b[^>]*\bid=")[^"]*(")', ident['app']),
        (r'(<tizen:application\b[^>]*\bpackage=")[^"]*(")', ident['package']),
        (r'(<tizen:application\b[^>]*\brequired_version=")[^"]*(")', required_version),
        (r'(<name>)[^<]*(</name>)', ident['name']),
    ]
    for pattern, value in replacements:
        text, n = re.subn(pattern, lambda m: m.group(1) + value + m.group(2), text, count=1)
        if n != 1:
            raise Stop('config.xml de l\'auteur a changé de forme (motif introuvable : ' + pattern + '). Adapter ma-tv/build.py.')
    meta = '<tizen:metadata key="http://samsung.com/tv/metadata/devel.api.version" value="' + lib.get(cfg, 'api_version', '6.0') + '"/>'
    if 'devel.api.version' not in text:
        text = text.replace('</widget>', '  ' + meta + '\n</widget>')
    root = XML.fromstring(text)
    app_node = root.find('t:application', NS)
    if app_node.get('id') != ident['app'] or app_node.get('required_version') != required_version:
        raise Stop('Vérification du config.xml généré en échec.')
    return text


STATIC_FONTS = lib.ROOT / 'ma-tv/assets/fonts'


def static_fonts(stage, warnings):
    """Polices variables → graisses fixes (Chromium 76 ignore les variations ; voir ma-tv/tools/static-fonts.py)."""
    target = stage / 'assets/fonts/ma-tv-static'
    target.mkdir(parents=True, exist_ok=True)
    for path in STATIC_FONTS.iterdir():
        shutil.copyfile(path, target / path.name)
    recorded = json.loads((STATIC_FONTS / 'SOURCES.json').read_text())['generated_from_sha256']
    for source, digest in recorded.items():
        if hashlib.sha256((lib.ROOT / source).read_bytes()).hexdigest() != digest:
            warnings.append(source + ' a changé en amont : relancer ma-tv/tools/static-fonts.py (graisses fixes périmées)')
    fonts_css = stage / 'assets/fonts.css'
    text, n = re.subn(r'@font-face\{font-family:Manrope;[^}]*\}', lambda m: ''.join(
        '@font-face{font-family:Manrope;src:url(fonts/ma-tv-static/manrope-%d.woff2) format("woff2");font-weight:%d;font-display:swap}' % (w, w)
        for w in (400, 500, 600)), fonts_css.read_text())
    if n != 1:
        raise Stop('assets/fonts.css de l\'auteur a changé (règle Manrope introuvable). Adapter ma-tv/build.py.')
    fonts_css.write_text(text)
    faces = stage / 'assets/typefaces.css'
    text = faces.read_text()
    rule = re.search(r"@font-face\{font-family:'Study Geist';[^}]*\}", text)
    if rule:
        static = ''.join(re.sub(r"font-weight:[^;]+;", 'font-weight:%d;' % w,
                                re.sub(r"src:url\([^)]*\)\s*format\([^)]*\)", "src:url('fonts/ma-tv-static/geist-%d.woff2') format('woff2')" % w, rule.group(0)))
                         for w in (300, 400))
        faces.write_text(text.replace(rule.group(0), static))
    # Fichiers variables devenus inutiles (plus référencés) : retirés du paquet.
    css = ''.join(p.read_text() for p in stage.rglob('*.css'))
    for name in ('assets/manrope.woff2', 'assets/fonts/geist/Geist-Variable.ttf'):
        if Path(name).name not in css and (stage / name).exists():
            (stage / name).unlink()


def write_local_config(stage, cfg):
    base = (APP / 'ma-tv-config.js').read_text()
    local = lib.get(cfg, 'local', {}) or {}
    extra = ('\n/* Généré par ma-tv/build.py depuis .local/ma-tv.json (section "local"). */\n'
             '(function (o) { Object.keys(o).forEach(function (k) { window.CleanFrameLocal[k] = o[k]; }); }('
             + json.dumps(local, ensure_ascii=False) + '));\n') if local else ''
    (stage / 'ma-tv-config.js').write_text(base + extra)


def git_revision():
    try:
        rev = subprocess.run(['git', '-C', str(lib.ROOT), 'rev-parse', '--short', 'HEAD'], text=True, capture_output=True).stdout.strip()
        dirty = subprocess.run(['git', '-C', str(lib.ROOT), 'status', '--porcelain', '--', 'app', 'ma-tv'], text=True, capture_output=True).stdout.strip()
        return rev + ('+modifs' if dirty else '')
    except OSError:
        return 'inconnu'


def build(required_version=None, check_only=False, quiet=False):
    cfg = lib.load_config()
    ident = lib.identity(cfg)
    required_version = required_version or lib.get(cfg, 'required_version', '6.0')
    source_config = (APP / 'config.xml').read_text()
    errors, warnings = gates(source_config)

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    files = []
    for path in sorted(APP.rglob('*')):
        name = path.relative_to(APP).as_posix()
        if path.is_symlink():
            raise Stop('Lien symbolique interdit dans app/ : ' + name)
        if path.is_file() and runtime_source(name):
            target = STAGE / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            files.append(name)

    # Adaptations Chromium 76 sur la copie.
    static_fonts(STAGE, warnings)
    conversions, css_texts = {}, []
    for name in [f for f in files if f.endswith('.css')]:
        text, count = adapt_css((STAGE / name).read_text())
        (STAGE / name).write_text(text)
        css_texts.append(text)
        for key, value in count.items():
            if value:
                conversions[name + ' ' + key] = value
        e, w = css_findings(text, name)
        errors += e; warnings += w
    selectors = gap_selectors(css_texts)
    (STAGE / 'ma-tv-gap.js').write_text('/* Généré par ma-tv/build.py : règles CSS avec gap, pour compat-tizen6.js. */\n'
                                        'window.CleanFrameGapSelectors = ' + json.dumps(selectors) + ';\n')
    write_local_config(STAGE, cfg)
    index = (STAGE / 'index.html').read_text()
    if index.count(INDEX_ANCHOR) != 1:
        raise Stop('index.html de l\'auteur a changé (ancre « ' + INDEX_ANCHOR + ' » introuvable). Adapter ma-tv/build.py.')
    (STAGE / 'index.html').write_text(index.replace(INDEX_ANCHOR, INJECT + INDEX_ANCHOR))
    (STAGE / 'config.xml').write_text(overlay_config(source_config, cfg, ident, required_version))
    for notice in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        shutil.copyfile(lib.ROOT / notice, STAGE / notice)

    version = XML.fromstring(source_config).get('version')
    report = {'version': version, 'source': git_revision(), 'app_id': ident['app'], 'required_version': required_version,
              'files': len(list(STAGE.rglob('*'))), 'css_conversions': conversions, 'gap_selectors': len(selectors),
              'errors': errors, 'warnings': warnings}
    if not quiet:
        for w in warnings:
            log('  attention : ' + w)
        for key, value in conversions.items():
            log('  converti : ' + key + ' ×' + str(value))
        log('  gap polyfill : ' + str(len(selectors)) + ' sélecteurs')
    if errors:
        for e in errors:
            log('  BARRIÈRE : ' + e)
        (lib.DIST / 'build.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        raise Stop(str(len(errors)) + ' barrière(s) franchie(s) : rien n\'est construit. Détails ci-dessus et dans dist/ma-tv/build.json.')
    if check_only:
        log('Barrières : OK (' + str(len(warnings)) + ' avertissement(s)).')
        return report
    output = lib.DIST / ('CleanFrame-' + version + '-tizen' + required_version + '-unsigned.wgt')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as package:
        for path in sorted(STAGE.rglob('*')):
            if path.is_file():
                package.write(path, path.relative_to(STAGE).as_posix())
    report['wgt'] = output.name
    report['sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    report['bytes'] = output.stat().st_size
    (lib.DIST / 'build.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    log('Paquet non signé : ' + str(output.relative_to(lib.ROOT)) + ' (' + str(report['bytes'] // 1024) + ' Ko, '
        + 'app ' + ident['app'] + ', Tizen ' + required_version + ')')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--required-version', help='valeur de required_version (test A/B, ex. 6.5)')
    parser.add_argument('--check-only', action='store_true', help='barrières et adaptations seulement, sans archive')
    args = parser.parse_args()
    lib.DIST.mkdir(parents=True, exist_ok=True)
    lib.main_guard(lambda: build(args.required_version, args.check_only))
