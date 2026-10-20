# Résultats des tests

Tests du 2026-10-20 sur le paquet CleanFrame 0.6.1 construit par `ma-tv/build.py` (Tizen 6.0, 169 fichiers, 15,8 Mo). Trois sources : la **recette navigateur** sur le Mac, l'**inspecteur** sur la vraie TV, et la **recette physique** à la télécommande par Alexis. Tout ce qui n'a pas été essayé est marqué **non vérifié**.

Statuts : « mesuré sur la TV », « mesuré sur le Mac », « mesuré dans la recette » (Chromium 76 de bureau, pas la TV). Profil de la TV : [profil-tv](profil-tv.md).

## 1. Verdict des critères

| Critère | Verdict | Mesure |
| --- | --- | --- |
| **0 erreur console** | ✔ | Sur la TV : 0 erreur console ou réseau sur 2 séances de 3 rechargements de l'accueil (inspecteur). Recette : 0 erreur sur 189 vérifications dans 2 moteurs. Autres écrans sous inspecteur sur la TV (« All apps », réglages) : **non vérifié** |
| **Accueil en moins de 2 s** | ✔ pour l'accueil utilisable · ✗ pour l'écran complet avec la photo | Accueil utilisable (horloge, apps, focus ; touches actives) : **0,52 à 0,65 s** (inspecteur). Chronomètre d'Alexis depuis Apps → CleanFrame : **1 à 2 s**, lancement de l'app compris. Écran complet avec la photo : **3,7 à 3,9 s** ✗. Avec un fond Dark ou Light : 0,72 à 0,78 s. Alexis a choisi de garder la photo |
| **Touches de la télécommande** | ✔ | Flèches, OK, Retour, « All apps », Settings, « Leave Home? », « Samsung Home », lancement de YouTube, retour dans CleanFrame avec le focus conservé (§ 5) |
| **Une commande pour mettre à jour** | ✔ **mesuré** (2026-10-21) | `ma-tv/maj` exécuté de bout en bout : build, recette 216/216 (0 erreur), anti-fuite, signature, `tizen install` (« install completed »), lancement, version validée, push sur le fork. Un second `ma-tv/maj --dry-run` répond « Rien de nouveau ». Non encore vécu : une vraie nouveauté de l'auteur (fusion) — non vérifié. |

## 2. Recette navigateur (Mac)

`node ma-tv/harness/run.mjs` sur le paquet construit (`dist/ma-tv/stage/`), servi en boucle locale, avec une API Tizen imitée strictement (`ma-tv/harness/page-init.js` : tout accès hors de l'API imitée est noté).

| Élément | Résultat |
| --- | --- |
| Moteurs | Chromium **76.0.3809.0** (snapshot officiel, x86_64 sous Rosetta) et Chrome for Testing **155.0.8059.84** (`chrome-headless-shell`, référence) — mesuré sur le Mac |
| Vérifications | **189 / 189** réussies : 74 dans Chromium 76, 73 dans la référence, 42 comparaisons de mise en page (dernière recette complète du 2026-10-20) |
| Erreurs | 0 erreur console ou réseau, 0 avertissement, 0 requête externe, 0 accès à une API Tizen non imitée |
| Mise en page | 14 écrans : positions et tailles à **±4 px** de la référence, aucun élément manquant, aucun texte coupé en plus |
| Démarrage (bridage CPU ÷4) | Chromium 76 : écran prêt médian 2,19 à 2,32 s, FCP médian ≈ 1,1 s. Référence : 0,14 à 0,16 s. **Non jugé** : le bridage n'est pas calibré sur la TV, et le goulot de la TV (pipeline d'images) n'est probablement pas reproduit (hypothèse) |

Écrans comparés : accueil Dock (icônes et noms, icônes seules, noms seuls), contrôles d'accueil, accueil List (avec et sans contrôles, noms seuls), fonds sombre et clair, « Leave Home? », « All apps », Settings, Appearance, éditeur de l'accueil. Chaque écran exige un seul focus visible et aucune erreur.

Scénarios fonctionnels : keyCode reçus identiques à la télécommande Samsung (37, 38, 39, 40, 13, 10009) ; navigation de l'accueil (ordre = `defaultHome`, bords sans bouclage, contrôles, « Leave Home? ») ; niveaux de Retour ; OK lance la bonne app ; OK maintenu = un seul lancement ; app absente → message propre et touches qui remarchent ; TV muette 8 s → « The TV did not respond » ; catalogue en échec puis « Try again » ; « Samsung Home » vers la cible configurée ; navigateur sans API Tizen → message, pas d'exception ; touches non gérées sans effet ; rafales de touches et flèche maintenue ; masquage puis reprise ; réglages conservés après relance.

Limites : moteur de bureau (pas le fork Samsung 76.0.3809.146), GPU désactivé, Rosetta, API Tizen imitée. La recette est une barrière, pas une preuve.

## 3. Sur la TV, par l'inspecteur

`python3 ma-tv/tv.py debug` puis `node ma-tv/harness/tv-inspect.mjs --port <port> --reloads 3` ([procédure](procedure.md#vérifier-avec-linspecteur)). Mesures sous inspecteur : un peu plus lentes qu'en usage normal.

| Élément | Valeur (mesuré sur la TV) |
| --- | --- |
| Moteur | `Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) 76.0.3809.146/6.0 TV Safari/537.36`, identique à la doc Samsung |
| Zone de rendu | `innerWidth` × `innerHeight` 1920 × 1080 ; `screen` 1920 × 1080 ; `devicePixelRatio` 1 |
| Matériel vu par le moteur | `navigator.hardwareConcurrency` 4 ; `navigator.deviceMemory` 1 |
| Compatibilité ma-tv | Polyfill `gap` actif (`polyfill`) ; Manrope en graisses fixes chargée (`document.fonts.check` vrai) |
| Erreurs | **0** erreur console ou réseau, sur les deux séances |

| Rechargement (2e séance) | Accueil utilisable | Écran complet (photo) | FCP |
| --- | --- | --- | --- |
| 1 | 646 ms | 3 927 ms | 276 ms |
| 2 | 614 ms | 3 784 ms | 240 ms |
| 3 | 522 ms | 3 742 ms | 232 ms |

1re séance (avant la mesure en deux temps) : FCP 310, 225 et 247 ms ; écran complet atteint 3,6 à 4,1 s après le rechargement. Au total, FCP entre 225 et 310 ms.

Hors inspecteur, chronomètre d'Alexis, depuis le bandeau Apps → CleanFrame : accueil visible en **1 à 2 s**, lancement de l'app compris. Vidéo au ralenti : **non faite**.

## 4. Enquête sur le démarrage avec la photo

Pourquoi l'écran complet attend 3,7-3,9 s alors que l'accueil est prêt en 0,5-0,65 s. Essais faits sur la TV sous inspecteur, avec des scripts jetables (`.local/tmp/`, non versionnés).

| Essai | Résultat (mesuré sur la TV) |
| --- | --- |
| Fond **Dark** ou **Light** au lieu de Photo | Écran complet en **0,72 à 0,78 s** |
| Disposition **List** avec la photo | **7,6 à 7,9 s** |
| Format de la photo : JPEG de base contre progressif | 3,6 à 3,9 s dans les deux cas ; le fond le plus lourd (1,1 Mo) : 4,6 s |
| Masquer voiles en dégradé, masques, lentilles de verre, logos SVG, ou le dessin de la photo | Aucun changement |
| Polyfill `gap` | Coûte ≈ 150 ms |
| Contourner `img.decode()`, ou précharger la photo, visible et en priorité haute | Gain ≈ 0,3 s |
| Lire les mêmes fichiers par XHR | 44 à 221 ms : le disque et le chargement ne sont pas en cause |
| Profil du moteur au démarrage | ≈ 8 s de travail cumulé des « tile workers » (rastérisation logicielle) sur 2 fils ; `Performance.getMetrics` : TaskDuration 3,47 s, dont script 0,18 s, mise en page 0,11 s, styles 0,2 s |

**Conclusion :** le délai est dans le pipeline d'images du moteur sous charge (rastérisation logicielle pendant le démarrage), pas dans le script, la mise en page ou le chargement des fichiers. La cause exacte n'est pas isolée : **non vérifié**. Replis : fond Dark/Light (0,75 s), ou un futur changement ma-tv qui afficherait la photo progressivement (**non implémenté**) — [plan-b](plan-b.md) § 7. Choix d'Alexis : garder la photo.

## 5. Installation et chaîne d'outils

| Étape | Résultat |
| --- | --- |
| `sdb capability` | `platform_version` 6.0, `cpu_arch` armv7. `appcmd_support` vaut disabled, pourtant `shell 0 applist`, `vd_appinstall`, `was_kill` et `debug` fonctionnent (mesuré sur la TV) |
| `:8001/api/v2/` | Répond ; JSON avec caractères de contrôle bruts (un parseur strict échoue ; `lib.py` utilise `strict=False`) (mesuré sur la TV) |
| Outils Samsung | Tizen Studio 6.1 web-cli + `cert-add-on` 2.0.75, `TV-SAMSUNG-Extension-Tools`/`-Resources`, `WebIDE` (nécessaire pour Certificate Manager) (mesuré sur le Mac) |
| Certificats | Profil `MaTV`, Samsung → TV, Public ; auteur « Samsung VD Author CA », distributeur « VD DEVELOPER Public CA Class » ; **expiration le 2027-10-20 pour les deux** (mesuré sur le Mac) |
| Signature (`sign.py`) | « Package (…) is created successfully » ; empreinte auteur enregistrée ; dates lues ; archive dans `.local/releases/` (mesuré sur le Mac) |
| `tv.py permit` | « Install Permitted » (mesuré sur la TV) |
| **Test A/B `required_version`** | Même paquet, seule cette valeur change. **6.5** : refusé par `tizen install` puis par le repli `vd_appinstall`, « install failed[118, -19], reason: Parsing error » ; la sortie du CLI contenait aussi une ligne trompeuse, la détection de `tv.py` a retenu l'échec. **6.0** : « install completed », app présente dans `applist` (mesuré sur la TV). Hypothèse confirmée : abaisser `required_version` était nécessaire, mais pas suffisant (corrections CSS et polices aussi) |
| `tv.py install` | `tizen install` : « Installation confirmée (tizen install, … présent dans applist) » (mesuré sur la TV) |
| `tv.py launch` | `tizen run` : « Tizen application is successfully launched » ; version enregistrée comme validée (mesuré sur la TV) |
| `tv.py debug` | Sans arrêt préalable, `shell 0 debug` reste bloqué quand l'app tourne déjà ; avec `was_kill` d'abord, il affiche « port: NNNNN » ; `sdb forward` OK. `Page.captureScreenshot` ne marche pas sur cet inspecteur (mesuré sur la TV) |
| Mode développeur | Code envoyé par `ma-tv/tools/remote.mjs` (KEY_1…KEY_5) après une autorisation acceptée sur la TV (elle expire en ≈ 30 s) ; « Host PC IP » saisi par Alexis ; redémarrage par appui long sur Marche (mesuré sur la TV). Node et Python ont eu besoin de l'autorisation « Réseau local » de macOS pour iTerm (`EHOSTUNREACH` sinon ; curl exempté) (mesuré sur le Mac) |
| `ma-tv/maj --dry-run` | Essayé (récupération et affichage, rien d'autre) |

## 6. Recette physique à la télécommande (Alexis)

| Essai | Résultat (mesuré sur la TV) |
| --- | --- |
| Flèches, OK, Retour dans l'accueil | OK |
| « All apps » | OK |
| Settings | OK |
| Retour à l'accueil → « Leave Home? » | OK |
| « Leave Home? » → « Samsung Home » | OK : ouvre Smart Hub |
| Lancer YouTube depuis CleanFrame | OK |
| Touche Home | Ouvre Samsung Home (attendu : touche système) |
| Revenir dans CleanFrame | OK, focus conservé |
| Netflix puis Retour / Exit | Ramène à Samsung Home, pas à CleanFrame |
| Veille 1 min puis rallumage | Samsung Home / la TV : CleanFrame n'est pas reprise |
| CleanFrame épinglée en tête du bandeau Apps | OK : Home puis OK = CleanFrame (2 appuis) |
| Autorun Last App | N'a pas fait démarrer la TV sur CleanFrame |
| Accueil affiché | YouTube, Netflix, Plex, ARTE, france.tv, Apple TV, Twitch, DAZN, RMC Sport (9, le maximum de l'auteur) ; M6+ dans « All apps » ; Art Mode masqué (`FrameTVSupport` = false) |
| Coupure du réseau | **non vérifié** (pas testé) |

## 7. Non vérifié

- Coupure du réseau pendant l'usage.
- Entrée « TV settings » de CleanFrame (ouverture des réglages Samsung).
- Lancement depuis CleanFrame des apps autres que YouTube et Netflix.
- Rendu des logos SVG sur la TV, relevé formellement (aucune anomalie signalée).
- Erreurs console sur « All apps » et les réglages, sous inspecteur (`iconPath` des icônes natives).
- Réception d'un `keyup` après OK et Retour.
- Mise à jour en place d'une version déjà installée (réglages conservés ?).
- Exécution complète de `ma-tv/maj` de bout en bout, et retour arrière automatique en réel.
- Désinstallation (`tv.py uninstall`) et désactivation du mode développeur.
- Effet de l'expiration des certificats sur l'app installée.
- Vidéo au ralenti hors inspecteur (critère des 2 s mesuré au chronomètre seulement).
- Cause exacte du délai d'affichage de la photo.
- Calibrage du bridage CPU de la recette.

## 8. Rejouer les tests

```sh
python3 ma-tv/build.py && node ma-tv/harness/run.mjs                   # recette navigateur → .local/qa/ma-tv/<horodatage>/summary.md
python3 ma-tv/tv.py debug                                              # TV : inspecteur + tunnel ; affiche le port
node ma-tv/harness/tv-inspect.mjs --port <port> --reloads 3            # → .local/qa/ma-tv/tv-<horodatage>.json
```

Puis, hors inspecteur (TV redémarrée), le chronomètre depuis le bandeau Apps et la recette physique du § 6.

## Langue et heure (2026-10-21)

| Vérification | Résultat |
|---|---|
| Français et 24 h par défaut | ✔ mesuré (recette Chromium 76 et référence) |
| Réglages → « Langue et heure » : passage à English / 12 h, coches, conservation après relance, retour au français | ✔ mesuré (recette) |
| Aucun texte anglais visible en français (15 écrans) | ✔ mesuré (détecteur de la recette, 0 avertissement) |
| Liste des Réglages à 7 groupes sans chevauchement | ✔ vérifié sur capture Chromium 76 |
| Rendu sur la TV | à confirmer à la télécommande (non vérifié) |
