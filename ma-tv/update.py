"""ma-tv : LA commande de mise à jour — récupérer la version de l'auteur → tester → construire → signer → installer.

Entièrement automatique (choix d'Alexis), mais chaque étape est une barrière : au premier problème, tout
s'arrête ; la branche ma-tv et l'app installée restent intactes. Chaque commande vers la TV est affichée.

  1. git fetch de l'auteur (remote "upstream")
  2. rien de neuf chez l'auteur ET version installée = ma-tv → fin (sauf --rebuild)
  3. fusion dans une branche temporaire (merge, jamais de rebase ni de force-push) ; conflit → abandon propre
  4. barrières de build (privilèges, réseau, CSS/JS incompatibles avec Chromium 76, native-home…)
  5. recette Chromium 76 + Chrome de référence sur le paquet construit
  6. contrôle anti-fuite (avant toute signature ou publication), signature (même certificat auteur)
  7. TV : garde-fou d'identité, installation en place (préférences conservées), lancement, vérification
     → échec avec l'app absente ou qui ne se lance pas : réinstallation de la dernière version validée
  8. SEULEMENT si la TV a validé : avance de ma-tv, état enregistré, push sur le fork
  Si la TV est éteinte : rien n'avance ; le `maj` suivant refait tout.

Usage : python3 ma-tv/update.py [--dry-run] [--rebuild] [--confirm] [--skip-tv] [--skip-tests] [--no-push]
Raccourci : ma-tv/maj
"""
from datetime import datetime
from pathlib import Path
import argparse
import re
import subprocess

import lib
from lib import Stop, Cancelled, log
import build as builder
import sign as signer
from tv import TV

C = {'LC_ALL': 'C', 'LANG': 'C'}  # sorties git en anglais, quelle que soit la langue du Mac
# La branche porte le même nom que le dossier ma-tv/ : toujours la désigner sans ambiguïté.
BRANCH = 'refs/heads/ma-tv'


def git(*args, check=True, show=True, with_code=False):
    return lib.run(['git', '-C', str(lib.ROOT), '-c', 'core.quotepath=off', *args], check=check, show=show,
                   timeout=300, env=C, with_code=with_code)


def current_branch():
    return git('rev-parse', '--abbrev-ref', 'HEAD', show=False).strip()


def head(ref='HEAD'):
    return git('rev-parse', '--verify', ref, show=False).strip()


def preflight(cfg):
    if current_branch() != 'ma-tv':
        raise Stop('Se placer sur la branche ma-tv (git switch ma-tv).')
    dirty = git('status', '--porcelain', show=False).strip()
    if dirty:
        raise Stop('Modifications locales non commitées :\n' + dirty)
    if lib.get(cfg, 'upstream.remote') not in git('remote', show=False).split():
        raise Stop('Remote de l\'auteur absent : git remote add upstream https://github.com/nthnclrk/CleanFrame')
    if not lib.get(cfg, 'identity.package') or not lib.get(cfg, 'sign.author_sha256'):
        raise Stop('Première installation pas encore faite : la réaliser pas à pas (ma-tv/docs/procedure.md), '
                   'la mise à jour automatique prend le relais ensuite.')


SECRET_FILES = re.compile(r'\.(p12|pfx|pem|key|csr|pri|crt)$|(^|/)(profiles\.xml|device-profile\.xml|certificate-password\.txt|ma-tv\.json)$', re.I)
PRIVATE_KEY = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')


def leak_check(cfg, fork_ref):
    """Avant publication sur le fork public : aucune IP, aucun identifiant de TV/certificat, ni dans les fichiers
    suivis, ni dans l'historique et les messages des commits qui seront poussés."""
    secrets = [s for s in [lib.get(cfg, 'tv.host'), lib.get(cfg, 'tv.udn'), lib.get(cfg, 'mac_ip'),
                           lib.get(cfg, 'tv.remote_token'), lib.get(cfg, 'identity.package'),
                           (lib.get(cfg, 'tv.capability', {}) or {}).get('duid')] if s]
    profile_dir = Path.home() / 'SamsungCertificate' / str(lib.get(cfg, 'sign.profile'))
    device_profile = profile_dir / 'device-profile.xml'
    if device_profile.exists():  # DUID de la TV et autres valeurs du certificat distributeur
        secrets += [v.strip() for v in re.findall(r'>([0-9A-Za-z+/=]{12,})<', device_profile.read_text())]
    found = []
    for name in [n for n in git('ls-files', '-z', show=False).split('\0') if n]:
        path = lib.ROOT / name
        if SECRET_FILES.search(name):
            found.append(name + ' : fichier de certificat/configuration privée suivi par git')
        if not path.is_file():
            if not path.is_symlink():
                found.append(name + ' : suivi mais introuvable (vérifier)')
            continue
        if path.suffix.lower() in ('.jpg', '.png', '.woff2', '.ttf', '.zip', '.wgt'):
            continue
        text = path.read_text(errors='ignore')
        found += [name + ' contient « ' + s[:6] + '… »' for s in secrets if s in text]
        if PRIVATE_KEY.search(text):
            found.append(name + ' contient une clé privée')
    span = (fork_ref + '..' + BRANCH) if fork_ref else BRANCH
    history = git('log', '-p', '--format=%B', span, '--', show=False)
    found += ['historique (' + span + ') contient « ' + s[:6] + '… »' for s in secrets if s in history]
    if PRIVATE_KEY.search(history):
        found.append('historique (' + span + ') contient une clé privée')
    if found:
        raise Stop('Fuite évitée, rien n\'est publié :\n' + '\n'.join(found))


def run_tests(skip):
    if skip:
        log('Recette navigateur sautée (--skip-tests).')
        return
    log('Recette Chromium 76 + référence…')
    try:
        result = subprocess.run(['node', str(lib.ROOT / 'ma-tv/harness/run.mjs'), '--runs', '3', '--no-shots'],
                                text=True, capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired:
        raise Stop('Recette trop longue (> 30 min) : rien n\'est installé.')
    except FileNotFoundError:
        raise Stop('node introuvable : installer Node.js (recette impossible).')
    for line in (result.stdout + result.stderr).strip().splitlines()[-12:]:
        log('  ' + line)
    if result.returncode:
        raise Stop('La recette a échoué : la nouvelle version n\'est pas installée (rapport dans .local/qa/ma-tv/).')


def merge_upstream(upstream):
    """Fusion dans une branche temporaire ; renvoie son nom. Conflit → abandon complet, ma-tv intacte."""
    temp = 'ma-tv-maj-' + datetime.now().strftime('%Y%m%d-%H%M%S')
    git('switch', '-c', temp)
    code, out = git('merge', '--no-ff', '--no-edit', '-m', 'ma-tv : fusion de la version de l\'auteur (' + upstream + ')',
                    upstream, check=False, with_code=True)
    unmerged = git('diff', '--name-only', '--diff-filter=U', show=False).strip()
    pending = git('rev-parse', '-q', '--verify', 'MERGE_HEAD', check=False, show=False).strip()
    if code or unmerged or pending:
        git('merge', '--abort', check=False)
        git('switch', 'ma-tv', check=False)
        git('branch', '-D', temp, check=False)
        raise Stop('Fusion impossible automatiquement, rien n\'est changé (ma-tv intacte). Fichiers : '
                   + (unmerged.replace('\n', ', ') or '?') + '. Résoudre à la main : ma-tv/docs/procedure.md, « Conflit de mise à jour ».')
    return temp


def update(args):
    cfg = lib.load_config()
    preflight(cfg)
    upstream = lib.get(cfg, 'upstream.remote') + '/' + lib.get(cfg, 'upstream.branch')
    git('fetch', lib.get(cfg, 'upstream.remote'))
    news = git('log', '--oneline', BRANCH + '..' + upstream, '--', show=False).strip()
    installed = lib.get(cfg, 'tv.installed_commit')
    pending_install = installed != head(BRANCH)
    if news:
        log('Nouveautés de l\'auteur :\n' + news)
        git('diff', '--stat', BRANCH + '...' + upstream, '--')
    elif pending_install:
        log('ma-tv (' + head(BRANCH)[:8] + ') n\'est pas encore installée sur la TV (installée : ' + str(installed)[:8] + ') : installation.')
    elif not args.rebuild:
        log('Rien de nouveau : la TV a déjà la dernière version. (--rebuild pour reconstruire et réinstaller.)')
        return
    if args.dry_run:
        log('--dry-run : aucune fusion, aucun build, rien vers la TV.')
        return

    temp, done = merge_upstream(upstream) if news else None, False
    try:
        builder.build()
        run_tests(args.skip_tests)
        fork = lib.get(cfg, 'fork.remote')
        push = lib.get(cfg, 'fork.push') and not args.no_push
        remotes = git('remote', show=False).split()
        fork_ref = None
        if push and fork in remotes:
            exists = git('rev-parse', '-q', '--verify', 'refs/remotes/' + fork + '/ma-tv', check=False, show=False).strip()
            fork_ref = fork + '/ma-tv' if exists else None
            leak_check(cfg, fork_ref)  # avant de signer : un état propre ou rien
        signer.sign()
        if args.skip_tv:
            log('TV non touchée (--skip-tv). Le prochain `ma-tv/maj` installera cette version.')
        else:
            install_and_verify(args)
        done = True
    finally:
        if temp and not done:
            git('switch', 'ma-tv', check=False)
            git('branch', '-D', temp, check=False)
            log('Branche temporaire supprimée : ma-tv inchangée.')
    if temp:
        git('switch', 'ma-tv')
        git('merge', '--ff-only', temp)
        git('branch', '-d', temp)
    if not args.skip_tv:
        lib.save_local({'tv': {'installed_commit': head(BRANCH)}})
    publish(cfg, args)
    log('Mise à jour terminée' + ('' if args.skip_tv else ' et installée') + '. Vérifier l\'écran de la TV.')


def install_and_verify(args):
    tv = TV(argparse.Namespace(yes=not args.confirm))
    try:
        tv.install()
        tv.launch()
    except Cancelled:
        raise
    except Stop as error:
        if tv.installed() and 'Lancement' not in str(error):
            raise  # l'installation a été refusée : l'ancienne version, valide, est toujours là
        log('Échec après installation (' + str(error) + ') : retour à la dernière version validée.')
        tv.rollback()
        raise
    tv.mark_good()


def publish(cfg, args):
    fork = lib.get(cfg, 'fork.remote')
    if args.no_push or not lib.get(cfg, 'fork.push'):
        return
    if fork not in git('remote', show=False).split():
        log('ATTENTION : fork « ' + fork + ' » non configuré, rien n\'est publié (git remote add ' + fork + ' <url du fork>).')
        return
    exists = git('rev-parse', '-q', '--verify', 'refs/remotes/' + fork + '/ma-tv', check=False, show=False).strip()
    leak_check(cfg, fork + '/ma-tv' if exists else None)
    code, _ = git('push', fork, 'ma-tv', check=False, with_code=True)
    if code:
        log('ATTENTION : fork NON mis à jour (push refusé, voir ci-dessus). La TV, elle, est à jour.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help='montrer les nouveautés sans rien changer')
    parser.add_argument('--rebuild', action='store_true', help='reconstruire et réinstaller même sans nouveauté')
    parser.add_argument('--confirm', action='store_true', help='demander confirmation avant chaque commande vers la TV')
    parser.add_argument('--skip-tv', action='store_true', help='s\'arrêter après la signature')
    parser.add_argument('--skip-tests', action='store_true', help='sauter la recette navigateur (déconseillé)')
    parser.add_argument('--no-push', action='store_true', help='ne pas publier sur le fork')
    args = parser.parse_args()
    lib.main_guard(lambda: update(args))
