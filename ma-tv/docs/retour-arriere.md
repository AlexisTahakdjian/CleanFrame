# Retour arrière : désinstaller et revenir à l'état d'origine

Cette procédure, pas à pas, ramène la TV et le Mac à leur état d'avant `ma-tv`. **L'ordre compte** : la désinstallation par script exige que le mode développeur soit encore actif, et l'envoi du code 12345 depuis le Mac exige que le Mac soit encore appairé.

Pour revenir seulement à une version précédente de CleanFrame, sans rien désinstaller : [retour arrière partiel](#retour-arrière-partiel--revenir-à-une-version-validée), en fin de document.

Conventions : `<IP_TV>`, `<IP_MAC>`, `<APP_ID>` (identifiant de l'app, dans `.local/ma-tv.json` → `identity.app`), `<PROFIL>` (profil de signature, `MaTV`). Toutes les commandes se lancent depuis la racine du dépôt (`~/CleanFrame`). Chaque commande vers la TV s'affiche et attend un « o », sauf avec `--yes`.

## 0. Ce que ma-tv a changé (état au 2026-10-20)

| Où | Changement | Comment l'annuler | Étape |
| --- | --- | --- | --- |
| TV | CleanFrame installée et lancée (`<APP_ID>`) | Désinstaller | 1 |
| TV | Paquets transférés dans `/home/owner/share/tmp/sdk_tools/` (`tmp/` par `tizen install`, `ma-tv-cleanframe.wgt` par le repli `vd_appinstall`, qui a servi lors du test A/B) | Pas d'effacement possible (shell interactif désactivé) | 1 |
| TV | Autorisation d'installation (`tv.py permit` → « Install Permitted ») | Disparaît avec le mode développeur (**non vérifié**) | 3 |
| TV | Mode développeur **On** avec `<IP_MAC>` comme « Host PC IP » | Off + redémarrage | 3 |
| TV | Mac appairé comme télécommande réseau (« CleanFrame Mac ») | Gestionnaire de connexion de l'appareil | 4 |
| TV | CleanFrame épinglée en tête du bandeau Apps ; « Autorun Last App » essayé ([plan-b](plan-b.md) § 9) | Remettre comme sur les photos | 5 |
| TV | **Rien d'autre** : aucun réglage système, aucune clé vconf, pas de Home natif (l'outil de l'auteur a été retiré) | — | — |
| Mac | `.local/`, `dist/` dans le dépôt | Supprimer | 7 |
| Mac | `~/tizen-studio`, `~/tizen-studio-data`, `~/.package-manager` (journaux et caches du gestionnaire de paquets Tizen), `~/SamsungCertificate/<PROFIL>/` | Désinstaller ou supprimer | 7 |
| Mac | Entrée du Trousseau `cleanframe-signing` : **seulement si tu l'as créée** (les mots de passe sont gardés par Certificate Manager dans le profil ; le Trousseau n'a pas servi jusqu'ici) | Supprimer | 7 |
| Mac | Accès « Réseau local » accordé à iTerm | Retirer | 7 |
| Mac / GitHub | Branche `ma-tv` ; fork GitHub public, s'il a été créé (pas encore au 2026-10-20) | Supprimer si souhaité (ce qui a été publié reste public) | 7 |
| Compte Samsung | Certificats auteur et distributeur émis (DUID de la TV), valables jusqu'au 2027-10-20 | Impossible à annuler | 8 |

**Photos de l'état initial** (utiles à l'étape 5) : À propos de ce téléviseur ; panneau Apps → 12345 (mode développeur Off) ; Paramètres → Général → Fonctions intelligentes ; Assistance → Mise à jour du logiciel ; Gestionnaire de connexion de l'appareil ; bandeau Apps. Si elles n'ont pas été prises avant les changements, se fier au tableau de l'étape 5.

## 1. Désinstaller CleanFrame (TV, mode développeur encore actif)

```sh
python3 ma-tv/tv.py uninstall
```

Ce que fait la commande (`ma-tv/tv.py`, méthode `uninstall`) :

1. garde-fou `guard_tv` : modèle UE43AU7105KXXC, identifiant réseau enregistré, `developerMode`=1, `developerIP` = IP actuelle du Mac ;
2. si nécessaire, `sdb connect <IP_TV>:26101` (après ton « o ») ;
3. `~/tizen-studio/tools/ide/bin/tizen uninstall -s <IP_TV>:26101 -p <APP_ID>` (après ton « o ») ;
4. si l'app figure encore dans `applist` : `~/tizen-studio/tools/sdb -s <IP_TV>:26101 shell 0 vd_appuninstall <APP_ID>` (commande non documentée) ;
5. contrôle final : `<APP_ID>` doit être absent de `sdb shell 0 applist`. Sinon, arrêt avec le message « Repli manuel ». En cas de succès, `tv.installed_commit` est effacé de `.local/ma-tv.json`.

Aucune de ces deux méthodes n'a encore été essayée sur cette TV (**non vérifié**).

**Effet :** les réglages de CleanFrame (`localStorage`) sont effacés ([FAQ Samsung](https://developer.samsung.com/smarttv/develop/faq/data-and-file-handling.html)).

**Vérifier :**

```sh
python3 ma-tv/tv.py applist          # lecture seule ; la liste est copiée dans .local/tv-applist.txt
grep -c "$(python3 -I -c 'import json;print(json.load(open(".local/ma-tv.json"))["identity"]["app"])')" .local/tv-applist.txt
```

Résultat attendu : `0`.

**Repli manuel (télécommande)**, fiable même si sdb échoue (un forum signale des désinstallations sdb sans effet sur des modèles 2021, source non officielle) : Accueil → **Applications** → icône **Paramètres** (roue dentée, en haut à droite) → sélectionner **CleanFrame** → **Supprimer** → confirmer. Libellés exacts de cette TV **non vérifiés** (exemple Samsung, modèles 2022 : [gérer les apps](https://www.samsung.com/uk/support/tv-audio-video/2022-how-to-install-apps-and-manage-downloaded-apps-on-your-samsung-tv/)).

## 2. Fermer la connexion sdb (Mac)

```sh
python3 ma-tv/tv.py disconnect          # sdb disconnect <IP_TV>:26101
~/tizen-studio/tools/sdb kill-server    # ferme aussi un éventuel tunnel d'inspecteur (sdb forward)
```

## 3. Désactiver le mode développeur (TV)

1. Sur la TV : Accueil → **Applications** (le panneau Apps doit être affiché).
2. Saisir **1 2 3 4 5**. Avec cette Smart Remote, la saisie manuelle n'a rien donné (mesuré). Envoyer plutôt le code depuis le Mac, tant que le Mac est encore appairé :

   ```sh
   node ma-tv/tools/remote.mjs KEY_1 KEY_2 KEY_3 KEY_4 KEY_5
   ```

3. Dans la fenêtre « Developer mode » : **Off**, puis **OK**. Si le champ « Host PC IP » est modifiable, le vider (effet **non vérifié**).
4. Redémarrage complet. **D'abord** Paramètres → Assistance → Mise à jour du logiciel : aucune mise à jour en cours. **Ensuite** maintenir la touche Marche jusqu'au redémarrage (méthode utilisée à l'activation, mesuré) ou débrancher 30 s. Ne jamais couper pendant un écran de mise à jour.
5. Vérifier (lecture seule) :

   ```sh
   python3 ma-tv/tv.py info              # attendu : developerMode : 0
   nc -z -w 3 <IP_TV> 26101; echo $?     # attendu : 1 (port fermé)
   ```

   Le bandeau « Develop Mode » doit avoir disparu du panneau Apps. `developerIP` peut rester affiché (**non vérifié**).

**Si la fenêtre 12345 ne revient pas, ou si l'état ne change pas** (cas signalé sur le [forum Samsung](https://forum.developer.samsung.com/t/how-do-i-disable-developer-mode/25104), non officiel ; la doc Samsung ne décrit que l'activation) :

1. redémarrage complet, puis nouvel essai ;
2. avec ton accord : **Reset Smart Hub**, qui efface les apps téléchargées et les comptes connectés ([Samsung](https://www.samsung.com/nz/support/tv-audio-video/i-want-to-reset-smart-hub-setting-how-can-i-do-that/)) ; effet sur le mode développeur **non vérifié** ;
3. en tout dernier recours : réinitialisation d'usine (Paramètres → Général → Réinitialiser), qui efface tout.

## 4. Retirer le Mac appairé (télécommande réseau)

À faire **après** l'étape 3, qui a encore besoin de l'appairage.

1. TV : Paramètres → Général → **Gestionnaire d'appareils externes** → **Gestionnaire de connexion de l'appareil** → **Liste des appareils** → « CleanFrame Mac » → **Supprimer**. Chemin donné en commentaire de `ma-tv/tools/remote.mjs` ; libellés français **non vérifiés**.
2. Si tu l'avais changée, remettre « **Notification d'accès** » (même menu) comme sur la photo.
3. Mac : retirer le jeton.

   ```sh
   python3 -I -c 'import json,os;p=".local/ma-tv.json";d=json.load(open(p));d.get("tv",{}).pop("remote_token",None);open(p,"w").write(json.dumps(d,indent=2,ensure_ascii=False)+"\n");os.chmod(p,0o600)'
   ```

   Inutile si tu supprimes tout `.local/` à l'étape 7.

## 5. Restaurer les réglages de démarrage (TV)

| Réglage | Où (libellés **non vérifiés** sur ce modèle) | Quoi faire |
| --- | --- | --- |
| Position de CleanFrame dans le bandeau Apps | Accueil → tuile → maintenir OK → Déplacer | Disparaît avec la désinstallation (étape 1) |
| « Autorun Last App » (exécution auto de la dernière app) | Paramètres → Général → Fonctions intelligentes | Essayé (sans effet sur CleanFrame, mesuré) : le remettre comme avant si tu l'avais activé |
| « Autorun Smart Hub » | Même menu | Seulement si modifié |
| Verrouillage d'Universal Guide, Anynet+ | — | Seulement si modifiés |
| Mise à jour automatique du logiciel | Paramètres → Assistance | Ne pas y toucher si tu ne l'avais pas changée |

Sans photo, laisser les autres réglages tels quels : les valeurs d'usine de cette TV ne sont pas connues (**non vérifié**).

## 6. Contrôle final sur la TV

| Contrôle | Attendu |
| --- | --- |
| Bandeau Apps | CleanFrame absente |
| Panneau Apps | Plus de bandeau « Develop Mode » |
| `python3 ma-tv/tv.py info` | `developerMode : 0` (à lancer **avant** de supprimer `.local/`) |
| `nc -z -w 3 <IP_TV> 26101` | Échec (port fermé) |
| Touche Home | Ouvre Samsung Home comme avant |
| Gestionnaire de connexion | « CleanFrame Mac » absent |

## 7. Nettoyer le Mac

**Décider d'abord :** si une réinstallation future est possible, garder une **copie chiffrée hors du Mac** de `~/SamsungCertificate/<PROFIL>/`, de `~/tizen-studio-data/profile/profiles.xml`, des mots de passe des certificats, de `.local/ma-tv.json` et de `.local/releases/` ([procédure](procedure.md#sauvegarder-certificats-et-configuration)). Sans eux, une réinstallation se fera sous une nouvelle identité, ce qui ne gêne pas après un retour complet ([risques](risques.md), C1).

| # | Action | Commande |
| --- | --- | --- |
| 1 | Supprimer le mot de passe du Trousseau, **s'il existe** | `security delete-generic-password -s cleanframe-signing -a <PROFIL>` (message « could not be found » = rien à faire) |
| 2 | Retirer le profil de signature du CLI | `~/tizen-studio/tools/ide/bin/tizen security-profiles remove -n <PROFIL>` (syntaxe lue dans l'aide du CLI installé, **non essayée**), ou Certificate Manager → supprimer le profil |
| 3 | Supprimer les certificats | `rm -rf ~/SamsungCertificate/<PROFIL>`, puis `rmdir ~/SamsungCertificate` s'il est vide. Chemins confirmés par `profiles.xml` (mesuré) |
| 4 | Désinstaller Tizen Studio | `open ~/tizen-studio/package-manager/package-manager-uninstaller.app`, puis `rm -rf ~/tizen-studio ~/tizen-studio-data ~/.package-manager` |
| 5 | Supprimer les fichiers locaux du dépôt : `.local/` contient `ma-tv.json` (IP, identité, jeton, capacités), `tv-applist.txt`, `m76/` (Chromium 76), `chrome-ref/`, `venv/` (fontTools), `releases/`, `logs/`, `qa/`, `tmp/`, `downloads/` et les profils de recette | `rm -rf .local dist` |
| 6 | Retirer l'accès « Réseau local » d'iTerm | Réglages Système → Confidentialité et sécurité → Réseau local → iTerm : désactivé |
| 7 | Rosetta 2 | Laisser : composant système, sans désinstallation simple (**non vérifié**), sans effet s'il reste |
| 8 | Dépôt git | Revenir sur `main`, puis supprimer la branche `ma-tv` en local et le fork sur GitHub si tu le souhaites |
| 9 | Box | Supprimer les réservations DHCP créées pour la TV et le Mac, et vérifier qu'aucune redirection de port (26101, 8001, 8002) n'existe |

Node, Python, `gh` et les autres outils du Mac ne sont pas touchés par ma-tv.

## 8. Compte Samsung

Rien d'obligatoire. Ne pas supprimer le compte Samsung principal : il sert à la TV, au téléphone et à SmartThings. Si un compte dédié au développement a été créé, il peut être supprimé sur account.samsung.com (effet sur les certificats déjà émis **non vérifié**).

## Ce qui est irréversible

| Élément | Pourquoi |
| --- | --- |
| Certificats émis par Samsung (le distributeur contient le DUID de la TV) | Aucune révocation en libre-service documentée. Le lien entre DUID et compte reste chez Samsung (durée **non vérifiée**) |
| Acceptation des CGU Samsung Developers et des licences Tizen Studio | Ne s'annule pas |
| Réglages de CleanFrame (`localStorage`) | Effacés à la désinstallation |
| Mises à jour du firmware installées entre-temps | Pas de retour à une version antérieure proposé par Samsung (**non vérifié**) |
| Ce qui a été poussé sur le **fork public** | Peut avoir été cloné ou mis en cache |
| `developerIP` mémorisé par la TV | Peut subsister après la désactivation (**non vérifié**). Seule une réinitialisation l'efface à coup sûr |
| Paquets transférés dans `/home/owner/share/tmp/sdk_tools/` | Pas d'effacement possible par sdb (mesuré : pas de shell interactif) |
| Période d'exposition de sdb sur le réseau local | Aucun journal de connexions accessible (`log_enable` = disabled, mesuré) |
| Certificat auteur ou mot de passe perdus | Plus de mise à jour en place de **cette** installation : désinstaller (réglages perdus), puis réinstaller avec un nouveau certificat |
| Reset Smart Hub ou réinitialisation d'usine, si on en arrive là | Apps, comptes et réglages effacés |

## Retour arrière partiel : revenir à une version validée

Sans tout désinstaller, et en gardant les réglages (si la TV accepte la réinstallation en place : **non vérifié**).

**Ce que `ma-tv` appelle une version « validée »** : un paquet signé, installé **et** lancé avec succès. `tv.py launch` (et `ma-tv/maj`) l'enregistrent dans `.local/ma-tv.json` : `tv.last_good_archive` (la dernière) et `tv.previous_good_archive` (celle d'avant). Les archives sont dans `.local/releases/`.

```sh
python3 ma-tv/tv.py rollback
```

Ce que fait `rollback` (lu dans le code) :

- si une installation **non validée** est en cours (`tv.pending_archive`, cas d'un lancement raté), il réinstalle la **dernière version validée** ;
- sinon (la version installée est la dernière validée), il réinstalle l'**avant-dernière version validée**.

**Au 2026-10-20, une seule version est validée** : `rollback` répond « Aucune version validée à réinstaller ». C'est normal. Pour réinstaller une archive précise, par exemple la dernière validée si l'app a disparu :

```sh
python3 -I -c 'import json;print(json.load(open(".local/ma-tv.json"))["tv"]["last_good_archive"])'   # nom de l'archive validée
python3 ma-tv/tv.py install --wgt .local/releases/<archive>.wgt
python3 ma-tv/tv.py launch
```

**Attention :** `.local/releases/` contient aussi le paquet du test A/B en `required_version` 6.5, refusé par la TV. Le nom des archives n'indique pas cette valeur. Avant d'installer une archive qui n'est pas nommée dans `tv.last_good_archive` ou `tv.previous_good_archive`, la vérifier :

```sh
unzip -p .local/releases/<archive>.wgt config.xml | grep -o 'required_version="[^"]*"'   # attendu : 6.0
```

La TV accepte-t-elle une version plus ancienne, ou de même numéro ? **Non vérifié.** En dernier recours : désinstaller (étape 1) puis réinstaller, ce qui efface les réglages.

**Après un retour arrière manuel**, `tv.py launch` enregistre comme « commit installé » celui du **dernier build** (`dist/ma-tv/build.json`), pas celui de l'archive réinstallée (lu dans le code). `ma-tv/maj` peut donc croire la TV à jour. Pour revenir ensuite à la version courante de `ma-tv` : `ma-tv/maj --rebuild`.
