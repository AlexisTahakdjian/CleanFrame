"""ma-tv : signer le paquet avec le profil de certificats Samsung d'Alexis (CLI officiel Tizen).

- Profil : "sign.profile" de .local/ma-tv.json (créé dans Certificate Manager → Samsung → TV).
- Mot de passe : jamais dans un fichier. Si le CLI le demande, il est lu dans le Trousseau macOS
  (service "sign.keychain_service", compte = nom du profil). Pour l'y mettre une fois :
      security add-generic-password -s cleanframe-signing -a MaTV -w
- Contrairement à scripts/package.py de l'auteur, ne réécrit ni profiles.xml ni sdk.info.
- Garde-fous : même certificat auteur qu'à la première installation (sinon la TV verrait une autre app
  et effacerait les préférences), certificats non expirés, signatures présentes dans le paquet.

Usage : python3 ma-tv/sign.py [--wgt dist/ma-tv/…-unsigned.wgt]
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import pty
import re
import select
import shutil
import signal
import subprocess
import time
import zipfile

import lib
from lib import Stop, log


def keychain_password(cfg):
    service = lib.get(cfg, 'sign.keychain_service', 'cleanframe-signing')
    account = lib.get(cfg, 'sign.profile')
    result = subprocess.run(['security', 'find-generic-password', '-s', service, '-a', account, '-w'], text=True, capture_output=True)
    if result.returncode:
        raise Stop('Le CLI demande le mot de passe du certificat, absent du Trousseau. Une fois : '
                   'security add-generic-password -s ' + service + ' -a ' + account + ' -w')
    return result.stdout.strip().encode()


def sdk_package(cfg, unsigned, outdir):
    """`tizen package -t wgt -s <profil>` dans un pseudo-terminal, pour répondre aux invites éventuelles."""
    tizen = lib.sdk_tool(cfg, 'tizen')
    profile = lib.get(cfg, 'sign.profile')
    profiles = lib.run([tizen, 'security-profiles', 'list'], timeout=60)
    if not re.search(r'(^|\s)' + re.escape(profile) + r'(\s|$)', profiles, re.M):
        raise Stop('Profil de signature « ' + profile + ' » introuvable. Le créer dans Certificate Manager '
                   '(Samsung → TV) ou corriger "sign.profile". Voir ma-tv/docs/procedure.md.')
    command = [str(tizen), 'package', '-t', 'wgt', '-s', profile, '-o', str(outdir), '--', str(unsigned)]
    log('$ ' + ' '.join(command))
    pid, terminal = pty.fork()
    if pid == 0:
        os.execv(command[0], command)
    output, password, answered, refused, deadline = b'', None, 0, 0, time.monotonic() + 180
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([terminal], [], [], 1)
            if not ready:
                continue
            try:
                chunk = os.read(terminal, 8192)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
            asked = output.lower().count(b'password:')
            if asked > answered:
                password = password or keychain_password(lib.load_config())
                os.write(terminal, password + b'\n')
                answered = asked
            if output.count(b'No: (N) ?') > refused:
                os.write(terminal, b'n\n')  # ne jamais enregistrer le mot de passe en clair dans le profil
                refused = output.count(b'No: (N) ?')
        else:
            os.kill(pid, signal.SIGTERM)
            raise Stop('Signature : délai dépassé.')
    finally:
        os.close(terminal)
    os.waitpid(pid, 0)
    text = output.decode(errors='replace')
    if password:
        text = text.replace(password.decode(), '[masqué]')
    for line in text.strip().splitlines()[-12:]:
        log('  ' + line)
    if 'is created successfully' not in text and 'successfully' not in text.lower():
        raise Stop('Le CLI Samsung n\'a pas confirmé la signature (sortie ci-dessus).')


def certificates(signed):
    """Certificats X.509 (base64) des signatures auteur et distributeur."""
    with zipfile.ZipFile(signed) as package:
        names = set(package.namelist())
        if not {'author-signature.xml', 'signature1.xml'} <= names:
            raise Stop('Paquet signé incomplet : author-signature.xml ou signature1.xml manquant.')
        out = {}
        for role, name in (('auteur', 'author-signature.xml'), ('distributeur', 'signature1.xml')):
            xml = package.read(name).decode()
            out[role] = [re.sub(r'\s+', '', c) for c in re.findall(r'<X509Certificate>(.*?)</X509Certificate>', xml, re.S)]
        return out


def end_date(b64):
    pem = '-----BEGIN CERTIFICATE-----\n' + b64 + '\n-----END CERTIFICATE-----\n'
    out = subprocess.run(['openssl', 'x509', '-noout', '-enddate', '-subject'], input=pem, text=True, capture_output=True).stdout
    match = re.search(r'notAfter=(.+)', out)
    when = datetime.strptime(match.group(1).strip().replace('  ', ' '), '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc) if match else None
    subject = (re.search(r'subject=\s*(.+)', out) or [None, ''])[1]
    return when, subject.strip()


def check_certificates(cfg, signed):
    certs = certificates(signed)
    if not certs['auteur']:
        raise Stop('Certificat auteur absent de la signature.')
    author = hashlib.sha256(base64.b64decode(certs['auteur'][0])).hexdigest()
    known = lib.get(cfg, 'sign.author_sha256')
    if known and known != author:
        raise Stop('Le certificat auteur a changé (' + author[:16] + '… au lieu de ' + known[:16] + '…). '
                   'Une mise à jour en place serait refusée ou effacerait les préférences. Utiliser le certificat '
                   'auteur d\'origine (sauvegarde) — voir ma-tv/docs/risques.md.')
    if not known:
        lib.save_local({'sign': {'author_sha256': author}})
        log('Empreinte du certificat auteur enregistrée (première signature) : ' + author[:16] + '…')
    now = datetime.now(timezone.utc)
    report = {}
    for role, chain in certs.items():
        if not chain:
            continue
        when, subject = end_date(chain[0])
        report[role] = {'expire': when.isoformat() if when else None, 'sujet': subject}
        if when and when < now:
            raise Stop('Certificat ' + role + ' expiré le ' + when.date().isoformat() + ' : le renouveler (ma-tv/docs/procedure.md).')
        if when and (when - now).days < 30:
            log('  ATTENTION : certificat ' + role + ' expire dans ' + str((when - now).days) + ' jours (' + when.date().isoformat() + ').')
        log('  certificat ' + role + ' valide jusqu\'au ' + (when.date().isoformat() if when else 'inconnu'))
    return author, report


def sign(unsigned=None):
    cfg = lib.load_config()
    build_info = json.loads((lib.DIST / 'build.json').read_text())
    unsigned = Path(unsigned) if unsigned else lib.DIST / build_info['wgt']
    if not unsigned.exists():
        raise Stop('Paquet non signé introuvable : ' + str(unsigned) + ' (lancer ma-tv/build.py).')
    outdir = lib.DIST / 'signed'
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    sdk_package(cfg, unsigned, outdir)
    produced = sorted(outdir.glob('*.wgt'))
    if len(produced) != 1:
        raise Stop('Sortie de signature inattendue dans ' + str(outdir))
    author, certs = check_certificates(cfg, produced[0])
    target = lib.DIST / unsigned.name.replace('-unsigned', '')
    shutil.copyfile(produced[0], target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    # Archive pour le retour arrière automatique (tv.py rollback).
    releases = lib.LOCAL / 'releases'
    releases.mkdir(parents=True, exist_ok=True)
    archived = releases / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + build_info['version'] + '-' + digest[:12] + '.wgt')
    shutil.copyfile(target, archived)
    info = {'wgt': target.name, 'sha256': digest, 'archive': archived.name, 'author_sha256': author, 'certificats': certs,
            'version': build_info['version'], 'app_id': build_info['app_id'], 'required_version': build_info['required_version']}
    (lib.DIST / 'signed.json').write_text(json.dumps(info, indent=2, ensure_ascii=False) + '\n')
    log('Paquet signé : ' + str(target.relative_to(lib.ROOT)) + ' (archivé : .local/releases/' + archived.name + ')')
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--wgt', help='paquet non signé (par défaut : celui du dernier build)')
    args = parser.parse_args()
    lib.main_guard(lambda: sign(args.wgt))
