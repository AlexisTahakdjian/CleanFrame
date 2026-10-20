# Plans B : si une fonction ne marche pas sur Tizen 6.0

Pour chaque point fragile, ce document donne le symptôme, le repli, et **comment basculer** : clé de configuration, option de build ou réglage à la télécommande. Quand un repli n'existe pas encore dans le code, c'est écrit « **non implémenté** ». Ce qui n'a pas été testé sur la TV est marqué « **non vérifié** ». Les mesures citées viennent de [resultats-tests](resultats-tests.md) (2026-10-20).

## Où se règlent les replis

| Type | Où | Prise en compte |
| --- | --- | --- |
| **Comportement de l'app** | `.local/ma-tv.json`, section `"local"`. Fusionnée au build par-dessus `app/ma-tv-config.js` (`window.CleanFrameLocal`). **Chaque clé remplace la valeur entière** : pour `primaryApps`, recopier la liste complète | Reconstruire et réinstaller : `ma-tv/maj --rebuild` |
| **Outillage** | `.local/ma-tv.json`, clés de premier niveau : `required_version`, `api_version`, `install.method`, `sdk`, `sign.profile`, `sign.keychain_service`, `tv.*`, `mac_ip`, `chromium76`, `chrome_reference`, `harness.calibrated_throttle`, `upstream.*`, `fork.*` | Commande suivante |
| **Variables d'environnement** | `CLEANFRAME_TV_HOST`, `CLEANFRAME_TV_PORT`, `CLEANFRAME_MAC_IP`, `CLEANFRAME_TIZEN_SDK`, `CLEANFRAME_SIGN_PROFILE`, `CLEANFRAME_CHROMIUM76`, `CLEANFRAME_CHROME_REFERENCE` | Priorité sur le fichier |
| **Options en ligne de commande** | `build.py --required-version X`, `--check-only` · `update.py` (`ma-tv/maj`) `--dry-run --rebuild --confirm --skip-tv --skip-tests --no-push` · `harness/run.mjs --engine m76\|modern\|both --throttle N --runs N --only motif --no-shots` · `harness/tv-inspect.mjs --port N --reloads N --keys` · `tv.py <action> [--yes] [--wgt fichier]` | Immédiate |
| **Réglages dans l'app** | Settings → Appearance (fond, disposition, apps, contrôles, police…) à la télécommande | Enregistrés dans l'app (`localStorage`), aucune reconstruction |

Exemple de section `"local"` (valeurs fictives, sans identifiant privé) :

```json
{
  "local": {
    "system": { "home": "hide", "settings": "hide" },
    "hideUtils": ["art"]
  }
}
```

## Tableau récapitulatif

| # | Fonction à risque | État (2026-10-20) | Repli principal | Bascule |
| --- | --- | --- | --- | --- |
| 1 | Installation refusée | OK en `required_version` 6.0 ; **refusée en 6.5** (mesuré) | `required_version` 6.0 / certificat | `required_version`, Certificate Manager |
| 2 | `tizen install` contre `vd_appinstall` | `tizen install` OK ; `vd_appinstall` s'exécute (mesuré) | Forcer une méthode | `install.method` |
| 3 | Ouvrir Samsung Home / Réglages TV | Samsung Home OK (mesuré) ; TV settings **non vérifié** | Mettre l'app en arrière-plan | `local.system` = `'hide'` |
| 4 | Masques SVG (icônes de marque) | OK en Chromium 76 ; aucune anomalie signalée sur la TV, **non vérifié** formellement | Monogrammes / texte | Réglage Apps → Text ; `local.primaryApps[].mark=false` |
| 5 | Icônes natives (`iconPath`) | 0 erreur sur l'accueil (mesuré) ; « All apps » **non vérifié** | Monogramme (déjà automatique) | Masquage des erreurs : **non implémenté** |
| 6 | Polices | Graisses fixes chargées sur la TV (mesuré) | Manrope par défaut | Réglage Font ; `tools/static-fonts.py` |
| 7 | Démarrage | Accueil utilisable 0,52-0,65 s ; **photo complète 3,7-3,9 s** (mesuré) | Fond Dark/Light (0,72-0,78 s, mesuré) | Réglage Background ; affichage progressif **non implémenté** |
| 8 | Inspecteur sur la TV | Marche, après `was_kill` (mesuré) ; pas de capture d'écran | Chronomètre, vidéo | `tv.py debug` |
| 9 | Touche Home | **impossible** pour une app web | Épingler l'app en tête du bandeau Apps (marche, mesuré) | Menus de la TV |
| 10 | macOS 28 (fin de Rosetta) | échéance automne 2027 (attendu) | Rester sous macOS 27, machine x86_64 | `sdk`, `chromium76` |
| 11 | Recette impossible à lancer | — | Moteur de référence seul, ou rien | `--engine`, `--skip-tests` |
| 12 | Signature bloquée | Signature OK (mesuré) ; renouvellement le 2027-10-20 | Tizen Studio (interface) | `sign.profile` |
| 13 | Polyfill `gap` trop lent | ≈ 150 ms au démarrage (mesuré) ; touches réactives | — | Interrupteur **non implémenté** |
| 14 | Saisie du code 12345 | Résolu (mesuré) | Télécommande réseau | `tools/remote.mjs` |

## 1. Installation refusée

| Symptôme | Cause probable | Repli | Bascule |
| --- | --- | --- | --- |
| « install failed[118, -19], reason: Parsing error » | `required_version` > 6.0 : **mesuré** avec 6.5, refusé par `tizen install` comme par `vd_appinstall` | Déclarer 6.0 (c'est la valeur par défaut, acceptée : « install completed », mesuré) | `.local/ma-tv.json` : `"required_version": "6.0"`, `"api_version": "6.0"`. Ne **pas** descendre sous 6.0 sans test (les règles de privilèges changent pour les anciennes versions d'API : **non vérifié**) |
| `[118, -12]`, « Check certificate error », « Invalid certificate chain » | Distributeur sans le bon DUID, profil Tizen au lieu de Samsung | Recréer le distributeur dans Certificate Manager (Samsung → TV, DUID pré-coché sur la TV connectée, **pas** l'identifiant `device.id` de `/api/v2/`), puis autoriser l'installation | `python3 ma-tv/tv.py permit`, puis `python3 ma-tv/tv.py install` |
| « Certificate in signature was expired » | Certificat expiré (le 2027-10-20 pour les deux) | Renouveler : [procédure](procedure.md#renouveler-les-certificats) | `sign.py` s'arrête avant la TV et donne la date |
| `tv.py permit` : « Le profil de certificats actif n'est pas … » | Un autre profil est actif dans le CLI | Rendre `<PROFIL>` actif | `~/tizen-studio/tools/ide/bin/tizen security-profiles set-active -n <PROFIL>` |
| Privilège refusé | Profil de niveau Partner sans partenariat (**non vérifié**) | Les 3 privilèges sont **publics** : profil Public (celui créé, mesuré) | Certificate Manager |
| Rien ne s'installe, même par Tizen Studio | Mode développeur ou IP du Mac | `guard_tv` le signale : corriger « Host PC IP » (Apps → 12345) | `mac_ip` dans `.local/ma-tv.json` |

L'installation par USB n'est plus prise en charge par Samsung ([TV Device](https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-device.html)) : il n'existe pas de repli hors mode développeur.

## 2. `tizen install` contre `vd_appinstall`

`tv.py install` essaie d'abord la commande officielle `tizen install`, puis la commande Samsung non documentée `sdb push` + `sdb shell 0 vd_appinstall` (utilisée par [Samsung Wits](https://github.com/Samsung/Wits/blob/master/lib/appLaunchHelper.js)). Le succès exige toujours le message attendu, **aucune** marque d'échec dans la sortie (le CLI peut afficher une ligne de succès trompeuse après un refus) **et** la présence de `<APP_ID>` dans `applist`.

| Valeur de `install.method` | Comportement |
| --- | --- |
| `"auto"` (défaut) | `tizen install`, puis `vd_appinstall` si non confirmé |
| `"tizen"` | `tizen install` seulement ; arrêt s'il n'est pas confirmé |
| `"vd"` (toute autre valeur) | `vd_appinstall` seulement |

Mesuré le 2026-10-20 : `tizen install` a installé le paquet 6.0 ; lors du refus en 6.5, le repli `vd_appinstall` s'est bien exécuté et a rendu le même diagnostic. `"auto"` peut donc rester.

Si aucune ne marche : installer depuis Tizen Studio (interface, Device Manager → Permit to install, puis Run As → Tizen Web Application), **non vérifié** sur ce Mac. Le lancement a le même double repli : `tizen run -p` (marche, mesuré), puis `sdb shell 0 was_execute` (non utilisé).

## 3. Ouvrir « Samsung Home » et « TV settings »

Les ID `com.samsung.tv.csfs` et `com.samsung.tv.coba.setting` existent sur la TV (mesuré). « Leave Home? » → « Samsung Home » ouvre bien Smart Hub (mesuré). « TV settings » n'a pas été essayé (**non vérifié**).

| Symptôme | Repli | Bascule |
| --- | --- | --- |
| « The TV could not open this screen », ou rien au bout de 8 s, après Retour → « Samsung Home » ou Settings → « TV settings » | Mettre CleanFrame en arrière-plan (`tizen.application.getCurrentApplication().hide()`), ce qui rend la main à l'interface Samsung | `"local": { "system": { "settings": "hide" } }` (ou `"home"`), puis `ma-tv/maj --rebuild`. Une seule des deux clés suffit (l'autre garde sa valeur par défaut) |
| `hide()` sans effet visible | La touche **Home** de la télécommande marche toujours (gérée par le système, mesuré) | `exit()` n'est pas utilisé : **non implémenté** |

## 4. Masques SVG (icônes de marque)

La [FAQ Samsung Q19](https://developer.samsung.com/smarttv/develop/faq/specifications-and-feature-support.html) dit « SVG images are not supported ». Chromium 76 les affiche (recette). Sur la TV, l'accueil a été jugé correct à la télécommande, sans relevé dédié des logos (**non vérifié** formellement). Si la sonde `probeMark` (main.js) échoue, `.mark.is-bad` masque l'icône **sans** monogramme de repli : la tuile reste vide en mode Icons.

| Repli | Bascule | Effet |
| --- | --- | --- |
| 1. Afficher les noms | Télécommande : Settings → Appearance → **Apps : Text** (et **Home controls : Text** si les pictogrammes de contrôle sont faux) | Immédiat, sans reconstruction |
| 2. Monogrammes au lieu des logos | `"local": { "primaryApps": [ { "id": "netflix", "name": "Netflix", "mark": false, "appId": "org.tizen.netflix-app" }, … ] }` avec **la liste complète**, puis `ma-tv/maj --rebuild` | `appMark()` dessine un monogramme (plus l'icône native si elle se charge) |
| 3. Logos en PNG | Rasteriser `app/assets/icons/*.svg` en PNG au build et les utiliser comme masques : **non implémenté** (à ajouter dans `ma-tv/build.py`) | Logos conservés |

Les pictogrammes SVG en ligne (`SVG` dans main.js) n'ont pas de repli PNG : **non implémenté**. Masquer les logos SVG ne change pas le temps de démarrage (mesuré) : aucun gain à attendre de ce côté.

## 5. Icônes natives des apps (`iconPath`)

`getAppsInfo` fournit un chemin de fichier local sur la TV, affiché en `<img>`. En cas d'échec, `onerror` masque l'image et le monogramme reste visible : l'interface est déjà protégée. Le risque restant est une erreur console (« Not allowed to load local resource »), contraire au critère « 0 erreur ».

- **Constaté :** 0 erreur console sur l'accueil, 3 rechargements sous inspecteur (mesuré). L'écran « All apps » s'ouvre à la télécommande (mesuré) mais n'a pas été observé sous inspecteur (**non vérifié**).
- **Constater :** `tv-inspect.mjs` ne parcourt que l'accueil. Ajouter un passage par « All apps » (`ShoreQA.scene('apps')`, comme dans `harness/run.mjs`) avant le relevé des erreurs : **non implémenté**.
- **Repli :** ne plus émettre l'`<img>` natif. Aucun interrupteur aujourd'hui : **non implémenté**. Il faudrait un crochet `ma-tv` dans `appMark()` ou `safeIcon()` (main.js), lu dans `CleanFrameLocal` (par exemple `nativeIcons: false`).

## 6. Polices

| Symptôme | Repli | Bascule |
| --- | --- | --- |
| Texte trop fin ou faux gras (polices variables ignorées) | Déjà traité : graisses fixes Manrope 400/500/600 et Geist 300/400 dans le paquet. Manrope chargée sur la TV (mesuré) | — |
| Le build avertit « … a changé en amont : relancer static-fonts.py » | Régénérer les graisses fixes | `.local/venv/bin/python ma-tv/tools/static-fonts.py` (venv : `python3 -m venv .local/venv && .local/venv/bin/pip install fonttools brotli`), puis commit de `ma-tv/assets/fonts/` |
| Newsreader mal rendue (restée variable) | Ne pas la choisir | Settings → Appearance → **Font : Manrope**. La retirer de la liste : **non implémenté** (il faudrait réécrire `assets/font-catalog.js` au build) |
| Geist ou Newsreader : texte invisible jusqu'à 3 s (`font-display: block`) | Manrope (`swap`) | Réglage Font |
| Une police ne se charge pas | Le code de l'auteur se rabat sur des métriques de secours au bout de 3 s | Automatique |

## 7. Démarrage

**Mesuré sur la TV** (inspecteur, 3 rechargements) : accueil **utilisable** (horloge, apps, focus ; touches actives) en 0,52-0,65 s ; écran **complet** avec la photo en 3,7-3,9 s. Chronomètre d'Alexis depuis Apps → CleanFrame : accueil visible en 1-2 s, lancement compris. **Choix d'Alexis : garder le fond photo.**

Ce que l'enquête a montré (mesuré sur la TV, essais jetables, détail dans [resultats-tests](resultats-tests.md) § 4) : la photo arrive tard parce que le pipeline d'images du moteur est saturé au démarrage (rastérisation logicielle), pas à cause du réseau, du disque ou du script. Le format de la photo compte peu ; masquer voiles, masques, lentilles de verre ou logos ne change rien. Cause exacte **non vérifiée**.

| Repli | Bascule | Effet |
| --- | --- | --- |
| **Fond uni** | Settings → Appearance → **Background : Dark** ou **Light** | Écran complet en **0,72-0,78 s** (mesuré) |
| Éviter List + Photo | Layout : **Dock** | List avec photo : 7,6-7,9 s (mesuré) contre 3,7-3,9 s en Dock |
| Pas de changement de fond | Rotation : **Fixed** | Pas de nouveau lot d'images à chaque ouverture |
| Police par défaut | Font : **Manrope** | Évite le blocage de 3 s des autres polices |
| Afficher la photo progressivement (accueil d'abord, photo ensuite, sans attendre `decode()`) | Changement ma-tv au démarrage : **non implémenté** | Contourner `img.decode()` ou précharger la photo en priorité haute fait gagner ≈ 0,3 s (mesuré) ; un affichage progressif changerait surtout la perception |
| Images plus légères | Réduire les fonds au build : **non implémenté** | Faible attendu : baseline contre progressif = 3,6-3,9 s ; seul le fond de 1,1 Mo est plus lent (4,6 s) |
| Laisser l'app résidente | Revenir à CleanFrame par le bandeau Apps plutôt que la fermer | Mesuré : après une autre app ou la touche Home, retour avec focus conservé. Après la veille, la TV rallume sur Samsung Home : démarrage à froid |

Le bridage de la recette (`harness.calibrated_throttle`) n'est pas calibré : la recette rapporte ses temps sans juger le critère des 2 s. Le bridage CPU ne reproduit probablement pas le goulot de la TV (hypothèse).

## 8. Inspecteur sur la TV

`python3 ma-tv/tv.py debug` arrête d'abord l'app (`sdb shell 0 was_kill <APP_ID>` : sans cela, `debug` reste bloqué si l'app tourne, mesuré), lance `sdb shell 0 debug <APP_ID>`, lit « port: NNNNN » au fil de l'eau, puis ouvre le tunnel `sdb forward tcp:N tcp:N`. Ensuite `node ma-tv/harness/tv-inspect.mjs --port <port>` relève erreurs, temps et dimensions. **Marche sur cette TV** (mesuré).

| Symptôme | Repli |
| --- | --- |
| « Port d'inspection non fourni par la TV » | Relancer `tv.py debug` (il refait `was_kill`). Sinon : Tizen Studio → Debug As → Tizen Web Application ([Web Inspector](https://developer.samsung.com/SmartTV/develop/getting-started/using-sdk/web-inspector.html)), **non vérifié** |
| Pas de capture d'écran (`Page.captureScreenshot` ne marche pas sur cet inspecteur, mesuré) | Photo de l'écran au téléphone. La géométrie fine reste vérifiée dans la recette (Chromium 76 contre référence) |
| Inspecteur muet avec un Chrome récent (problème connu, [FAQ Samsung](https://developer.samsung.com/smarttv/develop/faq/application-testing.html)) | `tv-inspect.mjs` parle directement au protocole DevTools, sans navigateur : non concerné |
| Mesures faussées par le débogage | Samsung : fermer une app déboguée ne l'arrête pas. Redémarrer la TV, puis faire la mesure finale **hors** mode debug (chronomètre ou vidéo) |

## 9. Touche Home de la télécommande

**Impossible pour une app web.** La touche Home est gérée par le système avant toute app : `registerKey` ne la propose pas ([TVInputDevice](https://developer.samsung.com/smarttv/develop/api-references/tizen-web-device-api-references/tvinputdevice-api.html)). `config.xml` ne permet pas le lancement au démarrage sur une TV grand public ([forum Samsung](https://forum.developer.samsung.com/t/launch-application-automatically-on-boot-of-the-device/26398), non officiel). Les touches raccourcis (Netflix, Prime…) ne se reprogramment pas, et Universal Guide ne se remplace pas. La réassignation native de l'auteur a été **retirée** : élévation de privilèges, verrouillage sur sa TV, .NET 6 absent de Tizen 6.0, base de restauration privée.

Mesuré sur la TV : Home ouvre Samsung Home ; Retour/Exit dans Netflix ramène à Samsung Home ; après 1 min de veille, la TV rallume sur Samsung Home (CleanFrame n'est pas reprise).

| Repli | Comment | Résultat sur cette TV | Limite |
| --- | --- | --- | --- |
| **Épingler CleanFrame en tête** | Accueil → tuile CleanFrame → maintenir OK → Déplacer tout à gauche | **Marche** (mesuré) : Home puis OK = CleanFrame, 2 appuis | À refaire si l'app est désinstallée |
| Autorun Last App | Paramètres → Général → Fonctions intelligentes → Autorun Last App : On ([Samsung](https://www.samsung.com/ae/support/tv-audio-video/use-autorun-start-screen-options-on-your-samsung-tv/)) | **Ne marche pas** : la TV n'a pas démarré sur CleanFrame (mesuré) | — |
| Autorun Smart Hub : Off | Même menu | **non vérifié** | Ne fait pas de CleanFrame l'accueil |
| Habitude | Revenir sur CleanFrame avant d'éteindre | Sans effet après la veille (mesuré) | — |
| Boîtier externe + Anynet+ (HDMI-CEC) | Accueil sur un boîtier HDMI qui allume la TV et bascule sur son entrée ([Samsung](https://www.samsung.com/sg/support/tv-audio-video/use-anynetplus-hdmi-cec-on-your-samsung-smart-tv/)) | **non vérifié** | Change d'architecture : ce n'est plus CleanFrame sur la TV |

Retour arrière de ces réglages : [retour-arriere](retour-arriere.md), étape 5.

## 10. macOS 28 et la fin de Rosetta

Apple garantit Rosetta comme outil général jusqu'à macOS 27, puis n'en garde qu'un sous-ensemble pour les jeux ([Apple](https://developer.apple.com/documentation/apple-silicon/about-the-rosetta-translation-environment)). Tizen Studio 6.1 (`sdb`, CLI `tizen`, JDK) et le Chromium 76 de la recette sont en x86_64. Sous macOS 28, `ma-tv/maj` cessera donc probablement de fonctionner. **L'app installée sur la TV continuera de tourner** : seules les mises à jour s'arrêtent. L'échéance tombe à peu près en même temps que celle des certificats (2027-10-20) : renouveler les certificats **avant** de changer de macOS.

| Repli | Bascule | Statut |
| --- | --- | --- |
| 1. Ne pas passer à macOS 28 sur ce Mac tant qu'aucun repli n'est prêt | — | Le plus sûr |
| 2. Machine x86_64 (vieux Mac Intel, PC Linux ou Windows) avec Tizen Studio, certificats restaurés depuis la sauvegarde | `sdk` (ou `CLEANFRAME_TIZEN_SDK`) vers la nouvelle installation ; copier `.local/ma-tv.json`, `~/SamsungCertificate/`, `profiles.xml` ([procédure](procedure.md#restaurer-le-certificat-auteur)) | **non vérifié** |
| 3. VM Linux arm64 avec traduction Intel intégrée à la virtualisation (macOS 27 : [Apple](https://developer.apple.com/documentation/virtualization/running-intel-binaries-in-linux-vms)) | Idem | **non vérifié**, rien de garanti après macOS 27 |
| 4. Recette : Chromium 76 Linux arm64 natif (paquet Debian buster `chromium 76.0.3809.100` sur [snapshot.debian.org](https://snapshot.debian.org/mr/package/chromium/)) dans un conteneur, donc sans Rosetta | `chromium76` / `CLEANFRAME_CHROMIUM76` vers un script lanceur : **non implémenté** | **non vérifié** |
| 5. Sinon : `--skip-tests` (déconseillé) et installation manuelle | `ma-tv/maj --skip-tests` | Perte de la principale barrière |

## 11. Recette impossible à lancer

| Symptôme | Repli | Bascule |
| --- | --- | --- |
| « navigateur présent » en échec | Indiquer le bon chemin | `chromium76` / `chrome_reference` ou les variables `CLEANFRAME_*` |
| Chromium 76 ne démarre plus (Rosetta, macOS) | Référence seule (perd la vérification M76) | `node ma-tv/harness/run.mjs --engine modern` |
| Le Chrome installé sur le Mac plante en headless (Chrome 118 sous macOS 27, mesuré) | Utiliser le `chrome-headless-shell` officiel (Chrome for Testing) | `chrome_reference` ([procédure](procedure.md#navigateurs-de-la-recette)) |
| Pas de recette du tout | Sauter la recette, puis regarder l'écran | `ma-tv/maj --skip-tests --confirm` (**déconseillé**) |

## 12. Signature bloquée

| Symptôme | Repli | Bascule |
| --- | --- | --- |
| « Profil de signature … introuvable » | Créer le profil (Certificate Manager → Samsung → TV) ou corriger son nom | `sign.profile` / `CLEANFRAME_SIGN_PROFILE` |
| « Le CLI demande le mot de passe du certificat, absent du Trousseau » | Les mots de passe ne sont plus dans le profil : les y remettre (Certificate Manager) ou les placer une fois dans le Trousseau | `security add-generic-password -s cleanframe-signing -a <PROFIL> -w` |
| Délai de 180 s dépassé (invites du CLI différentes) | Signer depuis Tizen Studio (interface), puis installer le paquet produit | `python3 ma-tv/tv.py install --wgt <fichier signé>` |
| « Certificat … expire dans N jours » / « expiré » | Renouveler | [procédure](procedure.md#renouveler-les-certificats) |
| « Le certificat auteur a changé » | Hors renouvellement : restaurer le certificat d'origine depuis la sauvegarde. **Ne pas** effacer `sign.author_sha256` pour forcer le passage, sauf dans le cas prévu par la procédure de renouvellement (même clé publique vérifiée) | [procédure](procedure.md#restaurer-le-certificat-auteur) |

## 13. Polyfill `gap` trop lent

`app/compat-tizen6.js` ne s'active que si le moteur ignore le flex `gap`, donc sur la TV (actif, mesuré). Il observe le DOM, recalcule les marges et enveloppe `getBoundingClientRect`. **Coût mesuré : ≈ 150 ms au démarrage.** Les touches restent réactives (mesuré à la télécommande).

- **Constater :** `tv-inspect.mjs` indique l'état du polyfill (`CleanFrameCompat.flexGap`).
- **Repli :** aucun interrupteur aujourd'hui (**non implémenté**). Piste : remplacer le polyfill par des marges CSS générées au build (comme pour les pseudo-éléments, `html.cf-no-flexgap`). Gain plafonné à ≈ 150 ms : pas prioritaire.

## 14. Saisie du code 12345 (mode développeur)

Résolu le 2026-10-20 (mesuré) : avec la Smart Remote, la saisie manuelle n'a rien donné. Le panneau Apps étant affiché, envoyer le code depuis le Mac :

```sh
node ma-tv/tools/remote.mjs pair                          # une fois : accepter l'invite sur la TV (elle expire en ≈ 30 s)
node ma-tv/tools/remote.mjs KEY_1 KEY_2 KEY_3 KEY_4 KEY_5
```

Si macOS bloque Node (`EHOSTUNREACH`), autoriser « Réseau local » pour le terminal (Réglages Système → Confidentialité et sécurité → Réseau local). Pour un champ texte de la TV ouvert (clavier à l'écran), `remote.mjs --text "…"` peut saisir chiffres et points ; Alexis a préféré taper « Host PC IP » lui-même. Autre repli, non testé : le pavé numérique virtuel de la Smart Remote (touche « 123 », [Remote Control](https://developer.samsung.com/smarttv/develop/guides/user-interaction/remote-control.html)).
