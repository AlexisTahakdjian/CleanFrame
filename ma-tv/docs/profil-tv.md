# Fiche profil de ma TV

Samsung **UE43AU7105KXXC** (Crystal UHD AU7100, 2021) : la TV cible de la branche `ma-tv`.

Relevés faits le **2026-10-20**. Les valeurs privées (adresses IP, identifiant réseau, DUID, identifiant de l'app, jeton, empreintes de certificats) ne figurent pas ici : elles restent dans `.local/ma-tv.json` et `~/SamsungCertificate/`, hors de git. Dans ce document, `<IP_TV>`, `<IP_MAC>`, `<APP_ID>` et `<PROFIL>` les remplacent.

**Statuts utilisés**

| Statut | Sens |
| --- | --- |
| mesuré sur la TV | Lu ou constaté sur cette TV le 2026-10-20 (`:8001/api/v2/`, `sdb`, inspecteur, menus, essai à la télécommande) |
| mesuré sur le Mac | Constaté sur le Mac de développement |
| mesuré dans la recette | Constaté dans Chromium 76 de bureau (`ma-tv/harness/run.mjs`), **pas** sur la TV |
| vérifié (source officielle) | Écrit par Samsung ou Tizen, non mesuré ici |
| source non officielle | Forum, revendeur, projet tiers |
| **non vérifié** | Ni mesuré ni confirmé par une source |

## 1. Identité et système

| Champ | Valeur | Source | Statut |
| --- | --- | --- | --- |
| Modèle commercial | UE43AU7105KXXC | `GET http://<IP_TV>:8001/api/v2/` → `device.modelName` | mesuré sur la TV |
| Gamme, année | Crystal UHD AU7100, 2021 | [Support Samsung FR](https://www.samsung.com/fr/support/model/UE43AU7105KXXC/) ; champ `model` en `21_…` | vérifié (source officielle) + mesuré |
| Code plateforme (`model`) | `21_KANTSU2E_UHD_BASIC` | `/api/v2/` → `device.model` | mesuré sur la TV |
| Groupe de modèles Samsung | Probablement `21TV_BASIC1` : la ligne cite « UAU7000 » | [TV Model Groups](https://developer.samsung.com/smarttv/develop/specifications/tv-model-groups.html) | **non vérifié** pour l'AU7105 précisément |
| Système (`OS`) | « Tizen », sans numéro de version | `/api/v2/` → `device.OS` | mesuré sur la TV |
| **Version de plateforme** | **6.0** | `sdb capability` → `platform_version` | mesuré sur la TV |
| `product_version` | 4.0 | `sdb capability` | mesuré sur la TV (sens non documenté) |
| Firmware selon `/api/v2/` | « Unknown » | `/api/v2/` → `firmwareVersion` | mesuré sur la TV |
| Firmware selon le menu | T-KSU2EDEUC-2301.1 | Paramètres → Assistance → À propos de ce téléviseur | mesuré sur la TV |
| Dernier firmware publié | 2301.1 (fichier `T-KSU2EDEUC.zip`, daté du 28/01/2026) : la TV est à jour | [Support Samsung FR](https://www.samsung.com/fr/support/model/UE43AU7105KXXC/) | vérifié (source officielle) |
| **Moteur web** | Chromium **M76** (76.0.3809.146, fork Samsung) | [Web Engine Specifications](https://developer.samsung.com/smarttv/develop/specifications/web-engine-specifications.html) (2021 / Tizen 6.0 / M76) et User-Agent réel | vérifié (source officielle) + **mesuré sur la TV** |
| User-Agent réel | `Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) 76.0.3809.146/6.0 TV Safari/537.36` : identique à la doc Samsung | `navigator.userAgent` via l'inspecteur (`ma-tv/harness/tv-inspect.mjs`) ; [Retrieving Platform Information](https://developer.samsung.com/smarttv/develop/guides/fundamentals/retrieving-platform-information.html) | mesuré sur la TV |
| Runtime .NET | .NET Core 3.1 (TizenFX TV 8.8.0) | [TV Extension, release history](https://developer.samsung.com/smarttv/develop/tools/tv-extension/release-history.html) | vérifié (source officielle) ; non mesuré (ma-tv n'en a pas besoin) |
| Architecture | `armv7` (ARM 32 bits) | `sdb capability` → `cpu_arch` | mesuré sur la TV |
| Processeur | « Crystal Processor 4K » ; `navigator.hardwareConcurrency` = 4 | Fiche commerciale ; inspecteur | mesuré sur la TV (4 cœurs logiques vus par le moteur ; fréquence et modèle **non vérifiés**) |
| Mémoire vue par le moteur | `navigator.deviceMemory` = 1 (valeur arrondie par le navigateur, en Go) | Inspecteur | mesuré sur la TV |
| Dalle | 3840x2160 | `/api/v2/` → `resolution` | mesuré sur la TV (taille de la dalle, pas de la zone de rendu des apps) |
| **Zone de rendu des apps web** | `innerWidth` × `innerHeight` = **1920 × 1080** ; `screen` = 1920 × 1080 ; `devicePixelRatio` = **1** | Inspecteur ; [Managing Screen Resolution](https://developer.samsung.com/smarttv/develop/guides/fundamentals/managing-screen-resolution.html) | mesuré sur la TV (conforme à la doc Samsung) |
| Flex `gap` natif | Absent : le polyfill `app/compat-tizen6.js` s'active (`CleanFrameCompat.flexGap` = `polyfill`) | Inspecteur | mesuré sur la TV |
| Polices de ma-tv | Manrope en graisses fixes chargée (`document.fonts.check('500 32px Manrope')` = vrai) | Inspecteur | mesuré sur la TV |
| `FrameTVSupport` | false | `/api/v2/` | mesuré sur la TV |
| Identifiant réseau (`device.id`) | Identifiant de format UUID, gardé dans `.local/ma-tv.json` (`tv.udn`) pour le garde-fou `guard_tv`. **Ce n'est pas le DUID** des certificats (voir § 5, n° 17) | `/api/v2/` | mesuré sur la TV (valeur volontairement absente) |
| Réseau | Wi-Fi (`networkType` = wireless) | `/api/v2/` | mesuré sur la TV (nom du réseau volontairement absent) |
| Pays, langue | FR, fr_FR | `/api/v2/` → `countryCode`, `Language` | mesuré sur la TV |
| `TokenAuthSupport` | true | `/api/v2/` | mesuré sur la TV |
| Format de `/api/v2/` | JSON avec des caractères de contrôle bruts : un parseur JSON strict échoue. `ma-tv/lib.py` le lit avec `strict=False` | `ma-tv/lib.py` (`tv_api`) | mesuré sur la TV |
| Documentation de `/api/v2/` | Point d'accès cité par Samsung, schéma non documenté | [Smart View, Debugging](https://developer.samsung.com/smarttv/develop/extension-libraries/smart-view-sdk/receiver-apps/debugging.html) | vérifié (source officielle) |

## 2. Capacités `sdb` (mode développeur)

Valeurs **mesurées sur la TV** (`python3 ma-tv/tv.py capability`), enregistrées dans `.local/ma-tv.json` (`tv.capability`). Aucune doc officielle ne décrit ces champs : leur interprétation vient de forums (source non officielle), sauf quand l'essai l'a tranchée.

| Champ | Valeur | Conséquence pour ma-tv |
| --- | --- | --- |
| `platform_version` | 6.0 | Cible Tizen 6.0 / Chromium 76. Tranche la contradiction 5.5 / 6.0 (§ 5) |
| `profile_name` / `can_launch` | `tv` / `tv-samsung` | Profil TV Samsung, cohérent avec `config.xml` |
| `vendor_name` | Samsung | — |
| `cpu_arch` | armv7 | 32 bits |
| `sdbd_rootperm` / `rootonoff_support` | disabled / disabled | Pas de root via sdb |
| `intershell_support` | disabled | Pas de `sdb shell` interactif : seules les commandes `sdb shell 0 <verbe>` passent. On ne peut pas effacer un fichier poussé sur la TV |
| `appcmd_support` | disabled | **Sans effet constaté** : `shell 0 applist`, `shell 0 vd_appinstall`, `shell 0 was_kill` et `shell 0 debug` fonctionnent (mesuré sur la TV) |
| `pkgcmd_debugmode` / `netcoredbg_support` | enabled / enabled | Lancement en mode inspecteur possible : `tv.py debug` marche, à condition d'arrêter l'app d'abord (`was_kill`, mesuré) |
| `appid2pid_support` | enabled | — |
| `filesync_support` | pushpull | `sdb push` possible (repli d'installation `vd_appinstall`, mesuré) |
| `secure_protocol` | enabled | — |
| `multiuser_support` / `zone_support` | enabled / disabled | — |
| `encryption_support` / `usbproto_support` / `sockproto_support` / `syncwinsz_support` | disabled / disabled / enabled / enabled | — |
| `log_enable` / `log_path` | disabled / `/tmp` | Pas de journal accessible |
| `sdk_toolpath` | `/home/owner/share/tmp/sdk_tools` | `tizen install` y transfère le paquet (sous-dossier `tmp/`) ; le repli de `tv.py` y pousse `ma-tv-cleanframe.wgt` (mesuré) |
| `sdbd_version` / `sdbd_plugin_version` / `sdbd_cap_version` | 2.2.31 / 3.8.4_TV_REL / 1.0 | — |

## 3. Applications installées

`sdb shell 0 applist` fonctionne et renvoie 393 lignes (**mesuré sur la TV**). Copie locale : `.local/tv-applist.txt` (non suivie par git).

| Rôle | Nom | ID d'application | Statut |
| --- | --- | --- | --- |
| **CleanFrame (ma-tv)** | CleanFrame | `<APP_ID>` | installée et lancée le 2026-10-20 (mesuré) |
| Accueil Samsung (« Samsung Home ») | — | `com.samsung.tv.csfs` | présente ; **ouverte depuis CleanFrame** (« Leave Home? » → « Samsung Home » ouvre Smart Hub, mesuré à la télécommande) |
| Réglages TV | — | `com.samsung.tv.coba.setting` | présente (mesuré) ; ouverture depuis l'entrée « TV settings » de CleanFrame **non vérifiée** |
| Art | « ArtApp » | `org.tizen.art-app` | présente (mesuré) **malgré** `FrameTVSupport=false` ; bouton masqué dans ma-tv (`hideUtils: ['art']`) ; comportement **non testé** |
| Streaming | YouTube | `9Ur5IzDKqV.TizenYouTube` | présente ; **lancée depuis CleanFrame** (mesuré) |
| | Netflix | `org.tizen.netflix-app` | présente ; **lancée depuis CleanFrame** ; Retour/Exit dans Netflix ramène à Samsung Home, pas à CleanFrame (mesuré) |
| | Prime Video | `org.tizen.primevideo` | présente (mesuré) ; lancement depuis CleanFrame **non vérifié** |
| | Disney+ | `MCmYXNxgcu.DisneyPlus` | présente (mesuré) ; lancement **non vérifié** |
| | Apple TV | `com.samsung.tv.aria-video` | présente (mesuré) ; lancement **non vérifié** |
| | Plex | `kIciSQlYEM.plex` | présente (mesuré) ; lancement **non vérifié** |
| | ARTE | `aLlph042JZ.arte` | présente (mesuré) ; lancement **non vérifié** |
| | france.tv | `QY16tZ64E3.francetv` | présente (mesuré) ; lancement **non vérifié** |
| | M6+ | `Ol7HVEXtqh.6play` | présente (mesuré) ; dans « All apps » de CleanFrame |
| | TF1+ | `E0P3lRI4H7.MYTF1` | présente (mesuré) |
| | Molotov | `bstjKvX6LM.molotov` | présente (mesuré) |
| | Twitch, DAZN, RMC Sport | voir `app/ma-tv-config.js` (`extraApps`) | présentes (mesuré) ; lancement **non vérifié** |
| | CANAL+ (2 ID), OCS, Spotify… | voir `.local/tv-applist.txt` | présentes (mesuré) |

**Accueil de CleanFrame au premier lancement** (`defaultHome` dans `app/ma-tv-config.js`) : YouTube, Netflix, Plex, ARTE, france.tv, Apple TV, Twitch, DAZN, RMC Sport. Neuf apps, le maximum de l'auteur (`CAP = 9` dans `app/main.js`). M6+ reste dans « All apps ». Mesuré sur la TV : cet accueil s'affiche tel quel.

## 4. Télécommande, accès et poste de développement

| Champ | Valeur | Source | Statut |
| --- | --- | --- | --- |
| Télécommande | Smart Remote ; taper 12345 à la main dans le panneau Apps n'a rien déclenché | Essai du propriétaire | mesuré sur la TV ; modèle exact **non vérifié** (une fiche du modèle voisin UE43AU7100KXXU cite la TM2140A : source non officielle) |
| Activation du mode développeur | Code KEY_1…KEY_5 envoyé depuis le Mac par la télécommande réseau `wss://<IP_TV>:8002` (`ma-tv/tools/remote.mjs`), panneau Apps affiché. Invite d'autorisation acceptée une fois sur la TV : **elle expire au bout d'environ 30 s**. Le propriétaire a ensuite saisi lui-même `<IP_MAC>` dans « Host PC IP », validé, puis redémarré la TV (appui long sur Marche) | Essai | mesuré sur la TV |
| Connexion sdb | `sdb connect <IP_TV>:26101`, puis `capability`, `applist`, installation, lancement, inspecteur : OK | `ma-tv/tv.py` | mesuré sur la TV |
| Mac appairé (télécommande réseau) | Nom « CleanFrame Mac » ; jeton dans `.local/ma-tv.json` (`tv.remote_token`) | `ma-tv/tools/remote.mjs` | mesuré sur la TV |
| Accès « Réseau local » de macOS | Accordé à iTerm. Avant : Node et Python échouaient en `EHOSTUNREACH` (« No route to host ») ; curl passait (exempté) | Réglages Système → Confidentialité et sécurité → Réseau local | mesuré sur le Mac |
| Mac | Apple Silicon, macOS 27, Rosetta 2 installé ; Node 26, Python 3.10 | — | mesuré sur le Mac |
| Rosetta | macOS 27 est la dernière version avec Rosetta complet | [Apple, Rosetta](https://developer.apple.com/documentation/apple-silicon/about-the-rosetta-translation-environment) | vérifié (source officielle) |
| Outils Samsung | Tizen Studio 6.1 « web-cli » dans `~/tizen-studio`, plus les paquets `cert-add-on` 2.0.75 (Samsung Certificate Extension), `TV-SAMSUNG-Extension-Tools` et `-Resources` 10.0.0, `WebIDE` 3.1.3 ; `sdb` 4.2.36. Binaires x86_64 sous Rosetta. `WebIDE` est **nécessaire** : il fournit l'application de base de Certificate Manager (avec `cert-add-on` seul, `Certificate-manager.app` restait incomplète) | `~/tizen-studio/.info/installedpackage.list` | mesuré sur le Mac |
| Certificats | Profil `<PROFIL>` (`MaTV`), type Samsung → TV, privilège Public. Auteur émis par « Samsung VD Author CA », distributeur par « VD DEVELOPER Public CA Class ». **Validité d'un an pour les deux : expiration le 2027-10-20** | Certificate Manager ; dates lues par `ma-tv/sign.py` | mesuré sur le Mac |
| Autorisation d'installation | `tizen install-permit` → « Install Permitted » | `python3 ma-tv/tv.py permit` | mesuré sur la TV |
| Moteurs de la recette | Chromium 76.0.3809.0 (snapshot officiel r665002, x86_64 sous Rosetta) et Chrome for Testing 155.0.8059.84 (`chrome-headless-shell`, arm64) comme référence | `ma-tv/harness/run.mjs` | mesuré sur le Mac |
| Chrome installé sur le Mac | Chrome 118 plante en mode headless sous macOS 27 : la référence est donc le `chrome-headless-shell` officiel dans `.local/chrome-ref/` | Essai | mesuré sur le Mac |

## 5. Contradictions entre la TV et Internet

| # | Ce que disent Internet ou la doc | Ce que montre la TV ou la mesure | Conclusion |
| --- | --- | --- | --- |
| 1 | Revendeur [kitele.com](https://www.kitele.com/es/televisor-samsung-ue43au7105) : Tizen 5.5 (source non officielle) | `platform_version` = 6.0 et User-Agent « Tizen 6.0 » (mesuré). Samsung associe aussi 2021 à Tizen 6.0 ([TV Model Groups](https://developer.samsung.com/smarttv/develop/specifications/tv-model-groups.html)) | **Tizen 6.0.** La fiche du revendeur est fausse |
| 2 | `/api/v2/` est censé décrire l'appareil | `firmwareVersion` = « Unknown » ; le menu affiche T-KSU2EDEUC-2301.1 (mesuré) | Lire le firmware dans le menu, jamais dans `/api/v2/` |
| 3 | `/api/v2/` donne `resolution` 3840x2160 | Les apps web voient 1920 × 1080, DPR 1 (mesuré) | **Tranché :** 3840x2160 décrit la dalle ; la scène 1920×1080 de l'auteur s'affiche à l'échelle 1 |
| 4 | `FrameTVSupport` = false : pas de mode Art | `org.tizen.art-app` (« ArtApp ») est installée (mesuré) | Bouton Art masqué (`hideUtils: ['art']`). Ne pas tester sans raison |
| 5 | Doc Samsung : « saisir 12345 » avec la télécommande dans Apps ([TV Device](https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-device.html)) | Avec la Smart Remote, la saisie manuelle n'a rien fait. Les touches envoyées par le réseau ont marché (mesuré) | Pour activer ou désactiver le mode développeur, utiliser `ma-tv/tools/remote.mjs` |
| 6 | Deux pages Samsung donnent des chemins différents : « Apps → App Settings » contre « Apps → My Apps » ([Debugging](https://developer.samsung.com/smarttv/develop/extension-libraries/smart-view-sdk/receiver-apps/debugging.html)) | Le panneau Apps a reçu le code (mesuré) | Libellé exact du menu de cette TV **non vérifié** |
| 7 | Tableau Samsung des moteurs web : « No » en 6.0 pour `prefers-reduced-motion` et `font-variation-settings`, ainsi que pour `ResizeObserver` et `linear-gradient` | MDN et caniuse : présents dans Chrome 74, 62, 64 et 26, donc dans M76 | Tableau Samsung peu fiable, fonction par fonction (voir [compatibilité](compatibilite.md)) |
| 8 | MDN et caniuse : polices variables prises en charge depuis Chrome 62/66 ([caniuse](https://caniuse.com/variable-fonts)) | Recette : Chromium 76 ignore les variations de graisse, Manrope s'affiche à sa graisse par défaut (200). Samsung indique « No ». Sur la TV, les graisses fixes de ma-tv sont chargées (mesuré) | Ici, le tableau Samsung avait raison : ma-tv utilise des graisses fixes |
| 9 | [FAQ Samsung Q19](https://developer.samsung.com/smarttv/develop/faq/specifications-and-feature-support.html) : « SVG images are not supported » | Chromium 76 affiche les masques SVG de l'app (mesuré dans la recette). Sur la TV, l'accueil a été jugé correct à la télécommande, sans relevé dédié des logos | Rendu des logos SVG sur la TV **non vérifié** formellement ; plan B dans [plan-b](plan-b.md) |
| 10 | FAQ Q13 : une app « se lance » sur une plateforme plus ancienne. FAQ [Baseline SDK](https://developer.samsung.com/tizen/Smart-TV/FAQ/Tizen-baseline-SDK.html) : refus « CheckTizenVersion » (cas .tpk) | Test A/B (mesuré) : même paquet, seul `required_version` change. **6.5 → refusé** par `tizen install` et par `vd_appinstall` : « install failed[118, -19], reason: Parsing error ». **6.0 → « install completed »**, app présente dans `applist` | **Tranché :** abaisser `required_version` à 6.0 était nécessaire (mais pas suffisant : il fallait aussi les corrections CSS et polices) |
| 11 | Samsung : Certificate Extension ≥ 2.0.73 requise depuis septembre 2025 ([Installing TV SDK](https://developer.samsung.com/smarttv/develop/getting-started/setting-up-sdk/installing-tv-sdk.html)). Forum Samsung : ≥ 2.0.74 (extrait, non officiel) | 2.0.75 installée ; certificats créés et acceptés par la TV (mesuré) | Conditions remplies |
| 12 | Support Samsung : « Autorun Last App » existe sur les modèles 2017-2021 ([page Samsung](https://www.samsung.com/ae/support/tv-audio-video/use-autorun-start-screen-options-on-your-samsung-tv/)) | Essai du propriétaire : Autorun Last App n'a **pas** fait démarrer la TV sur CleanFrame. Après 1 min de veille puis rallumage : Samsung Home / la TV, CleanFrame non reprise (mesuré) | Ne pas compter sur Autorun Last App. Repli qui marche : épingler CleanFrame en tête du bandeau Apps ([plan-b](plan-b.md) § 9) |
| 13 | FAQ montre Samsung : un certificat expiré n'affecte pas les apps installées ([FAQ](https://developer.samsung.com/galaxy-watch-tizen/getting-certificates/faq.html)). Forum Emby : app désactivée au bout d'un mois (non officiel) | Certificats valides jusqu'au 2027-10-20 (mesuré) | Effet de l'expiration sur cette TV **non vérifié** : renouveler avant ([procédure](procedure.md#renouveler-les-certificats)) |
| 14 | README de l'auteur : The Frame 2024 = Tizen 9.0. Tableau Samsung : 2024 = Tizen 8.0 | — | Le modèle 2024 est passé de 8.0 à 9.0 par une mise à jour : écart de 44 versions de Chromium avec cette TV |
| 15 | Recette : Chromium 76.0.3809.0 de bureau | TV : 76.0.3809.146, fork Samsung (mesuré) | Même branche, correctifs Samsung en plus : la recette reste un indice, pas une preuve |
| 16 | Doc Samsung CLI : pour une TV, `tizen uninstall -p` prend l'**ID d'application** ([CLI](https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/command-line-interface.html)) | Aide du CLI installé : `-p <package id>` (mesuré sur le Mac) | `tv.py` passe `<APP_ID>` et confirme la suppression avec `applist`. Désinstallation **non testée** |
| 17 | On pourrait croire que l'identifiant `device.id` de `/api/v2/` (format UUID) est le DUID demandé par les certificats | Certificate Manager détecte un DUID différent sur la TV connectée (mesuré) | Pour le certificat distributeur, garder le DUID **pré-coché** par Certificate Manager ; ne jamais y coller `device.id` |
| 18 | `sdb capability` : `appcmd_support` = disabled | `applist`, `vd_appinstall`, `was_kill`, `debug` répondent (mesuré) | Ne pas se fier à ce champ |
| 19 | On attend qu'un Chrome récent du Mac serve de référence | Chrome 118 du Mac plante en headless sous macOS 27 (mesuré sur le Mac) | Référence = `chrome-headless-shell` officiel (Chrome for Testing) |

## 6. Mesures : faites et restantes

Outils : `python3 ma-tv/tv.py debug` (inspecteur et tunnel local), puis `node ma-tv/harness/tv-inspect.mjs --port <port>` ; chronomètre ou vidéo pour la mesure hors inspecteur ([procédure](procedure.md#vérifier-avec-linspecteur)). Chaque commande touche la TV et se lance seulement avec ton accord.

| # | Mesure | Résultat | Statut |
| --- | --- | --- | --- |
| 1 | `devicePixelRatio` | 1 | mesuré sur la TV |
| 2 | `innerWidth` × `innerHeight` | 1920 × 1080 | mesuré sur la TV |
| 3 | `screen.width` × `screen.height` | 1920 × 1080 | mesuré sur la TV |
| 4 | User-Agent réel | `… 76.0.3809.146/6.0 …`, conforme à la doc Samsung | mesuré sur la TV |
| 5 | Calibrage du bridage CPU de la recette (`harness.calibrated_throttle`) | **Pas fait.** Sur la TV, le goulot du démarrage est le pipeline d'images (rastérisation), que le bridage CPU du Chromium de bureau ne reproduit probablement pas (hypothèse). La recette rapporte ses temps sans les juger | **non vérifié** |
| 6 | Modèle de télécommande | Smart Remote (TM2140A ?) | **non vérifié** |
| 7 | Temps d'affichage | Accueil utilisable (horloge, apps, focus ; touches actives) **0,52 à 0,65 s** ; écran complet avec la photo **3,7 à 3,9 s** (inspecteur, 3 rechargements). Chronomètre du propriétaire depuis Apps → CleanFrame : accueil visible en **1 à 2 s**, lancement compris. Vidéo au ralenti : non faite | mesuré sur la TV ([résultats](resultats-tests.md)) |
| 8 | Touches OK et Retour, appui tenu | Touches OK à la télécommande. Réception d'un `keyup` après OK/Retour (`heldKeys`) non relevée | touches : mesuré ; `keyup` : **non vérifié** |
| 9 | Icônes natives (`iconPath`) | 0 erreur console sur l'accueil (3 rechargements). Écran « All apps » non observé sous inspecteur | accueil : mesuré ; « All apps » : **non vérifié** |
| 10 | Samsung Home / Réglages TV depuis l'app | « Samsung Home » ouvre Smart Hub ; « TV settings » non essayé | Samsung Home : mesuré ; TV settings : **non vérifié** |
| 11 | Démarrage automatique | Autorun Last App sans effet ; CleanFrame épinglée en tête du bandeau Apps : Home puis OK = CleanFrame (2 appuis) | mesuré sur la TV |
| 12 | Installation avec `required_version` 6.5 | Refusée : « install failed[118, -19], reason: Parsing error » | mesuré sur la TV |
| 13 | Méthode d'installation | `tizen install` marche (6.0). Le repli `sdb push` + `vd_appinstall` s'exécute aussi (essayé lors du refus en 6.5) | mesuré sur la TV |
| 14 | Dates d'expiration des certificats | Auteur et distributeur : 2027-10-20 | mesuré sur le Mac |
| 15 | `developerMode` et `developerIP` après désactivation | — | **non vérifié** (désactivation pas encore faite) |
| 16 | Espace de stockage libre | Paquet d'environ 15 Mo installé sans erreur | valeur libre **non vérifiée** |
| 17 | Comportement si le réseau est coupé | — | **non vérifié** |
| 18 | Mise à jour en place (préférences conservées) | Aucune 2e version installée par-dessus la 1re pour l'instant | **non vérifié** |
