"""ma-tv : commandes vers la TV (sdb et CLI officiels Samsung), toujours affichées avant exécution.

Par défaut, chaque action qui touche la TV attend un « o » ; --yes l'exécute directement (utilisé par
update.py, la mise à jour automatique). Avant toute écriture : garde-fou d'identité (modèle, appareil,
mode développeur pointé sur ce Mac) via la lecture seule http://<TV>:8001/api/v2/.

Actions :
  info          lecture seule de :8001/api/v2/ (aucun sdb)
  connect       sdb connect <TV>:26101
  capability    version de plateforme, architecture… (enregistrée dans .local/ma-tv.json)
  applist       applis installées et leurs IDs (enregistrées dans .local/tv-applist.txt)
  permit        autorisation d'installation (profil distributeur) — « Permit to install applications »
  install       installe le dernier paquet signé (tizen install, repli vd_appinstall)
  launch        lance CleanFrame
  debug         lance en mode inspecteur et ouvre le tunnel DevTools (pour la recette sur TV)
  uninstall     désinstalle CleanFrame (tizen uninstall, repli vd_appuninstall)
  rollback      réinstalle la version signée précédente (.local/releases)
  disconnect    ferme la connexion sdb
"""
from pathlib import Path
import argparse
import json
import re
import time

import lib
from lib import Stop, log

ACTIONS = ['info', 'connect', 'capability', 'applist', 'permit', 'install', 'launch', 'debug', 'uninstall', 'rollback', 'disconnect']


class TV:
    def __init__(self, args):
        self.args = args
        self.cfg = lib.load_config()
        self.serial = lib.serial(self.cfg)
        self.app_id = lib.identity(self.cfg)['app']

    def sdb(self, *command, timeout=60, check=True):
        return lib.run([lib.sdk_tool(self.cfg, 'sdb'), '-s', self.serial, *command], timeout=timeout, check=check)

    def tizen(self, *command, timeout=180, check=True):
        return lib.run([lib.sdk_tool(self.cfg, 'tizen'), *command], timeout=timeout, check=check)

    def ok(self, what):
        if getattr(self.args, 'yes', False):
            log('→ ' + what)
            return
        answer = input('→ ' + what + '\n  Lancer cette commande vers la TV ? [o/N] ').strip().lower()
        if answer not in ('o', 'oui', 'y', 'yes'):
            raise Stop('Annulé : ' + what)

    # ---------- lecture seule ----------
    def info(self):
        device = lib.tv_api(self.cfg).get('device', {})
        keep = ['modelName', 'model', 'name', 'OS', 'firmwareVersion', 'resolution', 'networkType', 'developerMode',
                'developerIP', 'FrameTVSupport', 'countryCode', 'PowerState']
        for key in keep:
            log('  ' + key + ' : ' + str(device.get(key)))
        return device

    def connected(self):
        out = lib.run([lib.sdk_tool(self.cfg, 'sdb'), 'devices'], show=False, check=False)
        return any(line.startswith(self.serial) and 'device' in line.split() for line in out.splitlines())

    def connect(self):
        if self.connected():
            return
        lib.guard_tv(self.cfg)
        self.ok('sdb connect ' + self.serial + ' (ouvre la connexion développeur ; ne modifie rien sur la TV)')
        out = lib.run([lib.sdk_tool(self.cfg, 'sdb'), 'connect', self.serial], timeout=45, check=False)
        if not self.connected():
            raise Stop('Connexion sdb refusée. Vérifier le mode développeur (IP du Mac), puis redémarrer la TV '
                       '(débranchement 30 s, jamais pendant une mise à jour). Sortie : ' + out.strip()[-200:])

    def capability(self):
        self.connect()
        self.ok('sdb capability (lecture des capacités de la TV)')
        out = self.sdb('capability')
        caps = dict(line.split(':', 1) for line in out.splitlines() if ':' in line)
        caps = {k.strip(): v.strip() for k, v in caps.items()}
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

    # ---------- écritures ----------
    def permit(self):
        self.connect()
        self.ok('tizen install-permit -s ' + self.serial + ' (installe sur la TV l\'autorisation liée à ton certificat distributeur)')
        self.tizen('install-permit', '-s', self.serial)

    def signed(self, path=None):
        if path:
            return Path(path)
        info = json.loads((lib.DIST / 'signed.json').read_text())
        return lib.DIST / info['wgt']

    def installed(self):
        return self.app_id in self.applist(quiet=True)

    def install(self, path=None):
        self.connect()
        lib.guard_tv(self.cfg)
        wgt = self.signed(path)
        if not wgt.exists():
            raise Stop('Paquet signé introuvable : ' + str(wgt))
        method = lib.get(self.cfg, 'install.method', 'auto')
        self.ok('installation de ' + wgt.name + ' (' + self.app_id + ') sur la TV — l\'écran peut clignoter')
        if method in ('auto', 'tizen'):
            out = self.tizen('install', '-s', self.serial, '-n', wgt.name, '--', str(wgt.parent), check=False, timeout=300)
            if re.search(r'install completed|installed successfully|Tizen application is successfully installed', out, re.I) and self.installed():
                log('Installation confirmée (tizen install, app présente dans applist).')
                return 'tizen'
            if method == 'tizen':
                raise Stop('tizen install n\'a pas confirmé l\'installation.')
            log('tizen install non confirmé : repli sur la méthode Samsung vd_appinstall.')
        remote = '/home/owner/share/tmp/sdk_tools/ma-tv-cleanframe.wgt'  # nom fixe : écrasé à chaque mise à jour
        pushed = self.sdb('push', str(wgt), remote, timeout=300, check=False)
        if 'pushed' not in pushed or 'failed' in pushed.lower():
            raise Stop('Transfert du paquet vers la TV non confirmé.')
        out = self.sdb('shell', '0', 'vd_appinstall', self.app_id, remote, timeout=300, check=False)
        if 'install completed' not in out or 'failed' in out.lower() or not self.installed():
            raise Stop('Installation refusée ou non confirmée par la TV (sortie ci-dessus).')
        log('Installation confirmée (vd_appinstall, app présente dans applist).')
        return 'vd'

    def launch(self):
        self.connect()
        self.ok('lancement de CleanFrame sur la TV')
        out = self.tizen('run', '-s', self.serial, '-p', self.app_id, check=False, timeout=120)
        if 'successfully' in out.lower() or 'launched' in out.lower():
            return True
        out = self.sdb('shell', '0', 'was_execute', self.app_id, check=False)
        if 'successfully' in out.lower() or 'launched' in out.lower():
            return True
        raise Stop('Lancement non confirmé : regarder l\'écran de la TV.')

    def debug(self):
        self.connect()
        self.ok('lancement de CleanFrame en mode inspecteur + tunnel DevTools local (sdb forward)')
        out = self.sdb('shell', '0', 'debug', self.app_id, timeout=120, check=False)
        match = re.search(r'port\s*:?\s*(\d{2,5})', out, re.I)
        if not match:
            raise Stop('Port d\'inspection non fourni par la TV (sortie ci-dessus). Plan B : overlay ?debug.')
        port = match.group(1)
        self.sdb('forward', 'tcp:' + port, 'tcp:' + port)
        log('Inspecteur TV : http://127.0.0.1:' + port + '/json  →  node ma-tv/harness/tv-inspect.mjs --port ' + port)
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
            raise Stop('L\'app est toujours installée. Repli manuel : Apps → CleanFrame → Supprimer (télécommande).')
        log('Désinstallation confirmée (absente d\'applist).')

    def rollback(self):
        signed = json.loads((lib.DIST / 'signed.json').read_text()) if (lib.DIST / 'signed.json').exists() else {}
        releases = sorted((lib.LOCAL / 'releases').glob('*.wgt'))
        previous = [r for r in releases if r.name != signed.get('archive')]
        if not previous:
            raise Stop('Aucune version précédente archivée dans .local/releases.')
        log('Retour à la version précédente : ' + previous[-1].name)
        return self.install(previous[-1])

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
