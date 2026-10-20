"""ma-tv : LA commande de mise à jour — récupérer la version de l'auteur → tester → construire → signer → installer.

Entièrement automatique (choix d'Alexis), mais chaque étape est une barrière : au premier problème, tout
s'arrête, la branche ma-tv et l'app installée restent intactes. Chaque commande vers la TV est affichée.

  1. git fetch de l'auteur (remote "upstream") ; rien de neuf → fin (sauf --rebuild)
  2. fusion dans une branche temporaire (merge, jamais de rebase ni de force-push) ; conflit → abandon
  3. barrières de build (privilèges, réseau, CSS/JS incompatibles avec Chromium 76, native-home…)
  4. recette Chromium 76 + Chrome de référence sur le paquet construit ; échec → abandon
  5. avance de ma-tv, push sur le fork (après contrôle anti-fuite)
  6. signature (même certificat auteur, certificats valides)
  7. TV : garde-fou d'identité, installation en place (préférences conservées), lancement, vérification
     → en cas d'échec après l'installation : réinstallation automatique de la version précédente

Usage : python3 ma-tv/update.py [--dry-run] [--rebuild] [--confirm] [--skip-tv] [--skip-tests] [--no-push]
Raccourci : ma-tv/maj
"""
from datetime import datetime
import argparse
import re
import subprocess

import lib
from lib import Stop, log
import build as builder
import sign as signer
from tv import TV


def git(*args, check=True, show=True):
    return lib.run(['git', '-C', str(lib.ROOT), *args], check=check, show=show, timeout=300)


def current_branch():
    return git('rev-parse', '--abbrev-ref', 'HEAD', show=False).strip()


def preflight(cfg):
    if current_branch() != 'ma-tv':
        raise Stop('Se placer sur la branche ma-tv (git switch ma-tv).')
    dirty = git('status', '--porcelain', show=False).strip()
    if dirty:
        raise Stop('Modifications locales non commitées :\n' + dirty)
    remotes = git('remote', show=False).split()
    if lib.get(cfg, 'upstream.remote') not in remotes:
        raise Stop('Remote de l\'auteur absent : git remote add upstream https://github.com/nthnclrk/CleanFrame')


def leak_check(cfg):
    """Avant de publier sur le fork public : aucune IP, aucun identifiant de TV ou de certificat dans le code suivi."""
    tracked = git('ls-files', show=False).split()
    secrets = [s for s in [lib.get(cfg, 'tv.host'), lib.get(cfg, 'tv.udn'), lib.get(cfg, 'mac_ip'),
                           (lib.get(cfg, 'tv.capability', {}) or {}).get('duid')] if s]
    found = []
    for name in tracked:
        path = lib.ROOT / name
        if path.suffix.lower() in ('.jpg', '.png', '.woff2', '.ttf', '.zip') or not path.is_file():
            continue
        text = path.read_text(errors='ignore')
        found += [name + ' contient « ' + s[:6] + '… »' for s in secrets if s in text]
        if re.search(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', text):
            found.append(name + ' contient une clé privée')
    if found:
        raise Stop('Fuite évitée, rien n\'est poussé :\n' + '\n'.join(found))


def run_tests(skip):
    if skip:
        log('Recette navigateur sautée (--skip-tests).')
        return
    log('Recette Chromium 76 + référence…')
    result = subprocess.run(['node', str(lib.ROOT / 'ma-tv/harness/run.mjs'), '--runs', '3', '--no-shots'], text=True, capture_output=True, timeout=1800)
    tail = (result.stdout + result.stderr).strip().splitlines()
    for line in tail[-12:]:
        log('  ' + line)
    if result.returncode:
        raise Stop('La recette a échoué : la nouvelle version n\'est pas installée (rapport dans .local/qa/ma-tv/).')


def update(args):
    cfg = lib.load_config()
    preflight(cfg)
    upstream = lib.get(cfg, 'upstream.remote') + '/' + lib.get(cfg, 'upstream.branch')
    git('fetch', lib.get(cfg, 'upstream.remote'))
    news = git('log', '--oneline', 'ma-tv..' + upstream, show=False).strip()
    if news:
        log('Nouveautés de l\'auteur :\n' + news)
        git('diff', '--stat', 'ma-tv...' + upstream)
    elif not args.rebuild:
        log('Rien de nouveau chez l\'auteur. (--rebuild pour reconstruire et réinstaller quand même.)')
        return
    if args.dry_run:
        log('--dry-run : aucune fusion, aucun build, rien vers la TV.')
        return

    temp = None
    if news:
        temp = 'ma-tv-maj-' + datetime.now().strftime('%Y%m%d-%H%M%S')
        git('switch', '-c', temp)
        merged = git('merge', '--no-ff', '--no-edit', '-m', 'ma-tv : fusion de la version de l\'auteur (' + upstream + ')', upstream, check=False)
        if 'CONFLICT' in merged or 'Automatic merge failed' in merged:
            conflicts = git('diff', '--name-only', '--diff-filter=U', show=False).strip()
            git('merge', '--abort', check=False)
            git('switch', 'ma-tv')
            git('branch', '-D', temp)
            raise Stop('Conflit de fusion, rien n\'est changé (ma-tv intacte). Fichiers : ' + conflicts.replace('\n', ', ')
                       + '. Résoudre à la main (ma-tv/docs/procedure.md, « Conflit de mise à jour »).')
    try:
        builder.build()
        run_tests(args.skip_tests)
    except Stop:
        if temp:
            git('switch', 'ma-tv')
            git('branch', '-D', temp)
            log('Branche temporaire supprimée : ma-tv et la TV sont inchangées.')
        raise
    if temp:
        git('switch', 'ma-tv')
        git('merge', '--ff-only', temp)
        git('branch', '-d', temp)
    if not args.no_push and lib.get(cfg, 'fork.push') and lib.get(cfg, 'fork.remote') in git('remote', show=False).split():
        leak_check(cfg)
        git('push', lib.get(cfg, 'fork.remote'), 'ma-tv', check=False)
    signer.sign()
    if args.skip_tv:
        log('TV non touchée (--skip-tv). Installer plus tard : python3 ma-tv/tv.py install')
        return
    tv = TV(argparse.Namespace(yes=not args.confirm))
    tv.install()
    try:
        tv.launch()
        if not tv.installed():
            raise Stop('App absente après installation.')
    except Stop as error:
        log('Échec après installation (' + str(error) + ') : retour automatique à la version précédente.')
        tv.rollback()
        raise
    log('Mise à jour terminée et installée. Vérifier l\'écran de la TV.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help='montrer les nouveautés sans rien changer')
    parser.add_argument('--rebuild', action='store_true', help='reconstruire et réinstaller même sans nouveauté')
    parser.add_argument('--confirm', action='store_true', help='demander confirmation avant chaque commande vers la TV')
    parser.add_argument('--skip-tv', action='store_true', help='s\'arrêter après la signature')
    parser.add_argument('--skip-tests', action='store_true', help='sauter la recette navigateur (déconseillé)')
    parser.add_argument('--no-push', action='store_true', help='ne pas pousser sur le fork')
    args = parser.parse_args()
    lib.main_guard(lambda: update(args))
