"""ma-tv : commandes vers la TV (sdb et CLI officiels Samsung), toujours affichées avant exécution.

Par défaut, chaque action qui touche la TV attend un « o » ; --yes l'exécute directement (utilisé par
update.py, la mise à jour automatique). Dans chaque processus, avant la première commande sdb : garde-fou
d'identité (modèle, appareil, mode développeur pointé sur ce Mac) via la lecture seule :8001/api/v2/.

Actions :
  info          lecture seule de :8001/api/v2/ (aucun sdb)
  connect       sdb connect <TV>:26101
  capability    version de plateforme, architecture… (enregistrée dans .local/ma-tv.json)
  applist       applis installées et leurs IDs (enregistrées dans .local/tv-applist.txt)
  permit        autorisation d'installation (profil distributeur) — « Permit to install applications »
  install       installe le dernier paquet signé (tizen install, repli vd_appinstall)
  launch        lance CleanFrame ; après une installation, marque cette version comme « validée »
  debug         lance en mode inspecteur et ouvre le tunnel DevTools (pour la recette sur TV)
  uninstall     désinstalle CleanFrame (tizen uninstall, repli vd_appuninstall)
  rollback      réinstalle la dernière version validée (.local/releases)
  disconnect    ferme la connexion sdb
"""
from pathlib import Path
import argparse
import os
import select
import signal
import subprocess
import json
import re
import time

import lib
from lib import Stop, Cancelled, log

ACTIONS = ['info', 'connect', 'capability', 'applist', 'permit', 'install', 'launch', 'debug', 'uninstall', 'rollback', 'disconnect']
# Le CLI Samsung peut afficher « successfully installed » même après un refus : ces marques l'emportent.
INSTALL_FAILED = re.compile(r'install failed|cmd_ret:\s*-\d|val\[(?:fail|-\d+)\]|Check certificate error|not permitted|Failed to', re.I)


class TV:
    def __init__(self, args):
        self.args = args
        self.cfg = lib.load_config()
        self.serial = lib.serial(self.cfg)
        self.app_id = lib.identity(self.cfg)['app']  # lecture seule : jamais d'identité inventée ici
        self.checked = False

    def sdb(self, *command, timeout=60, check=True, with_code=False):
        return lib.run([lib.sdk_tool(self.cfg, 'sdb'), '-s', self.serial, *command], timeout=timeout, check=check, with_code=with_code)

    def tizen(self, *command, timeout=180, check=True):
        return lib.run([lib.sdk_tool(self.cfg, 'tizen'), *command], timeout=timeout, check=check)

    def ok(self, what):
        if getattr(self.args, 'yes', False):
            log('→ ' + what)
            return
        answer = input('→ ' + what + '\n  Lancer cette commande vers la TV ? [o/N] ').strip().lower()
        if answer not in ('o', 'oui', 'y', 'yes'):
            raise Cancelled('Annulé : ' + what)

    def guard(self):
        if not self.checked:
            lib.guard_tv(self.cfg)
            self.checked = True

    # ---------- lecture seule ----------
    def info(self):
        device = lib.tv_api(self.cfg).get('device', {})
        for key in ['modelName', 'model', 'name', 'OS', 'firmwareVersion', 'resolution', 'networkType', 'developerMode',
                    'developerIP', 'FrameTVSupport', 'countryCode', 'PowerState']:
            log('  ' + key + ' : ' + str(device.get(key)))
        return device

    def connected(self):
        out = lib.run([lib.sdk_tool(self.cfg, 'sdb'), 'devices'], show=False, check=False)
        return any(line.split()[:2] == [self.serial, 'device'] for line in out.splitlines() if line.strip())

    def connect(self):
        self.guard()  # même si une connexion sdb existe déjà (ouverte par un autre outil ou une autre TV)
        if self.connected():
            return
        self.ok('sdb connect ' + self.serial + ' (ouvre la connexion développeur ; ne modifie rien sur la TV)')
        out = lib.run([lib.sdk_tool(self.cfg, 'sdb'), 'connect', self.serial], timeout=45, check=False)
        if not self.connected():
            raise Stop('Connexion sdb refusée. Vérifier le mode développeur (IP du Mac), puis redémarrer la TV '
                       '(débranchement 30 s, jamais pendant une mise à jour). Sortie : ' + out.strip()[-200:])

    def capability(self):
        self.connect()
        self.ok('sdb capability (lecture des capacités de la TV)')
        out = self.sdb('capability')
        caps = {k.strip(): v.strip() for k, v in (line.split(':', 1) for line in out.splitlines() if ':' in line)}
        lib.save_local({'tv': {'capability': caps}})
        log('  plateforme : ' + caps.get('platform_version', '?') + ' · architecture : ' + caps.get('cpu_arch', '?')
            + ' · profil : ' + caps.get('profile_name', '?'))
        return caps

    def applist(self, quiet=False):
        self.connect()
        if not quiet:
            self.ok('sdb shell 0 applist (liste des applis installées, lecture seule)')
        out = self.sdb('shell', '0', 'applist', timeout=90)
        (lib.LOCAL / 'tv-applist.txt').write_text(out)
        return out

    def installed(self):
        """L'ID exact de CleanFrame figure-t-il dans applist (jeton entier entre apostrophes) ?"""
        out = lib.run([lib.sdk_tool(self.cfg, 'sdb'), '-s', self.serial, 'shell', '0', 'applist'], timeout=90, show=False)
        return re.search(r"'" + re.escape(self.app_id) + r"'", out) is not None

    # ---------- écritures ----------
    def permit(self):
        self.connect()
        profile = lib.get(self.cfg, 'sign.profile')
        listing = self.tizen('security-profiles', 'list', timeout=60)
        active = re.search(r'^\s*(\S+)\s+O\s*$', listing, re.M) or re.search(r'^\[?\s*(\S+)\s*\]?\s*\(active\)', listing, re.M | re.I)
        if not active or active.group(1) != profile:
            raise Stop('Le profil de certificats actif n\'est pas « ' + profile + ' » (install-permit utilise le profil actif). '
                       'Le rendre actif : ' + str(lib.sdk_tool(self.cfg, 'tizen')) + ' security-profiles set-active -n ' + profile)
        self.ok('tizen install-permit -s ' + self.serial + ' (copie sur la TV l\'autorisation liée à ton certificat distributeur)')
        out = self.tizen('install-permit', '-s', self.serial, check=False)
        if 'permitted' not in out.lower() or re.search(r'Cannot push|Fail|No DUID|Invalid target', out, re.I):
            raise Stop('Autorisation d\'installation non confirmée par le CLI (sortie ci-dessus).')

    def signed(self, path=None):
        if path:
            return Path(path)
        return lib.DIST / json.loads((lib.DIST / 'signed.json').read_text())['wgt']

    def install(self, path=None):
        self.connect()
        wgt = self.signed(path)
        if not wgt.exists():
            raise Stop('Paquet signé introuvable : ' + str(wgt))
        method = lib.get(self.cfg, 'install.method', 'auto')
        self.ok('installation de ' + wgt.name + ' (' + self.app_id + ') sur la TV — l\'écran peut clignoter')
        if method in ('auto', 'tizen'):
            try:
                out = self.tizen('install', '-s', self.serial, '-n', wgt.name, '--', str(wgt.parent), check=False, timeout=300)
            except Stop as timeout:
                out = 'délai dépassé'
                log(str(timeout) + ' — vérification de l\'état de la TV avant de continuer.')
                time.sleep(20)
            failed = INSTALL_FAILED.search(out)
            if not failed and re.search(r'install completed|successfully installed', out, re.I) and self.installed():
                return self.installed_ok(wgt, 'tizen install')
            if method == 'tizen':
                raise Stop('tizen install n\'a pas confirmé l\'installation' + (' (' + failed.group(0) + ')' if failed else '') + '.')
            log('tizen install non confirmé' + (' (« ' + failed.group(0) + ' »)' if failed else '') + ' : repli sur la méthode Samsung vd_appinstall.')
        remote = lib.get(self.cfg, 'tv.capability.sdk_toolpath', '/home/owner/share/tmp/sdk_tools') + '/ma-tv-cleanframe.wgt'
        code, pushed = self.sdb('push', str(wgt), remote, timeout=300, check=False, with_code=True)
        if code or 'pushed' not in pushed or 'failed' in pushed.lower():
            raise Stop('Transfert du paquet vers la TV non confirmé.')
        out = self.sdb('shell', '0', 'vd_appinstall', self.app_id, remote, timeout=300, check=False)
        if 'install completed' not in out or INSTALL_FAILED.search(out) or not self.installed():
            raise Stop('Installation refusée ou non confirmée par la TV (sortie ci-dessus).')
        return self.installed_ok(wgt, 'vd_appinstall')

    def installed_ok(self, wgt, how):
        log('Installation confirmée (' + how + ', ' + self.app_id + ' présent dans applist). Version réellement installée : non vérifiable par sdb sur cette TV.')
        lib.save_local({'tv': {'pending_archive': self.archive_of(wgt)}})
        return how

    def archive_of(self, wgt):
        """Nom de l'archive .local/releases correspondant au paquet installé."""
        signed = lib.DIST / 'signed.json'
        if signed.exists():
            info = json.loads(signed.read_text())
            if Path(wgt).name == info.get('wgt'):
                return info.get('archive')
        return Path(wgt).name if Path(wgt).parent == lib.LOCAL / 'releases' else None

    def launch(self):
        self.connect()
        self.ok('lancement de CleanFrame sur la TV')
        out = self.tizen('run', '-s', self.serial, '-p', self.app_id, check=False, timeout=120)
        if not re.search(r'successfully|launched', out, re.I):
            out = self.sdb('shell', '0', 'was_execute', self.app_id, check=False)
        if not re.search(r'successfully|launched', out, re.I):
            raise Stop('Lancement non confirmé : regarder l\'écran de la TV.')
        self.mark_good()
        return True

    def mark_good(self):
        """Version installée + lancée = version validée : c'est elle que le retour arrière réinstallera."""
        cfg = lib.load_config()
        pending, last = lib.get(cfg, 'tv.pending_archive'), lib.get(cfg, 'tv.last_good_archive')
        if not pending or pending == last:
            return
        index = lib.LOCAL / 'releases' / 'index.json'
        commit = (json.loads(index.read_text()) if index.exists() else {}).get(pending, {}).get('commit')
        lib.save_local({'tv': {'previous_good_archive': last, 'last_good_archive': pending, 'pending_archive': None,
                               'installed_commit': commit}})
        log('Version validée : ' + pending)

    def debug(self):
        self.connect()
        self.ok('lancement de CleanFrame en mode inspecteur + tunnel DevTools local (sdb forward)')
        # Sur cette TV, `shell 0 debug` ne répond pas si l'app tourne déjà : l'arrêter d'abord (comme Samsung Wits).
        self.sdb('shell', '0', 'was_kill', self.app_id, check=False, timeout=30)
        # `shell 0 debug` peut rester ouvert après avoir annoncé le port : lecture au fil de l'eau, arrêt dès le port lu.
        command = [str(lib.sdk_tool(self.cfg, 'sdb')), '-s', self.serial, 'shell', '0', 'debug', self.app_id]
        log('$ ' + ' '.join(command))
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        out, match, deadline = '', None, time.monotonic() + 90
        while time.monotonic() < deadline and not match:
            ready, _, _ = select.select([proc.stdout], [], [], 1)
            if ready:
                line = proc.stdout.readline()
                if not line:
                    break
                out += line
                log('  ' + line.rstrip())
                match = re.search(r'port\s*:?\s*(\d{2,5})', line, re.I)
        os.killpg(proc.pid, signal.SIGTERM)
        if not match:
            raise Stop('Port d\'inspection non fourni par la TV (sortie ci-dessus). Plan B : ma-tv/docs/plan-b.md.')
        port = match.group(1)
        self.sdb('forward', 'tcp:' + port, 'tcp:' + port)
        log('Inspecteur TV : node ma-tv/harness/tv-inspect.mjs --port ' + port)
        lib.save_local({'tv': {'debug_port': int(port)}})
        return int(port)

    def uninstall(self):
        self.connect()
        self.ok('désinstallation de CleanFrame (' + self.app_id + ') — supprime aussi ses réglages')
        self.tizen('uninstall', '-s', self.serial, '-p', self.app_id, check=False, timeout=180)
        if self.installed():
            log('tizen uninstall sans effet : repli vd_appuninstall.')
            self.sdb('shell', '0', 'vd_appuninstall', self.app_id, check=False, timeout=180)
        if self.installed():
            raise Stop('L\'app est toujours installée. Repli manuel : Applications → CleanFrame → Supprimer (télécommande).')
        lib.save_local({'tv': {'installed_commit': None, 'pending_archive': None}})
        log('Désinstallation confirmée (absente d\'applist).')

    def rollback(self):
        cfg = lib.load_config()
        current = lib.get(cfg, 'tv.pending_archive') or lib.get(cfg, 'tv.last_good_archive')
        target = lib.get(cfg, 'tv.last_good_archive')
        # Version validée déjà en place mais défaillante → la précédente ; app absente → la dernière validée.
        if target == current and self.installed():
            target = lib.get(cfg, 'tv.previous_good_archive')
        if not target or not (lib.LOCAL / 'releases' / target).exists():
            raise Stop('Aucune version validée à réinstaller (.local/releases). Repli : Applications → Samsung Home reste utilisable.')
        log('Retour à la dernière version validée : ' + target)
        self.install(lib.LOCAL / 'releases' / target)
        lib.save_local({'tv': {'pending_archive': None, 'last_good_archive': target}})

    def disconnect(self):
        lib.run([lib.sdk_tool(self.cfg, 'sdb'), 'disconnect', self.serial], check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('action', choices=ACTIONS)
    parser.add_argument('--yes', action='store_true', help='ne pas demander de confirmation (mise à jour automatique)')
    parser.add_argument('--wgt', help='paquet signé à installer (par défaut : le dernier signé)')
    args = parser.parse_args()
    tv = TV(args)
    action = getattr(tv, args.action)
    result = action(args.wgt) if args.action == 'install' else action()
    if args.action == 'applist' and result:
        print(result)


if __name__ == '__main__':
    lib.main_guard(main)
