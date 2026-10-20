# Modifications de la branche `ma-tv`

Tout ce que la branche `ma-tv` change par rapport à la version de l'auteur ([nthnclrk/CleanFrame](https://github.com/nthnclrk/CleanFrame), branche `main`), commit par commit, avec la raison et les fichiers. Base de la branche : `fa537d1`. Pour relire le détail : `git log --stat fa537d1..ma-tv`.

**Principe :** les fichiers de l'auteur restent intacts, sauf quelques lignes **marquées d'un commentaire `ma-tv`** dans `app/device.js` et `app/main.js`, et deux fichiers ajoutés dans `app/`. Les autres adaptations (CSS, polices, `config.xml`, `index.html`) sont faites par `ma-tv/build.py` **sur une copie** (`dist/ma-tv/stage/`), au moment du build. Aucun script de l'auteur n'est exécuté.

## Commits

Du plus ancien au plus récent.

| # | Commit | Sujet | Pourquoi | Fichiers |
| --- | --- | --- | --- | --- |
| 1 | `26975d7` | Retirer `scripts/native-home` | Outil de l'auteur qui réaffecte le bouton Home en écrivant des clés système non documentées, via une injection de commande. Verrouillé sur sa The Frame et son firmware, écrit pour .NET 6 (Tizen 6.0 n'a que .NET Core 3.1), sauvegarde de restauration privée : risque d'accueil inutilisable sans retour arrière sur l'UE43AU7105 | `scripts/native-home/*` (supprimés). `ma-tv/build.py` refuse de construire si le dossier réapparaît |
| 2 | `be6f06b` | Réglages locaux pour la TV d'Alexis | Le code de l'auteur vise une The Frame australienne sous Tizen 9 : apps, IDs système et bouton Art Mode n'existent pas tels quels ici. Sans `window.CleanFrameLocal` (aperçu de l'auteur), rien ne change | `app/ma-tv-config.js` (nouveau) ; `app/device.js` (`SELF` lu à l'exécution, IDs système configurables, repli `'hide'`) ; `app/main.js` (apps de marque et contrôles d'accueil pris dans la config locale ; appui OK/Retour « tenu » qui expire après 700 ms, au cas où la TV n'envoie pas `keyup`) |
| 3 | `e7f4993` | Espacement flex `gap` pour Chromium 76 | Chromium 76 lit `gap` mais ne l'applique pas aux conteneurs flex (Chrome 84). Sans correction, tout l'espacement de l'interface disparaît. `@supports` répond vrai à tort : détection géométrique | `app/compat-tizen6.js` (nouveau) |
| 4 | `1d27294` | Listes d'apps locales | Les filtres de l'auteur (catalogue australien, IDs à 10 caractères) peuvent masquer des apps de cette TV dans « All apps » | `app/device.js` (`STREAMING`, `CONSUMER_SYSTEM`, `INTERNAL` extensibles depuis la config locale) |
| 5 | `6c423bb` | Build du paquet Tizen 6.0 | Construire un `.wgt` pour Tizen 6.0 **sans exécuter le code de l'auteur** : barrières (privilèges, réseau, CSS/JS inconnus de Chromium 76, retour de `native-home`), `inset` → `top/right/bottom/left`, `:focus-visible` → `:focus`, polices variables → graisses fixes (Chromium 76 affichait Manrope en 200), `config.xml` avec l'identité d'Alexis, `required_version` et `devel.api.version` 6.0. Paramètres privés dans `.local/ma-tv.json`, rien en dur | `ma-tv/build.py`, `ma-tv/lib.py`, `ma-tv/config.example.json`, `ma-tv/assets/fonts/*` (Manrope 400/500/600, Geist 300/400, licences OFL, `SOURCES.json`), `ma-tv/tools/static-fonts.py` |
| 6 | `f0e653d` | Recette Chromium 76 / Chrome de référence et inspection TV | Tester le paquet construit dans le moteur de la TV avant toute installation : 14 écrans comparés à ±4 px avec un Chrome récent, touches (keyCode réels dont 10009), app absente, lancement muet, catalogue en échec, sans API Tizen, reprise, persistance, rafales, temps de démarrage. Client DevTools sans dépendance npm | `ma-tv/harness/cdp.mjs`, `page-init.js` (API Tizen imitée strictement), `run.mjs`, `tv-inspect.mjs` |
| 7 | `383455c` | Signature, commandes TV et mise à jour en une commande | Alexis veut une seule commande. `sign.py` : CLI Samsung, même certificat auteur exigé, expiration contrôlée, archive pour le retour arrière. `tv.py` : chaque commande TV affichée et confirmée (sauf `--yes`), garde-fou d'identité via `:8001`, `tizen install/run/uninstall` avec replis Samsung. `update.py` + `ma-tv/maj` : récupération → fusion temporaire → barrières → recette → signature → installation → retour arrière automatique | `ma-tv/sign.py`, `ma-tv/tv.py`, `ma-tv/update.py`, `ma-tv/maj` |
| 8 | `720889f` | Accueil d'Alexis et préférences robustes | IDs relevés sur la TV (`applist` du 2026-10-20). Accueil : YouTube, Netflix, Plex, ARTE, france.tv, Apple TV, Twitch, DAZN, RMC Sport ; M6+ dans « All apps ». `defaultHome` (9 au plus) séparé des apps de marque ; `extraApps` nommées dès le démarrage ; `serialise()` enregistre aussi les apps de marque, pour qu'un changement de config ne retire aucune tuile. Une espace rétablie dans une ligne de l'auteur, pour éviter un conflit de fusion | `app/ma-tv-config.js`, `app/main.js` |
| 9 | `b002f3a` | Polyfill `gap` synchronisé avec les mesures de l'auteur | L'auteur mesure parfois juste après un `innerHTML`, avant que l'observateur ne passe : sur un moteur sans flex gap (seulement), `getBoundingClientRect` applique d'abord les marges en attente. Classe `html.cf-no-flexgap` pour les règles CSS que le build génère pour les pseudo-éléments | `app/compat-tizen6.js` |
| 10 | `3af9499` | Corrections de la revue adversariale | Revue critique du code : 44 constats, **34 confirmés, tous corrigés** (détail ci-dessous) | `ma-tv/build.py`, `ma-tv/harness/run.mjs`, `ma-tv/lib.py`, `ma-tv/sign.py`, `ma-tv/tv.py`, `ma-tv/update.py` |
| 11 | `f44ff3e` | Télécommande réseau | La Smart Remote n'a pas de chiffres et taper 12345 ne réagissait pas : envoi des touches par le canal `samsung.remote.control` (`wss` port 8002), autorisation à l'écran la 1re fois, jeton gardé dans `.local/`. Saisie de texte possible quand le clavier de la TV est ouvert | `ma-tv/tools/remote.mjs` (nouveau) |
| 12 | `70c97e9` | L'anti-fuite couvre aussi l'identité de l'app | Le package ID (et donc `<APP_ID>` et `widget_id`) ne doit jamais partir sur le fork public | `ma-tv/update.py` (`leak_check`) |
| 13 | `e5de6ef` | Inspecteur TV utilisable et mesure en deux temps | Sur cette TV, `sdb shell 0 debug` ne répond pas si l'app tourne déjà : `was_kill` d'abord (comme Samsung Wits), puis lecture du port au fil de l'eau. `tv-inspect.mjs` sépare « accueil utilisable » (focus visible) et « écran complet » (photo et polices) : 0,5-0,65 s et 3,7-3,9 s mesurés | `ma-tv/tv.py` (`debug`), `ma-tv/harness/tv-inspect.mjs` |
| 14 | après `e5de6ef` | Branche désignée sans ambiguïté | La branche `ma-tv` porte le même nom que le dossier `ma-tv/` : les commandes git de `update.py` utilisent `refs/heads/ma-tv` et `--` pour ne jamais confondre branche et chemin | `ma-tv/update.py` (`BRANCH`) |
| 15 | après `e5de6ef` | Documentation | Index, procédure pas à pas, résultats, risques, plans B, retour arrière, compatibilité et cette liste, à jour du code et des mesures du 2026-10-20 | `ma-tv/README.md`, `ma-tv/docs/*.md` |

### Détail du commit 10 (revue adversariale)

| Fichier | Corrections |
| --- | --- |
| `ma-tv/update.py` | git lancé en locale C (les conflits n'étaient pas reconnus avec un git en français) ; échec de fusion détecté par le code retour, les fichiers non fusionnés **et** `MERGE_HEAD` ; nettoyage garanti de la branche temporaire ; **`ma-tv` n'avance qu'après validation sur la TV** (TV éteinte → le `maj` suivant refait tout) ; anti-fuite sur les fichiers suivis **et** sur l'historique à pousser, **avant** la signature ; push en échec signalé ; un refus d'installation n'est pas un échec du lancement (pas de retour arrière inutile) |
| `ma-tv/tv.py` | garde-fou d'identité dans chaque processus, même si une connexion sdb existe déjà ; échecs de `tizen install` détectés malgré un « successfully » ; retour arrière vers la dernière version **validée** (installée et lancée), et non plus vers l'archive précédente quelle qu'elle soit ; `install-permit` vérifié (profil actif = `<PROFIL>`, sortie « permitted ») ; identité jamais inventée hors du build |
| `ma-tv/build.py` | analyse JS qui vide chaînes, commentaires et littéraux regex (plus de désynchronisation) ; barrières CSS ancrées sur les déclarations ; nouvelles barrières (masques sans `-webkit-`, `:not()` en liste, propriétés logiques, `@media` par intervalle, `translate/rotate/scale`…) ; `inset` avec `calc()`/`var()` laissé à la barrière au lieu d'un découpage hasardeux ; commentaires CSS jamais réécrits ; `config.xml` échappé puis vérifié élément par élément ; toute erreur due à un changement de forme en amont → arrêt propre |
| `ma-tv/lib.py` | délai dépassé → tout le groupe de processus est tué (le CLI `tizen` lance un Java enfant) ; IP du Mac lue en direct et comparée à celle enregistrée ; erreurs imprévues journalisées |
| `ma-tv/sign.py` | lecture du Trousseau avec délai (session verrouillée) ; `openssl` obligatoire pour lire les dates (sinon refus de signer) |
| `ma-tv/harness/run.mjs` | attentes de la recette lues dans la config réellement construite (`dist/ma-tv/stage/ma-tv-config.js`), et non codées en dur |

## Lignes marquées `ma-tv` dans les fichiers de l'auteur

Relevées le 2026-10-20 (`grep -n "ma-tv" app/device.js app/main.js`). À garder lors de la résolution d'un conflit de fusion.

| Fichier:ligne | Rôle |
| --- | --- |
| `app/device.js:19-22` | Lit `window.CleanFrameLocal` (IDs de marque `ids`, `selfId`, `system`) |
| `app/device.js:23-26` | Complète `STREAMING`, `CONSUMER_SYSTEM`, `INTERNAL` depuis la config locale |
| `app/device.js:27-28` | `SELF` = ID réel de l'app installée (`getCurrentApplication().appInfo.id`) |
| `app/device.js:60-68` | IDs « Samsung Home » et « TV settings » configurables ; `'hide'` met l'app en arrière-plan |
| `app/main.js:27-29` | Apps de marque prises dans `CleanFrameLocal.primaryApps` |
| `app/main.js:31-32` | `extraApps` : autres apps de la TV, nommées dès le démarrage |
| `app/main.js:346-347` | Accueil du premier lancement = `defaultHome` (9 au plus) |
| `app/main.js:366-367` | `serialise()` enregistre aussi les apps de marque |
| `app/main.js:501-502` | Contrôles d'accueil masquables (`hideUtils`, Art Mode masqué ici) |
| `app/main.js:1842-1843` | Appui OK/Retour « tenu » expiré après 700 ms sans répétition |

Fichiers ajoutés dans `app/` : `app/ma-tv-config.js` (réglages de la TV d'Alexis) et `app/compat-tizen6.js` (polyfill `gap`). Fichiers de l'auteur **non modifiés** : `app/index.html`, `app/config.xml`, `app/style.css`, les polices et images, `scripts/` (hors `native-home`, supprimé), `AGENTS.md` et la documentation de l'auteur.

## Adaptations faites au paquet par `ma-tv/build.py`

Appliquées à la copie `dist/ma-tv/stage/`, jamais aux fichiers de `app/`. Comptes du dernier build (`dist/ma-tv/build.json`).

| Adaptation | Pourquoi |
| --- | --- |
| `config.xml` : identité d'Alexis (`widget id`, `package`, `<APP_ID>`, `name`), `required_version` 6.0, `devel.api.version` 6.0 ajoutée, puis vérification | La TV refuse `required_version` 6.5 (mesuré) ; identité propre pour ne pas entrer en collision avec l'app de l'auteur |
| `index.html` : `ma-tv-config.js`, `ma-tv-gap.js`, `compat-tizen6.js` injectés avant `device.js` | Réglages locaux et polyfill chargés avant le code de l'auteur |
| `ma-tv-config.js` : section `"local"` de `.local/ma-tv.json` fusionnée par-dessus | Replis sans toucher au code ([plan-b](plan-b.md)) |
| `ma-tv-gap.js` : 35 sélecteurs qui déclarent un `gap` | Liste lue par le polyfill |
| CSS : `inset` ×6 → `top/right/bottom/left` ; `:focus-visible` ×2 → `:focus` ; 1 règle de marge pour un pseudo-élément flex (`html.cf-no-flexgap`) | Absents de Chromium 76 |
| Polices : Manrope et Geist en graisses fixes (`assets/fonts/ma-tv-static/`) ; fichiers variables retirés | Chromium 76 ignore les variations de graisse |
| Exclusions identiques à `scripts/font_assets.py` de l'auteur (outils de rendu, polices propriétaires `PP*`, `assets/private-fonts/`) ; `LICENSE` et `THIRD_PARTY_NOTICES.md` copiés | Paquet sans fichier non redistribuable |

## Ce qui n'est pas dans git

`.local/` (configuration privée, identité, jeton, navigateurs de recette, archives signées, journaux, rapports) et `dist/` (paquets) sont ignorés par git. Les certificats vivent dans `~/SamsungCertificate/` et `~/tizen-studio-data/`, hors du dépôt.
