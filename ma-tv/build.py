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
from xml.sax.saxutils import escape

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
# convertir automatiquement : leur apparition en amont arrête la mise à jour. Les propriétés sont ancrées sur
# une position de déclaration (après { ou ;) pour ne pas confondre avec un nom de classe ou une condition @media.
DECL = r'(?:^|[;{])\s*'
CSS_BLOCKERS = [
    (DECL + r'aspect-ratio\s*:', 'aspect-ratio (Chrome 88)'),
    (DECL + r'inset-(?:inline|block)(?:-start|-end)?\s*:', 'inset-inline/block (Chrome 87)'),
    (DECL + r'(?:margin|padding|border|scroll-margin|scroll-padding)-(?:inline|block)(?:-start|-end)?(?:-\w+)?\s*:', 'propriétés logiques inline/block (Chrome 87)'),
    (DECL + r'(?:translate|rotate|scale)\s*:', 'propriétés translate/rotate/scale (Chrome 104)'),
    (DECL + r'accent-color\s*:', 'accent-color (Chrome 93)'),
    (DECL + r'content-visibility\s*:', 'content-visibility (Chrome 85)'),
    (DECL + r'overflow(?:-[xy])?\s*:\s*clip', 'overflow: clip (Chrome 90)'),
    (DECL + r'container(?:-type|-name)?\s*:', 'container queries (Chrome 105)'),
    (DECL + r'scrollbar-gutter\s*:', 'scrollbar-gutter (Chrome 94)'),
    (DECL + r'text-(?:decoration-thickness|underline-offset)\s*:', 'text-decoration-thickness/underline-offset (Chrome 87)'),
    (DECL + r'inset\s*:', 'inset (Chrome 87) non converti (valeur complexe)'),
    (DECL + r'display\s*:\s*(?:inline|block)\s+(?:flex|grid|flow-root)', 'display à deux valeurs (Chrome 115)'),
    (r'@container|@layer|@property|@scope|@starting-style|@supports\s+selector\(', 'règle @ récente'),
    (r'@media[^{]*(?:[<>]=?|\(\s*(?:width|height)\s*[<>])', 'requête média par intervalle (Chrome 104)'),
    (r':(?:is|where|has)\(', 'sélecteur :is/:where/:has (Chrome 88+)'),
    (r':not\([^)]*,', ':not() avec liste (Chrome 88) : règle entière ignorée'),
    (r'::marker', '::marker (Chrome 86)'),
    (r':focus-visible', ':focus-visible (Chrome 86)'),
    (r'(?<![\w-])(?:clamp|min|max|round|mod|rem)\(', 'clamp()/min()/max()/round() (Chrome 79-125)'),
    (r'(?<![\w-])(?:color-mix|lab|lch|oklab|oklch|hwb|light-dark)\(', 'couleurs CSS Color 4/5'),
    (r'(?<![\w-])image-set\(', 'image-set() sans préfixe (Chrome 113)'),
    (r'\d(?:dvh|svh|lvh|dvw|svw|lvw|cqw|cqh|cqi|cqb)\b', 'unités viewport dynamiques / conteneur'),
    (r'&\s*[.:#\[>~+]', 'imbrication CSS (Chrome 112)'),
]
# Dans une même règle, la version sans préfixe exige la version -webkit- (seule comprise par Chromium 76).
CSS_PREFIX_NEEDED = [
    (r'(?<![\w-])mask(?:-image|-size|-repeat|-position|-mode)?\s*:', r'-webkit-mask', 'mask sans -webkit-mask (Chrome 120)'),
    (r'(?<![\w-])background-clip\s*:\s*text', r'-webkit-background-clip\s*:\s*text', 'background-clip:text sans préfixe (Chrome 120)'),
]
# Ignorées sans effet visible majeur en Chromium 76 (polices optionnelles) : signalées, acceptées.
CSS_ACCEPTED = [
    (DECL + r'size-adjust\s*:', 'size-adjust (Chrome 92)'),
    (DECL + r'(?:ascent|descent|line-gap)-override\s*:', '*-override (Chrome 87)'),
    (DECL + r'font-synthesis\s*:', 'font-synthesis (Chrome 97)'),
    (DECL + r'font-optical-sizing\s*:', 'font-optical-sizing (Chrome 79)'),
]
# Éléments de config.xml acceptés (ceux de l'auteur aujourd'hui). Tout autre élément (service, app-control,
# catégorie de fond…) change la nature de l'app et arrête le build.
CONFIG_ELEMENTS = {'{%s}%s' % (NS['w'], n) for n in ('name', 'icon', 'content', 'feature', 'description', 'author', 'license')} | \
                  {'{%s}%s' % (NS['t'], n) for n in ('application', 'profile', 'privilege', 'setting', 'metadata')}
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
          '<script src="ma-tv-config.js"></script>\n<script src="ma-tv-locale.js"></script>\n<script src="ma-tv-gap.js"></script>\n<script src="compat-tizen6.js"></script>\n')


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


REGEX_BEFORE = set('(,=:[!&|?{};+-*%<>~^') | {''}
REGEX_KEYWORDS = {'return', 'typeof', 'case', 'do', 'else', 'in', 'of', 'new', 'delete', 'void', 'throw', 'instanceof', 'yield', 'await'}


def strip_js(text, name='?'):
    """Code JavaScript sans commentaires, chaînes ni littéraux regex (vidés), pour les barrières.

    Reconnaît les regex d'après le jeton précédent (après un opérateur, une ponctuation ou un mot-clé comme
    return). Si l'analyse se désynchronise (chaîne simple qui traverse une fin de ligne), le build s'arrête :
    mieux vaut un faux arrêt qu'un code non inspecté.
    """
    out, i, n = [], 0, len(text)
    prev = ''  # dernier jeton significatif (caractère de ponctuation ou mot)
    while i < n:
        c = text[i]
        if c in ' \t\r\n':
            out.append(c); i += 1; continue
        if text.startswith('//', i):
            j = text.find('\n', i); i = n if j < 0 else j; continue
        if text.startswith('/*', i):
            j = text.find('*/', i + 2); i = n if j < 0 else j + 2; continue
        if c in '\'"':
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == '\n':
                    raise Stop(name + ' : analyse JS désynchronisée (chaîne ouverte ligne ' + str(text.count('\n', 0, i) + 1) + ').')
                j += 2 if text[j] == '\\' else 1
            out.append(c + c); i = j + 1; prev = 'x'; continue
        if c == '`':
            j = i + 1
            while j < n and text[j] != '`':
                if text.startswith('${', j):
                    raise Stop(name + ' : gabarit `${…}` non analysé par les barrières (ligne ' + str(text.count('\n', 0, j) + 1) + ').')
                j += 2 if text[j] == '\\' else 1
            out.append('``'); i = j + 1; prev = 'x'; continue
        if c == '/' and (prev in REGEX_BEFORE or prev in REGEX_KEYWORDS):
            j, in_class = i + 1, False
            while j < n:
                ch = text[j]
                if ch == '\\':
                    j += 2; continue
                if ch == '\n':
                    raise Stop(name + ' : littéral regex non terminé ligne ' + str(text.count('\n', 0, i) + 1) + '.')
                if ch == '[':
                    in_class = True
                elif ch == ']':
                    in_class = False
                elif ch == '/' and not in_class:
                    break
                j += 1
            j += 1
            while j < n and text[j].isalpha():
                j += 1
            out.append('/r/'); i = j; prev = 'x'; continue
        m = re.match(r'[A-Za-z_$][\w$]*', text[i:i + 64])
        if m:
            out.append(m.group(0)); i += len(m.group(0)); prev = m.group(0); continue
        out.append(c); i += 1
        prev = c if not c.isalnum() else 'x'
        if c in ')]':
            prev = 'x'  # après ) ou ], un / est une division
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
    unknown = sorted({child.tag for child in root} - CONFIG_ELEMENTS)
    if unknown:
        errors.append('config.xml : élément(s) non prévu(s) (accès réseau, service, app-control… ?) : ' + ', '.join(unknown))
    content = root.find('w:content', NS)
    if content is None or content.get('src') != 'index.html':
        errors.append('config.xml : <content src> doit rester « index.html » (pas de page distante).')
    for setting in root.findall('t:setting', NS):
        if setting.get('background-support', 'disable') != 'disable':
            errors.append('config.xml : background-support activé par l\'amont.')
    for path in sorted(APP.rglob('*')):
        name = path.relative_to(APP).as_posix()
        if not path.is_file() or not runtime_source(name) or path.suffix not in ('.js', '.html', '.css'):
            continue
        text = path.read_text(errors='replace')
        for url in re.findall(r'https?://[^\s"\'<>)]+', text):
            if not URL_ALLOW.match(url):
                errors.append(name + ' : adresse réseau ' + url)
        if path.suffix == '.html':
            if re.search(r'<script(?![^>]*\bsrc=)[^>]*>', text) or re.search(r'<style\b|\sstyle\s*=', text):
                errors.append(name + ' : script ou style en ligne, non couvert par les barrières (à déplacer dans un fichier).')
            if NETWORK.search(text):
                errors.append(name + ' : appel réseau (' + NETWORK.search(text).group(0) + ')')
        if path.suffix == '.js':
            try:
                code = strip_js(text, name)
            except Stop as stop:
                errors.append(str(stop)); continue
            if NETWORK.search(code):
                errors.append(name + ' : appel réseau (' + NETWORK.search(code).group(0) + ')')
            for pattern, label in JS_BLOCKERS:
                if re.search(pattern, code):
                    errors.append(name + ' : ' + label)
            if re.search(r'(?<![\w-])mask-image', text) and '-webkit-mask-image' not in text:
                errors.append(name + ' : mask-image sans -webkit-mask-image (icônes invisibles en Chromium 76)')
    return errors, warnings


def expand_inset(match):
    # Valeur avec fonction (calc, var, env…) : pas de découpage hasardeux, la barrière « inset non converti » arrêtera.
    if '(' in match.group(2):
        return match.group(0)
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
    (pas de souris sur la TV : le focus vient toujours de la télécommande). Les commentaires sont retirés
    d'abord, pour ne jamais réécrire leur texte."""
    count = {}
    text = strip_css_comments(text)
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
    for body in re.findall(r'\{([^{}]*)\}', clean):
        for pattern, prefixed, label in CSS_PREFIX_NEEDED:
            if re.search(pattern, body) and not re.search(prefixed, body):
                errors.append(name + ' : ' + label + ' → « ' + body.strip()[:80] + ' »')
    for pattern, label in CSS_ACCEPTED:
        if re.search(pattern, clean):
            warnings.append(name + ' : ' + label + ' ignoré par Chromium 76 (accepté)')
    return errors, warnings


def pseudo_gap_rules(css_texts, selectors):
    """Pseudo-éléments ::before/::after dans le flux d'un conteneur flex à gap : le polyfill JS ne peut pas leur
    donner de marge ; on génère la règle CSS équivalente, active seulement quand le polyfill l'est."""
    rules, gaps = [], {}
    for text in css_texts:
        for m in re.finditer(r'([^{}@;]+)\{([^{}]*)\}', text):
            body = m.group(2)
            g = re.search(r'(?<![\w-])(?:column-)?gap\s*:\s*([\d.]+px)', body)
            if g:
                for sel in m.group(1).split(','):
                    gaps[sel.strip()] = (g.group(1), 'column' in (re.search(r'flex-direction\s*:\s*([\w-]+)', body) or [None, ''])[1])
    # Toutes les déclarations de chaque pseudo-élément, toutes règles confondues.
    bodies = {}
    for text in css_texts:
        for m in re.finditer(r'([^{}@;]+)\{([^{}]*)\}', text):
            for sel in m.group(1).split(','):
                bodies.setdefault(sel.strip(), []).append(m.group(2))
    for sel, parts in bodies.items():
        host = re.match(r'^(.*?)::?(before|after)$', sel)
        body = ';'.join(parts)
        # Rendu seulement avec un content ; hors flux si absolu/fixe ou masqué.
        if not host or host.group(1) not in gaps or 'content' not in body or re.search(r'position\s*:\s*(?:absolute|fixed)|display\s*:\s*none', body):
            continue
        gap, column = gaps[host.group(1)]
        side = ('margin-top' if column else 'margin-left') if host.group(2) == 'after' else ('margin-bottom' if column else 'margin-right')
        rules.append('html.cf-no-flexgap ' + sel + '{' + side + ':' + gap + '}')
    return rules


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
    text = source.lstrip('﻿')
    api = lib.get(cfg, 'api_version', '6.0')
    attr = lambda v: escape(v, {'"': '&quot;'})
    replacements = [
        (r'(<widget\b[^>]*\bid=")[^"]*(")', attr(ident['widget_id'])),
        (r'(<tizen:application\b[^>]*\bid=")[^"]*(")', attr(ident['app'])),
        (r'(<tizen:application\b[^>]*\bpackage=")[^"]*(")', attr(ident['package'])),
        (r'(<tizen:application\b[^>]*\brequired_version=")[^"]*(")', attr(required_version)),
        (r'(<name>)[^<]*(</name>)', escape(ident['name'])),
    ]
    for pattern, value in replacements:
        text, n = re.subn(pattern, lambda m: m.group(1) + value + m.group(2), text, count=1)
        if n != 1:
            raise Stop('config.xml de l\'auteur a changé de forme (motif introuvable : ' + pattern + '). Adapter ma-tv/build.py.')
    meta = r'(<tizen:metadata\b[^>]*key="http://samsung\.com/tv/metadata/devel\.api\.version"[^>]*\bvalue=")[^"]*(")'
    text, n = re.subn(meta, lambda m: m.group(1) + attr(api) + m.group(2), text)
    if n == 0:
        text = text.replace('</widget>', '  <tizen:metadata key="http://samsung.com/tv/metadata/devel.api.version" value="' + attr(api) + '"/>\n</widget>')
    try:
        root = XML.fromstring(text)
    except XML.ParseError as error:
        raise Stop('config.xml généré illisible (' + str(error) + ').')
    app_node = root.find('t:application', NS)
    metas = [m.get('value') for m in root.findall('t:metadata', NS) if m.get('key', '').endswith('devel.api.version')]
    if (root.get('id') != ident['widget_id'] or app_node.get('id') != ident['app'] or app_node.get('package') != ident['package']
            or app_node.get('required_version') != required_version or root.find('w:name', NS).text != ident['name'] or metas != [api]):
        raise Stop('Vérification du config.xml généré en échec (identité, version de plateforme ou devel.api.version).')
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
    if not rule:
        raise Stop('assets/typefaces.css de l\'auteur a changé (règle Study Geist introuvable). Adapter ma-tv/build.py.')
    static = ''.join(re.sub(r"font-weight:[^;}]+", 'font-weight:%d' % w,
                            re.sub(r"src:url\([^)]*\)\s*format\([^)]*\)", "src:url('fonts/ma-tv-static/geist-%d.woff2') format('woff2')" % w, rule.group(0)))
                     for w in (300, 400))
    text = text.replace(rule.group(0), static)
    if 'geist-300.woff2' not in text or 'geist-400.woff2' not in text or 'Geist-Variable.ttf' in text:
        raise Stop('Conversion de Geist en graisses fixes incomplète. Adapter ma-tv/build.py.')
    faces.write_text(text)
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
    """Construit le paquet. Toute erreur due à un changement de forme en amont devient un arrêt propre."""
    try:
        return _build(required_version, check_only, quiet)
    except (OSError, XML.ParseError, TypeError, KeyError, ValueError, AttributeError) as error:
        raise Stop('L\'amont a changé de forme (' + type(error).__name__ + ' : ' + str(error) + ') : adapter ma-tv/build.py.')


def _build(required_version=None, check_only=False, quiet=False):
    cfg = lib.load_config()
    ident = lib.identity(cfg, create=True)
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
    pseudo = pseudo_gap_rules(css_texts, selectors)
    if pseudo:
        with open(STAGE / 'style.css', 'a') as css:
            css.write('\n/* ma-tv : marges des pseudo-éléments flex (polyfill gap, Chromium 76) */\n' + '\n'.join(pseudo) + '\n')
        conversions['style.css pseudo-éléments gap'] = len(pseudo)
    (STAGE / 'ma-tv-gap.js').write_text('/* Généré par ma-tv/build.py : règles CSS avec gap, pour compat-tizen6.js. */\n'
                                        'window.CleanFrameGapSelectors = ' + json.dumps(selectors) + ';\n')
    write_local_config(STAGE, cfg)
    index = (STAGE / 'index.html').read_text()
    if index.count(INDEX_ANCHOR) != 1:
        raise Stop('index.html de l\'auteur a changé (ancre « ' + INDEX_ANCHOR + ' » introuvable). Adapter ma-tv/build.py.')
    css_anchor = '<link rel="stylesheet" href="style.css">'
    if index.count(css_anchor) != 1:
        raise Stop('index.html de l\'auteur a changé (ancre « ' + css_anchor + ' » introuvable). Adapter ma-tv/build.py.')
    index = index.replace(css_anchor, css_anchor + '\n<link rel="stylesheet" href="ma-tv.css"><!-- ma-tv -->')
    (STAGE / 'index.html').write_text(index.replace(INDEX_ANCHOR, INJECT + INDEX_ANCHOR))
    (STAGE / 'config.xml').write_text(overlay_config(source_config, cfg, ident, required_version))
    for notice in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        shutil.copyfile(lib.ROOT / notice, STAGE / notice)

    version = XML.fromstring(source_config).get('version')
    commit = subprocess.run(['git', '-C', str(lib.ROOT), 'rev-parse', 'HEAD'], text=True, capture_output=True).stdout.strip()
    report = {'version': version, 'source': git_revision(), 'commit': commit if not git_revision().endswith('+modifs') else None, 'app_id': ident['app'], 'required_version': required_version,
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
