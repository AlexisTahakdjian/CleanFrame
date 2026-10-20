# Procédure pas à pas

Tout ce qu'il faut pour installer CleanFrame (branche `ma-tv`) sur la Samsung UE43AU7105, le mettre à jour en une commande, vérifier, revenir en arrière et renouveler les certificats. Écrit pour Alexis, à partir de ce qui a été fait et mesuré le 2026-10-20.

**Conventions.** Les commandes se lancent depuis la racine du dépôt (`~/CleanFrame`), dans iTerm. `<IP_TV>`, `<IP_MAC>`, `<APP_ID>` et `<PROFIL>` (`MaTV`) remplacent les valeurs privées, qui vivent dans `.local/ma-tv.json` (ignoré par git, droits 600). Chaque commande `tv.py` vers la TV s'affiche puis attend ton « o » ; `ma-tv/maj` les enchaîne sans question (sauf avec `--confirm`). Journal de tout ce qui est lancé : `.local/logs/ma-tv-AAAAMMJJ.log`.

**Où en est-on (2026-10-20)**

| Étape | État |
| --- | --- |
| [Prérequis sur le Mac](#prérequis-sur-le-mac), [navigateurs de la recette](#navigateurs-de-la-recette), [outils Samsung](#outils-samsung) | fait |
| [Configuration locale](#configuration-locale), [mode développeur](#mode-développeur), [certificats](#certificats) | fait |
| [Sauvegarde chiffrée](#sauvegarder-certificats-et-configuration) | **à faire** |
| [Première installation](#première-installation) | fait (installée, lancée, validée) |
| [Mise à jour `ma-tv/maj`](#mettre-à-jour--ma-tvmaj) | `--dry-run` essayé ; première exécution complète **à faire** |
| [Fork public](#le-fork-public) | **à faire** |
| [Renouvellement des certificats](#renouveler-les-certificats) | avant le **2027-10-20** |

Autres sections : [conflit de mise à jour](#conflit-de-mise-à-jour) · [retour arrière manuel](#retour-arrière-manuel) · [vérifier avec l'inspecteur](#vérifier-avec-linspecteur) · [restaurer le certificat auteur](#restaurer-le-certificat-auteur) · [tout désinstaller](#tout-désinstaller).

## Prérequis sur le Mac

Mac Apple Silicon sous **macOS 27** (dernière version avec Rosetta complet : ne pas passer à macOS 28 sans lire [plan-b](plan-b.md) § 10).

1. **Rosetta 2** (les outils Samsung et Chromium 76 sont en x86_64) :

   ```sh
   softwareupdate --install-rosetta --agree-to-license
   ```

2. **Node.js 22 ou plus** (le harnais utilise le `WebSocket` intégré de Node ; Node 26 sur ce Mac) et **Python 3.10 ou plus** (bibliothèque standard seulement). Avec Homebrew :

   ```sh
   brew install node python gh openssl
   node --version && python3 --version
   ```

   `gh` sert au fork, `openssl` à `sign.py` (lecture des dates des certificats). `git` et `unzip` sont fournis par macOS.

3. **Autorisation « Réseau local » pour iTerm.** Réglages Système → Confidentialité et sécurité → **Réseau local** → activer **iTerm** (ou Terminal si tu l'utilises). Sans elle, Node et Python échouent en `EHOSTUNREACH` (« No route to host ») vers la TV, alors que `curl` passe (il est exempté) (mesuré sur le Mac). Relance iTerm si le changement ne prend pas.

4. **Le dépôt.** Branche `ma-tv`, avec l'auteur comme remote `upstream` :

   ```sh
   git switch ma-tv
   git remote -v        # upstream → https://github.com/nthnclrk/CleanFrame
   ```

   S'il manque : `git remote add upstream https://github.com/nthnclrk/CleanFrame`.

## Navigateurs de la recette

La recette (`ma-tv/harness/run.mjs`) teste le paquet dans **Chromium 76** (le moteur de Tizen 6.0) et dans un **Chrome récent de référence**. Le Chrome 118 installé sur le Mac plante en mode headless sous macOS 27 (mesuré) : la référence est le `chrome-headless-shell` officiel. Les deux vont dans `.local/` (ignoré par git).

```sh
# Chromium 76.0.3809.0 : snapshot officiel r665002 (x86_64, tourne sous Rosetta)
mkdir -p .local/m76
curl -L -o .local/m76/chrome-mac.zip https://commondatastorage.googleapis.com/chromium-browser-snapshots/Mac/665002/chrome-mac.zip
unzip -q .local/m76/chrome-mac.zip -d .local/m76
.local/m76/chrome-mac/Chromium.app/Contents/MacOS/Chromium --version      # attendu : Chromium 76.0.3809.0

# Chrome for Testing 155 (référence, arm64)
mkdir -p .local/chrome-ref
curl -L -o .local/chrome-ref/shell.zip https://storage.googleapis.com/chrome-for-testing-public/155.0.8059.84/mac-arm64/chrome-headless-shell-mac-arm64.zip
unzip -q .local/chrome-ref/shell.zip -d .local/chrome-ref
.local/chrome-ref/chrome-headless-shell-mac-arm64/chrome-headless-shell --version   # Google Chrome for Testing 155.0.8059.84
```

Ces chemins sont ceux de `ma-tv/config.example.json` (`chromium76`, `chrome_reference`). Pour une autre version de référence : liste sur [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/), puis chemin dans `.local/ma-tv.json` ou `CLEANFRAME_CHROME_REFERENCE`. Chromium 76 ne sert **qu'à** la recette : ne jamais naviguer avec ([risques](risques.md), R5).

Facultatif, seulement si l'auteur change ses polices (le build le signale) : `python3 -m venv .local/venv && .local/venv/bin/pip install fonttools brotli`, puis `.local/venv/bin/python ma-tv/tools/static-fonts.py`.

## Outils Samsung

Tizen Studio 6.1 en version ligne de commande (« web-cli »), plus trois paquets. C'est l'étape que citent les messages d'erreur de `ma-tv` (« Outil Samsung introuvable »).

1. Télécharger `web-cli_Tizen_Studio_6.1_macos-64.bin` depuis la page officielle [Tizen Studio](https://developer.tizen.org/development/tizen-studio/download) (section des installeurs en ligne de commande, macOS) dans `.local/downloads/`.
2. Installer dans `~/tizen-studio` :

   ```sh
   chmod +x .local/downloads/web-cli_Tizen_Studio_6.1_macos-64.bin
   .local/downloads/web-cli_Tizen_Studio_6.1_macos-64.bin --accept-license ~/tizen-studio
   ```

3. Ajouter les paquets Samsung avec le gestionnaire de paquets (commandes exactes utilisées le 2026-10-20) :

   ```sh
   ~/tizen-studio/package-manager/package-manager-cli.bin show-pkgs
   ~/tizen-studio/package-manager/package-manager-cli.bin install --accept-license cert-add-on TV-SAMSUNG-Extension-Tools
   ~/tizen-studio/package-manager/package-manager-cli.bin install --accept-license WebIDE
   ```

   - `cert-add-on` = Samsung Certificate Extension (2.0.75 ; Samsung exige ≥ 2.0.73) ;
   - `TV-SAMSUNG-Extension-Tools` (10.0.0) amène aussi `TV-SAMSUNG-Extension-Resources` ;
   - `WebIDE` est **indispensable** : il fournit l'application de base de Certificate Manager. Avec `cert-add-on` seul, `Certificate-manager.app` restait incomplète (mesuré sur le Mac).

4. Vérifier :

   ```sh
   ~/tizen-studio/tools/sdb version                 # sdb 4.2.36 sur ce Mac
   ~/tizen-studio/tools/ide/bin/tizen version
   ls ~/tizen-studio/tools/certificate-manager/Certificate-manager.app
   ```

Tout est en x86_64 et tourne sous Rosetta. Si Tizen Studio est installé ailleurs : clé `"sdk"` dans `.local/ma-tv.json` ou variable `CLEANFRAME_TIZEN_SDK`.

## Configuration locale

Déjà fait sur ce Mac ; à refaire seulement sur un nouveau Mac (ou restaurer `.local/ma-tv.json` depuis la [sauvegarde](#sauvegarder-certificats-et-configuration), ce qui est préférable car il contient l'identité de l'app).

`ma-tv/config.example.json` (versionné) donne les valeurs par défaut ; `.local/ma-tv.json` (privé) les complète. Les deux sont fusionnés. Pour le créer sans recopier d'identifiant à la main :

```sh
# 1. adresse de la TV (lisible sur la TV : Paramètres → Général → Réseau → État du réseau ; libellés non vérifiés)
python3 -c 'import sys; sys.path.insert(0, "ma-tv"); import lib; lib.save_local({"tv": {"host": "<IP_TV>"}})'
# 2. identifiant réseau de la TV, pour le garde-fou (lu sur :8001, ce n'est PAS le DUID)
python3 -c 'import sys; sys.path.insert(0, "ma-tv"); import lib; d = lib.tv_api(lib.load_config())["device"]; lib.save_local({"tv": {"udn": d["id"]}}); print(d["modelName"])'
# 3. IP du Mac vers la TV
python3 -c 'import sys; sys.path.insert(0, "ma-tv"); import lib; lib.save_local({"mac_ip": lib.mac_ip_towards(lib.tv_host(lib.load_config()))}); print("ok")'
```

`save_local` écrit `.local/ma-tv.json` en droits 600. L'**identité de l'app** (`identity.*`, dont `<APP_ID>`) est créée une seule fois par le premier `build.py`, puis ne doit plus jamais changer (sinon la TV verrait une deuxième app et les réglages seraient perdus). Conseillé : réserver les IP de la TV et du Mac sur la box (réservation DHCP).

## Mode développeur

Fait le 2026-10-20 (mesuré). À refaire seulement après une réinitialisation de la TV, ou pour le désactiver ([retour-arriere](retour-arriere.md) étape 3).

1. TV allumée, sur le même réseau que le Mac. Ouvrir le panneau **Applications** (Apps).
2. Avec cette Smart Remote, taper 12345 ne fait rien (mesuré). Envoyer le code depuis le Mac, par la télécommande réseau de la TV (`wss://<IP_TV>:8002`) :

   ```sh
   node ma-tv/tools/remote.mjs pair
   ```

   La TV affiche une invite d'autorisation pour « CleanFrame Mac » : **l'accepter tout de suite, elle expire au bout d'environ 30 s** (mesuré). Le jeton reçu est gardé dans `.local/ma-tv.json` (`tv.remote_token`). À faire une seule fois.

3. Panneau Apps toujours affiché :

   ```sh
   node ma-tv/tools/remote.mjs KEY_1 KEY_2 KEY_3 KEY_4 KEY_5
   ```

4. La fenêtre « Developer mode » s'ouvre. Mettre **On**, saisir toi-même `<IP_MAC>` dans **Host PC IP** à la télécommande (`remote.mjs --text "<IP_MAC>"` existe, mais la saisie manuelle a suffi), **OK**.
5. Redémarrer la TV : **appui long sur Marche** jusqu'au redémarrage (mesuré). Avant, vérifier qu'aucune mise à jour du firmware n'est en cours (Paramètres → Assistance → Mise à jour du logiciel). Ne jamais couper pendant une mise à jour.
6. Vérifier depuis le Mac :

   ```sh
   python3 ma-tv/tv.py info          # lecture seule : developerMode : 1, developerIP = <IP_MAC>
   python3 ma-tv/tv.py connect       # sdb connect <IP_TV>:26101
   python3 ma-tv/tv.py capability    # platform_version 6.0, armv7 (enregistré dans .local/ma-tv.json)
   python3 ma-tv/tv.py applist       # liste des apps → .local/tv-applist.txt
   ```

Si `guard_tv` répond « La TV attend le Mac … » : l'IP du Mac a changé ; corriger « Host PC IP » sur la TV (étapes 1 à 5) et `mac_ip` dans `.local/ma-tv.json`.

## Certificats

Fait le 2026-10-20 (mesuré). Ce qui suit sert à refaire ou à comprendre le renouvellement. Un compte Samsung dédié au développement est recommandé ([risques](risques.md), C6).

1. La TV doit être **connectée en sdb** (pour que Certificate Manager lise son DUID) :

   ```sh
   python3 ma-tv/tv.py connect
   open ~/tizen-studio/tools/certificate-manager/Certificate-manager.app
   ```

2. Écrans de Certificate Manager (libellés anglais de l'application ; les écrans intermédiaires suivent la doc Samsung [Creating Certificates](https://developer.samsung.com/smarttv/develop/getting-started/setting-up-sdk/creating-certificates.html) et peuvent varier légèrement) :

   | Écran | Choix |
   | --- | --- |
   | Liste des profils | **+** (créer un profil de certificats) |
   | Type de profil | **Samsung** (pas Tizen) |
   | Type d'appareil | **TV** |
   | Nom du profil | **MaTV** (= `sign.profile` de ma-tv) |
   | Certificat auteur | **Create a new author certificate** : nom d'auteur, mot de passe (à garder dans ton gestionnaire de mots de passe) |
   | Connexion | Fenêtre de connexion au compte Samsung : saisir toi-même identifiants et 2FA |
   | Certificat distributeur | Nouveau certificat distributeur, privilège **Public** |
   | DUID | Le DUID de la TV connectée est **détecté et pré-coché** : le garder tel quel. Ne pas y ajouter l'identifiant `device.id` de `/api/v2/` : ce n'est **pas** le DUID (mesuré) |
   | Fin | Profil **MaTV** actif |

3. Résultat (mesuré) : `~/SamsungCertificate/MaTV/` contient `author.p12`, `author.pri`, `author.crt`, `author.csr`, `distributor.p12`, `distributor.pri`, `distributor.crt`, `distributor.csr`, `device-profile.xml`. Émetteurs : « Samsung VD Author CA » (auteur) et « VD DEVELOPER Public CA Class » (distributeur). **Les deux sont valables un an seulement : expiration le 2027-10-20.** Certificate Manager garde les mots de passe dans le profil Tizen (`~/tizen-studio-data/profile/profiles.xml`) : `sign.py` n'a pas eu besoin du Trousseau jusqu'ici.
4. Protéger les clés privées (déjà le cas, mesuré) :

   ```sh
   chmod 700 ~/SamsungCertificate/MaTV
   chmod 600 ~/SamsungCertificate/MaTV/*.p12 ~/SamsungCertificate/MaTV/*.pri
   ```

5. Vérifier que le CLI voit le profil, actif :

   ```sh
   ~/tizen-studio/tools/ide/bin/tizen security-profiles list          # MaTV marqué actif
   ~/tizen-studio/tools/ide/bin/tizen security-profiles set-active -n MaTV   # seulement s'il ne l'est pas
   ```

Si un jour le CLI demande le mot de passe pendant la signature, `sign.py` le cherche dans le Trousseau. L'y mettre une fois : `security add-generic-password -s cleanframe-signing -a MaTV -w`.

## Sauvegarder certificats et configuration

**À faire maintenant, puis après chaque renouvellement.** Sans le certificat auteur, son mot de passe et `.local/ma-tv.json`, plus aucune mise à jour en place n'est possible ([risques](risques.md), C1 et C2).

```sh
d=$(mktemp -d)
cp -Rp ~/SamsungCertificate/MaTV "$d/SamsungCertificate-MaTV"
cp -p ~/tizen-studio-data/profile/profiles.xml "$d/"
cp -p .local/ma-tv.json "$d/"
cp -Rp .local/releases "$d/releases"
hdiutil create -encryption AES-256 -srcfolder "$d" -volname matv-sauvegarde ~/Desktop/matv-sauvegarde-$(date +%Y%m%d).dmg   # demande un mot de passe
rm -rf "$d"
```

Copier l'image chiffrée **hors du Mac** (disque externe, stockage en ligne). Mettre dans le gestionnaire de mots de passe : le mot de passe de l'image, ceux des certificats auteur et distributeur. Ne jamais copier ces fichiers dans le dépôt.

## Première installation

Faite le 2026-10-20 (mesuré). À refaire seulement après une désinstallation ou sur une nouvelle TV.

```sh
python3 ma-tv/build.py            # barrières + adaptations Tizen 6.0 → dist/ma-tv/CleanFrame-<version>-tizen6.0-unsigned.wgt
node ma-tv/harness/run.mjs        # recette Chromium 76 + référence : attendu « N / N vérifications réussies »
python3 ma-tv/sign.py             # signature MaTV ; dates des certificats ; archive dans .local/releases/
python3 ma-tv/tv.py permit        # autorisation d'installation : attendu « Install Permitted »
python3 ma-tv/tv.py install       # tizen install (repli vd_appinstall) ; contrôlé par applist
python3 ma-tv/tv.py launch        # tizen run ; la version devient « validée »
```

Ce qu'il faut voir :

- `build.py` : « Barrières : OK » n'apparaît qu'avec `--check-only` ; sinon « Paquet non signé : … (… Ko, app `<APP_ID>`, Tizen 6.0) ». Au tout premier build : « Nouvelle identité d'app générée ».
- `run.mjs` : rapport dans `.local/qa/ma-tv/<horodatage>/summary.md` (189/189 le 2026-10-20). Les temps de démarrage sont rapportés sans être jugés.
- `sign.py` : « Empreinte du certificat auteur enregistrée (première signature) », puis « certificat auteur valide jusqu'au 2027-10-20 » et idem pour le distributeur.
- `tv.py permit` : refuse de continuer si le profil actif n'est pas `MaTV` (il donne la commande `set-active`).
- `tv.py install` : « Installation confirmée (tizen install, … présent dans applist) ». Avec `required_version` 6.5, la TV refuse : « install failed[118, -19], reason: Parsing error » (mesuré).
- `tv.py launch` : « Tizen application is successfully launched », puis « Version validée : <archive> ».

Ensuite, à la télécommande : épingler CleanFrame **en tête du bandeau Apps** (tuile → maintenir OK → Déplacer tout à gauche). Home puis OK ouvre alors CleanFrame (mesuré ; [plan-b](plan-b.md) § 9).

**Note :** la première installation a été construite depuis un arbre contenant des modifications pas encore commitées. `tv.installed_commit` est donc vide, et le **premier** `ma-tv/maj` reconstruira et réinstallera une fois, même sans nouveauté de l'auteur. C'est normal.

## Mettre à jour : `ma-tv/maj`

**La commande à retenir :**

```sh
ma-tv/maj
```

TV allumée (écran actif), mode développeur actif, branche `ma-tv` propre (tout commité). Lance-la quand personne ne regarde la TV : l'installation relance CleanFrame.

**Ce qu'elle fait, dans l'ordre** (`ma-tv/update.py`) :

1. vérifie la branche, l'arbre propre, le remote `upstream` et que la première installation a été faite ;
2. `git fetch upstream` ; affiche les nouveautés de l'auteur et le `git diff --stat` ;
3. s'il n'y a rien de nouveau **et** que la TV a déjà la dernière version de `ma-tv` : s'arrête là, **sans contacter la TV** ;
4. fusionne l'auteur dans une branche temporaire `ma-tv-maj-<date>` (merge, jamais de rebase) ; conflit → abandon propre ([conflit de mise à jour](#conflit-de-mise-à-jour)) ;
5. construit le paquet (barrières) puis lance la recette (3 essais de démarrage, sans captures) ;
6. contrôle anti-fuite (si le fork est configuré), puis signature ;
7. TV : garde-fou d'identité, installation en place, lancement → version validée. En cas d'échec avec l'app absente ou qui ne se lance pas : retour automatique à la dernière version validée ;
8. **seulement si la TV a validé** : avance `ma-tv` (fast-forward), enregistre le commit installé, publie sur le fork (anti-fuite refait avant le push).

Au premier problème, tout s'arrête avec un message « ARRÊT : … » : la branche `ma-tv` et l'app installée restent intactes, la branche temporaire est supprimée.

| Option | Effet |
| --- | --- |
| `--dry-run` | Récupère et affiche les nouveautés, puis s'arrête : aucune fusion, aucun build, rien vers la TV (essayé le 2026-10-20) |
| `--confirm` | Demande un « o » avant chaque commande vers la TV. Un « N » annule proprement, sans retour arrière |
| `--skip-tv` | S'arrête après la signature. Attention : `ma-tv` avance quand même et le fork est mis à jour ; la TV n'est pas touchée et le `maj` suivant installera |
| `--rebuild` | Reconstruit et réinstalle même sans nouveauté (après une mise à jour du firmware qui aurait effacé l'app, par exemple) |
| `--skip-tests` | Saute la recette (déconseillé : c'est la principale barrière) |
| `--no-push` | Ne publie pas sur le fork |

**Si la TV est éteinte** (ou en veille, ou le mode développeur coupé) — lu dans le code, non testé : s'il y a quelque chose à installer, `maj` refait fusion, build, recette et signature, puis s'arrête au garde-fou de la TV (« La TV ne répond pas sur … Est-elle allumée, écran actif ? » dans le journal ; le dernier message peut être celui de la commande sdb de contrôle). Rien n'avance : `ma-tv`, la TV et le fork restent comme avant. Allume la TV et relance `ma-tv/maj` : il refait tout. Chaque essai laisse une archive de plus dans `.local/releases/`.

**Messages d'arrêt fréquents**

| Message | Quoi faire |
| --- | --- |
| « Modifications locales non commitées » | Commiter (ou ranger) d'abord, puis relancer |
| « Fusion impossible automatiquement » | [Conflit de mise à jour](#conflit-de-mise-à-jour) |
| « N barrière(s) franchie(s) » | L'auteur a introduit quelque chose d'incompatible ou de risqué (détail dans `dist/ma-tv/build.json`). Attendre, ou adapter `ma-tv/build.py` |
| « L'amont a changé de forme » | Un fichier de l'auteur n'a plus la forme attendue : adapter `ma-tv/build.py` |
| « La recette a échoué » | Lire `.local/qa/ma-tv/<horodatage>/summary.md` |
| « Fuite évitée, rien n'est publié » | Retirer la valeur privée du fichier ou de l'historique cité, puis relancer |
| « Certificat … expire dans N jours » | [Renouveler les certificats](#renouveler-les-certificats) |
| « Le certificat auteur a changé » | [Restaurer le certificat auteur](#restaurer-le-certificat-auteur) |
| « L'IP du Mac a changé » / « La TV attend le Mac … » | Corriger `mac_ip` et « Host PC IP » ([mode développeur](#mode-développeur)) |
| « fork « origin » non configuré » | Avertissement seulement : [le fork public](#le-fork-public) |

## Conflit de mise à jour

`ma-tv/maj` n'essaie jamais de résoudre un conflit : il annule la fusion et laisse `ma-tv` intacte. Pour le résoudre à la main, dans une branche à part :

```sh
git fetch upstream
git switch -c ma-tv-maj-manuel
git merge upstream/main
```

Résoudre : ouvrir chaque fichier cité par `git status`, garder les changements de l'auteur **et** les lignes marquées `ma-tv` (liste dans [modifications](modifications.md)), puis :

```sh
git add <fichier>…
git commit --no-edit
```

Vérifier avant d'avancer `ma-tv` :

```sh
python3 ma-tv/build.py --check-only     # attendu : « Barrières : OK »
node ma-tv/harness/run.mjs              # attendu : toutes les vérifications réussies
```

`--check-only` prépare aussi `dist/ma-tv/stage/`, que la recette teste. Si tout est vert :

```sh
git switch ma-tv
git merge --ff-only ma-tv-maj-manuel
git branch -d ma-tv-maj-manuel
ma-tv/maj                               # voit que ma-tv n'est pas encore sur la TV : signe, installe, valide, publie
```

Pour abandonner en cours de route : `git merge --abort` (si la fusion n'est pas commitée), `git switch ma-tv`, `git branch -D ma-tv-maj-manuel`.

## Retour arrière manuel

Si une version installée ne te convient pas :

```sh
python3 ma-tv/tv.py rollback
```

Il réinstalle la version validée précédente (`.local/releases/`, nommée dans `.local/ma-tv.json` → `tv.previous_good_archive`), ou la dernière validée si une installation non validée est en cours. Au 2026-10-20, une seule version est validée : la réponse « Aucune version validée à réinstaller » est normale. Réinstaller une archive précise, vérifier qu'elle n'est pas le paquet de test 6.5, et revenir ensuite à la version courante : [retour-arriere](retour-arriere.md#retour-arrière-partiel--revenir-à-une-version-validée).

## Vérifier avec l'inspecteur

Pour relever, sur la vraie TV, les erreurs console, les temps et le moteur. Fait le 2026-10-20 (résultats : [resultats-tests](resultats-tests.md)).

```sh
python3 ma-tv/tv.py debug
```

Ce que fait la commande : arrête CleanFrame (`sdb shell 0 was_kill <APP_ID>` ; sans cela, `debug` reste bloqué si l'app tourne déjà, mesuré), la relance en mode inspecteur (`sdb shell 0 debug <APP_ID>`), lit « port: NNNNN », ouvre le tunnel local `sdb forward tcp:NNNNN tcp:NNNNN` et affiche la commande suivante :

```sh
node ma-tv/harness/tv-inspect.mjs --port <port> --reloads 3
```

Pour chaque rechargement : « accueil utilisable » (focus visible), « écran complet (photo) » et FCP, en ms. Puis le moteur réel, le viewport, l'état du polyfill `gap`, Manrope, et le nombre d'erreurs. Rapport : `.local/qa/ma-tv/tv-<horodatage>.json` ; code de sortie 1 s'il y a une erreur. `--keys` injecte en plus quelques touches par l'inspecteur (ça ne remplace pas la télécommande). L'inspecteur de cette TV ne fait pas de capture d'écran (`Page.captureScreenshot`, mesuré).

**Mesure finale hors inspecteur** (le critère « < 2 s ») : les mesures sous inspecteur sont un peu plus lentes, et une app déboguée ne s'arrête pas quand on la ferme (Samsung). Redémarrer la TV (appui long sur Marche), puis, depuis le bandeau Apps, chronométrer ou filmer au ralenti (≥ 120 i/s) l'ouverture de CleanFrame jusqu'à l'accueil, 5 fois. Mesure du 2026-10-20 au chronomètre : 1 à 2 s, lancement compris.

Le tunnel disparaît avec `~/tizen-studio/tools/sdb kill-server` ou au redémarrage du Mac.

## Le fork public

Pas encore fait au 2026-10-20 (aucun remote `origin`). Le fork est **public** : tout ce qui y est poussé est définitif.

1. Se connecter à GitHub :

   ```sh
   gh auth login        # GitHub.com → HTTPS → connexion par le navigateur
   ```

2. Créer le fork et l'ajouter comme remote `origin` :

   ```sh
   gh repo fork --remote
   git remote -v        # upstream → nthnclrk/CleanFrame ; origin → <ton-compte>/CleanFrame
   ```

   Variante : créer le fork sur github.com, puis `git remote add origin https://github.com/<ton-compte>/CleanFrame.git`.

3. Première publication, après le contrôle anti-fuite de `ma-tv` (le push n'a lieu que si le contrôle passe) :

   ```sh
   python3 -c 'import sys; sys.path.insert(0, "ma-tv"); import lib, update; lib.main_guard(lambda: update.leak_check(lib.load_config(), None)); print("Anti-fuite : OK")' && git push -u origin ma-tv
   ```

4. Ensuite, `ma-tv/maj` publie tout seul après chaque mise à jour validée sur la TV (`"fork": {"remote": "origin", "push": true}` par défaut), en refaisant le contrôle sur les commits à pousser. Pour ne pas publier : `--no-push`, ou `"fork": {"push": false}` dans `.local/ma-tv.json`.

Jamais `git add -f` dans `.local/` ou `dist/`, jamais de fichier de `~/SamsungCertificate/` dans le dépôt ([risques](risques.md), R4).

## Renouveler les certificats

**Échéance : 2027-10-20** pour l'auteur comme pour le distributeur (validité d'un an, mesuré). `sign.py` affiche un avertissement à moins de 30 jours (à partir du 2027-09-20) et refuse de signer une fois la date passée. Pose un rappel pour **début septembre 2027**, et fais-le **avant** tout passage à macOS 28 ([plan-b](plan-b.md) § 10).

1. **Sauvegarder l'existant** ([sauvegarde](#sauvegarder-certificats-et-configuration)) : l'ancien certificat auteur reste la référence en cas de problème.
2. TV allumée, mode développeur actif, `python3 ma-tv/tv.py connect`, puis ouvrir Certificate Manager (`open ~/tizen-studio/tools/certificate-manager/Certificate-manager.app`).
3. **Distributeur** : nouveau certificat distributeur pour la même TV, dans le profil **MaTV** : Samsung → TV, privilège **Public**, DUID pré-coché conservé.
4. **Auteur** : le but est de **garder la même clé** (sinon la TV verrait un autre auteur et refuserait la mise à jour en place ou effacerait les réglages). Choisir l'option qui réutilise le certificat auteur existant (`author.p12` + son mot de passe) ou qui le prolonge. Libellé exact et comportement pour une TV : **non vérifiés** (Samsung le documente pour la montre : [Extending certificates](https://developer.samsung.com/galaxy-watch-tizen/getting-certificates/extend.html)).
5. Signer et lire le verdict de `sign.py` :

   ```sh
   python3 ma-tv/build.py && python3 ma-tv/sign.py
   ```

   - **Il passe** : lire les dates affichées. Si l'auteur expire toujours le 2027-10-20, seul le distributeur a été renouvelé : reprendre l'étape 4 (un certificat auteur expiré bloquera la signature). Si les deux dates sont repoussées, refaire l'autorisation (liée au distributeur ; nécessité **non vérifiée**, sans danger) puis mettre à jour : `python3 ma-tv/tv.py permit` puis `ma-tv/maj --rebuild`.
   - **Il s'arrête sur « Le certificat auteur a changé »** : c'est le cas attendu après un vrai renouvellement de l'auteur. Un certificat réémis a d'autres dates, donc une autre empreinte, même avec la même clé (l'empreinte vérifiée par `sign.py` porte sur le certificat entier). Comparer les **clés publiques** de l'ancien paquet validé et du nouveau paquet signé :

     ```sh
     cle() { unzip -p "$1" author-signature.xml | python3 -I -c 'import re,sys; print(re.sub(r"\s+","",re.findall(r"<X509Certificate>(.*?)</X509Certificate>",sys.stdin.read(),re.S)[0]))' | fold -w 64 | { echo '-----BEGIN CERTIFICATE-----'; cat; echo '-----END CERTIFICATE-----'; } | openssl x509 -noout -pubkey | shasum -a 256 | cut -c1-64; }
     ancien=".local/releases/$(python3 -I -c 'import json;print(json.load(open(".local/ma-tv.json"))["tv"]["last_good_archive"])')"
     [ "$(cle "$ancien")" = "$(cle dist/ma-tv/signed/*.wgt)" ] && echo "MÊME CLÉ" || echo "CLÉ DIFFÉRENTE : ne pas installer"
     ```

     - **Même clé** : accepter le nouveau certificat. Vider `sign.author_sha256` dans `.local/ma-tv.json` (mettre `""`), puis faire la mise à jour pas à pas pour l'observer : `python3 ma-tv/sign.py` (enregistre la nouvelle empreinte), `python3 ma-tv/tv.py permit`, `python3 ma-tv/tv.py install`, `python3 ma-tv/tv.py launch`. Vérifier que l'accueil et les réglages de CleanFrame sont conservés. Ensuite `ma-tv/maj` reprend la main. Si la TV refuse la mise à jour en place (erreur de certificat) : dernier recours, `python3 ma-tv/tv.py uninstall` puis `install` et `launch` (les réglages sont perdus, l'identité de l'app reste la même).
     - **Clé différente** : ne rien installer. Recommencer l'étape 4 avec l'ancien `author.p12` ([restaurer le certificat auteur](#restaurer-le-certificat-auteur)).
6. Refaire la [sauvegarde](#sauvegarder-certificats-et-configuration), et mettre à jour la date d'expiration dans [profil-tv](profil-tv.md) et [risques](risques.md).

## Restaurer le certificat auteur

Quand : nouveau Mac, fichiers perdus, profil introuvable, ou `sign.py` qui dit « Le certificat auteur a changé » alors qu'aucun renouvellement n'a eu lieu.

1. Installer les [outils Samsung](#outils-samsung) si besoin.
2. Ouvrir l'image chiffrée de la [sauvegarde](#sauvegarder-certificats-et-configuration) et remettre en place :

   ```sh
   S=/Volumes/matv-sauvegarde
   [ -e ~/SamsungCertificate/MaTV ] && mv ~/SamsungCertificate/MaTV ~/SamsungCertificate/MaTV.avant-restauration
   mkdir -p ~/SamsungCertificate .local/releases && cp -Rp "$S/SamsungCertificate-MaTV" ~/SamsungCertificate/MaTV
   chmod 700 ~/SamsungCertificate/MaTV && chmod 600 ~/SamsungCertificate/MaTV/*.p12 ~/SamsungCertificate/MaTV/*.pri
   mkdir -p ~/tizen-studio-data/profile && cp -p "$S/profiles.xml" ~/tizen-studio-data/profile/
   cp -p "$S/ma-tv.json" .local/ma-tv.json && chmod 600 .local/ma-tv.json
   cp -Rp "$S/releases/." .local/releases/
   ```

   `profiles.xml` contient des chemins absolus vers `~/SamsungCertificate/MaTV/` : avec un autre nom d'utilisateur macOS, les corriger dans le fichier, ou recréer le profil dans Certificate Manager en important `author.p12` et `distributor.p12` existants avec leurs mots de passe.
3. Vérifier :

   ```sh
   ~/tizen-studio/tools/ide/bin/tizen security-profiles list     # MaTV présent et actif
   python3 ma-tv/build.py && python3 ma-tv/sign.py               # ne doit PAS dire « Le certificat auteur a changé »
   ```

4. Si le Mac a changé d'IP : [mode développeur](#mode-développeur) (« Host PC IP »), puis `ma-tv/maj`.

**Sans sauvegarde**, il n'y a pas de restauration possible : créer de nouveaux certificats ([certificats](#certificats)), désinstaller CleanFrame (`python3 ma-tv/tv.py uninstall`, réglages perdus), vider `sign.author_sha256`, puis refaire la [première installation](#première-installation). Garder `.local/ma-tv.json` : l'identité de l'app peut rester la même après une désinstallation (**non vérifié**).

## Tout désinstaller

Procédure complète et ordonnée (app, mode développeur, appairage, Mac) : [retour-arriere](retour-arriere.md).
