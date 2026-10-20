# Compatibilité de CleanFrame avec Tizen 6.0

Ce document passe en revue chaque API Tizen, chaque réglage de `config.xml` et chaque fonction JavaScript ou CSS récente de `app/`. Pour chacun, il indique s'il fonctionne sur la TV (Tizen 6.0, Chromium **M76**, User-Agent `76.0.3809.146/6.0` mesuré) et ce que la branche `ma-tv` en a fait. Profil de la TV : [profil-tv](profil-tv.md). Résultats détaillés : [resultats-tests](resultats-tests.md).

Les numéros de ligne ont été relevés le 2026-10-20 sur la branche `ma-tv`. Les fichiers peuvent bouger : en cas de doute, chercher avec `grep -n` le symbole indiqué.

## Légende

| Colonne | Valeurs |
| --- | --- |
| **Tizen 6.0** | **oui** : présent dans M76 (source, recette et/ou TV). **non** : absent de M76. **incertain** : sources contradictoires, ou dépend de la TV réelle |
| **Action** | **garder** : tel quel. **adapter** : corrigé ou paramétré par ma-tv. **retirer** : masqué ou exclu |
| **Recette** | Chromium 76.0.3809.0 de bureau contre Chrome for Testing 155, sur le paquet construit : **189/189** vérifications, 0 erreur console ou réseau, géométrie à ±4 px sur 14 écrans (2026-10-20, `.local/qa/ma-tv/`). Ce n'est **pas** la TV |
| **TV** | Mesuré sur la TV le 2026-10-20 : inspecteur (`tv.py debug` + `harness/tv-inspect.mjs`) et essai à la télécommande |

Sources abrégées : [Samsung moteurs web][wes], [MDN BCD][bcd], [caniuse][ciu], [Application API 6.0][app60], [Remote Control][rc], [FAQ Samsung][faq].

## Fiabilité du tableau Samsung des moteurs web

Le tableau « Web Engine Specifications » de Samsung ([lien][wes]) donne bien la version du moteur : 2021 / Tizen 6.0 / M76, confirmée par le User-Agent mesuré. Ligne par ligne, en revanche, il est **peu fiable** :

- **Faux négatifs.** Il marque « No » en 6.0 `ResizeObserver` (Chrome 64), `linear-gradient` (Chrome 26), `prefers-reduced-motion` (Chrome 74), `font-variation-settings` (Chrome 62) et `FontFaceSet` (son « No » vise probablement l'interface globale `window.FontFaceSet`, alors que `document.fonts` existe dès Chrome 35 ; `document.fonts.check` répond sur la TV, mesuré).
- **Lignes incohérentes.** `inset` est « Yes » de Tizen 2.3 à 4.0 puis « No » jusqu'à 9.0. `:focus-visible` est « No » en 9.0 (M120). `gap` alterne « Yes » et « Yes(partially) » d'une année à l'autre.
- **Faux positif probable.** `font-optical-sizing` est « Yes », alors qu'il n'arrive qu'avec Chrome 79.
- **Une fois juste contre MDN.** Polices variables : Samsung dit « No ». La recette l'a constaté : Chromium 76 ignore les variations de graisse.

**Règle suivie par ma-tv :** version Chromium (M76), puis [MDN BCD][bcd] et [caniuse][ciu], puis **chargement réel dans Chromium 76** (recette), et en dernier lieu la TV elle-même. Le tableau Samsung sert d'indice, jamais de seule preuve.

## A. `app/config.xml` (manifeste)

Le fichier de l'auteur n'est pas modifié : `ma-tv/build.py` (`overlay_config`) écrit la version adaptée dans le paquet, puis la relit et vérifie chaque valeur (identité, `required_version`, `devel.api.version`).

| Élément | Fichier:ligne | Tizen 6.0 | Source | Action | Ce que ma-tv a fait |
| --- | --- | --- | --- | --- | --- |
| `widget id` | config.xml:2 | oui | [Configuring TV apps][cfg] | adapter | Identifiant propre à Alexis, généré une fois et lu dans `.local/ma-tv.json` (`identity.widget_id`) |
| `version="0.6.1"`, `viewmodes="maximized"` | config.xml:2 | oui | [Configuring TV apps][cfg] | garder | Version de l'auteur conservée |
| `tizen:application id` / `package` | config.xml:3 | oui (package de 10 caractères [0-9A-Za-z]) | [Tizen config editor 2.4](https://developer.tizen.org/dev-guide/2.4.0/org.tizen.devtools/html/web_tools/config_editor_w.htm) (ancienne doc) | adapter | Identité `<APP_ID>` générée une seule fois par `lib.identity()` au premier build. Ensuite, aucun outil n'en invente une autre : si elle manque alors qu'une version a été signée, tout s'arrête |
| `required_version="6.5"` | config.xml:3 | **non** : la TV **refuse** le paquet en 6.5 (« install failed[118, -19], reason: Parsing error », mesuré, test A/B) | Mesure ; [FAQ Q13][faq], [FAQ Baseline SDK](https://developer.samsung.com/tizen/Smart-TV/FAQ/Tizen-baseline-SDK.html) | adapter | `6.0` (clé `required_version`), accepté par la TV (mesuré). Rejouer le test : `python3 ma-tv/build.py --required-version 6.5` |
| `tizen:metadata devel.api.version` | (absent chez l'auteur) | oui. Samsung dit qu'elle « must » être déclarée | [FAQ Q13][faq] | adapter | Ajoutée avec `6.0` (clé `api_version`), puis contrôlée dans le `config.xml` généré |
| `<content src="index.html">` | config.xml:4 | oui | [Configuring TV apps][cfg] | garder | Barrière : toute autre valeur (page distante) arrête le build |
| `<name>` | config.xml:5 | oui | — | adapter | `identity.name` (« CleanFrame » par défaut), échappé |
| `<icon src="icon.png">` (PNG 256×256) | config.xml:6 | oui | [FAQ Q19][faq] (PNG recommandé) | garder | — |
| `feature screen.size.normal.1080.1920` | config.xml:7 | incertain : sert au filtrage du Store, effet hors Store non documenté. Sans gêne à l'installation (mesuré) | [Tizen features](https://samsungtizenos.com/docs/misc/feature) | garder | — |
| `tizen:profile name="tv-samsung"` | config.xml:8 | oui (`can_launch` = tv-samsung, mesuré) | [FAQ][faq] | garder | — |
| Privilège `application.launch` | config.xml:9 | oui, niveau public. Lancement d'apps tierces mesuré (YouTube, Netflix) | [Privilèges Tizen](https://github.com/Samsung/tizen-docs/blob/master/docs/application/web/reference/security-privileges.md) | garder | Liste blanche : tout privilège ajouté en amont arrête le build |
| Privilège `application.info` | config.xml:10 | oui, public (seul `ApplicationInformation.size` l'exige) | [Application API 6.0][app60] | garder | Liste blanche |
| Privilège `tv.inputdevice` | config.xml:11 | oui, public. **Inutilisé** : aucun `registerKey` | [TVInputDevice API][tvi] | garder (inoffensif) | Liste blanche |
| `tizen:setting screen-orientation="landscape"` | config.xml:12 | oui | [config.xml de référence][cfx] | garder | — |
| `context-menu="disable"` | config.xml:12 | oui | [config.xml de référence][cfx] | garder | — |
| `background-support="disable"` | config.xml:12 | oui : l'app est suspendue quand elle est cachée (horloge et rotation en pause) | [config.xml de référence][cfx] | garder | Barrière : un `enable` en amont arrête le build |
| `encryption="disable"`, `install-location="auto"` | config.xml:12 | oui | [config.xml de référence][cfx] | garder | — |
| `hwkey-event="enable"` | config.xml:12 | oui au schéma (événement `tizenhwkey`) ; effet sur TV **non vérifié** | [config.xml de référence][cfx], l. 1385-1416 | garder | — |
| Aucun `<access>`, `allow-navigation` ni CSP | (absents) | oui : sans eux, pas de CSP (modèle de sécurité v1). Sur la TV, l'app s'affiche et répond (mesuré), donc les `style="…"` injectés par `main.js` ne sont pas bloqués | [crosswalk-tizen web_application.cc](https://github.com/crosswalk-project/crosswalk-tizen/blob/master/runtime/browser/web_application.cc) | garder | Barrière : `<access>`, `allow-navigation`, CSP ou tout élément non prévu arrêtent le build |

## B. API Tizen (`app/device.js`)

Tous les appels sont dans des `try/catch`, avec une garde de 8 s (`bounded()`, device.js:36). Hors TV, l'app affiche un message au lieu de lever une exception.

| Élément | Fichier:ligne | Tizen 6.0 | Source | Action | Ce que ma-tv a fait |
| --- | --- | --- | --- | --- | --- |
| Détection `window.tizen.application` | device.js:29 (`api()`) | oui | [Application API][appsam] | garder | — |
| `tizen.application.launch(id, ok, ko)` | device.js:41 (`launchApp`), appelé par main.js:471 | oui (depuis 2.0, public). **Mesuré sur la TV** : YouTube et Netflix se lancent depuis CleanFrame. Autres apps **non vérifiées** une à une | [Application API 6.0][app60] (« Do not abuse the API… »). Contradiction : absent de l'IDL de [developer.samsung.com][appsam] | garder | IDs relevés sur la TV (`app/ma-tv-config.js` : `primaryApps`, `extraApps`). Recette : app absente → message propre ; sans réponse → message au bout de 8 s |
| Lancement de `com.samsung.tv.csfs` (« Samsung Home ») | device.js:67, main.js:925 et 968 | **oui** : « Leave Home? » → « Samsung Home » ouvre Smart Hub (mesuré à la télécommande) | Mesure ; [Forum Samsung](https://forum.developer.samsung.com/t/unable-to-launch-samsung-tv-plus-on-tizen-smart-tv-via-app-control-api/40673) (non officiel) | adapter | Paramétrable : `system.home`. La valeur `'hide'` met CleanFrame en arrière-plan |
| Lancement de `com.samsung.tv.coba.setting` (réglages TV) | device.js:68, main.js:926 | incertain : ID présent (mesuré), ouverture depuis « TV settings » **non vérifiée** | idem | adapter | Paramétrable : `system.settings` (ou `'hide'`) |
| `getCurrentApplication().hide()` | device.js:62 (`system`) | oui (depuis 2.0, sans privilège) ; sur la TV **non vérifié** (repli non utilisé) | [Application API 6.0][app60] | adapter (repli) | Utilisé seulement si `system.*` vaut `'hide'` |
| `getCurrentApplication().appInfo.id` | device.js:28 | oui | [Application API 6.0][app60] | adapter | `SELF` prend l'ID réel installé : l'app ne se liste jamais elle-même |
| `new tizen.ApplicationControlData`, `new tizen.ApplicationControl`, `launchAppControl(…, 'org.tizen.art-app')` | device.js:51-59 (`art`), main.js:509 | incertain : les constructeurs existent. ArtApp est présente (mesuré) mais `FrameTVSupport`=false | [Application API][appsam] ; ID connu seulement par un [forum Tizen](https://developer.tizen.org/node/31106) (non officiel) | retirer (masqué) | `hideUtils: ['art']` (main.js:502). Code de l'auteur conservé. Recette : « contrôles d'accueil = config » |
| `tizen.application.getAppsInfo` et filtres (regex d'ID, `show`, listes) | device.js:69-89 | oui (depuis 2.0, sans privilège). « All apps » s'ouvre et liste les apps (mesuré à la télécommande) | [Application API 6.0][app60] | adapter | Listes extensibles depuis `.local/ma-tv.json` (section `local`) : `ids`, `streaming`, `consumer`, `internal`, `selfId` |
| `ApplicationInformation.id` / `name` / `show` | device.js:77-83 | oui | [Application API][appsam] | garder | — |
| `ApplicationInformation.iconPath` chargé en `<img>` | device.js:83, main.js:148-152 (`appMark`), 321 (`safeIcon`) | incertain : 0 erreur console sur l'accueil (mesuré) ; écran « All apps » **non observé** sous inspecteur | [Application API][appsam] | garder | Rien. En cas d'échec, le monogramme de l'auteur prend le relais (`onerror`). Le mock de la recette fournit un `iconPath` vide |
| `webapis.*`, `tizen.systeminfo`, `tizen.tvinputdevice`, `exit()` | — | sans objet | grep : non utilisés | — | La recette vérifie qu'aucune API Tizen non imitée n'est appelée (0 accès, 2 moteurs) |

## C. Télécommande

| Élément | Fichier:ligne | Tizen 6.0 | Source | Action | Ce que ma-tv a fait |
| --- | --- | --- | --- | --- | --- |
| Flèches 37-40, OK 13, Retour 10009, sans `registerKey` | main.js:13 (`KEYS`), 1837 (keydown) | **oui** : flèches, OK et Retour marchent à la télécommande (mesuré) | [Remote Control][rc], [TVInputDevice 6.0](https://samsungtizenos.com/docs/application/web/api/6.0.0/tv/device_api/tv/tizen/tvinputdevice) | garder | Recette : keyCode reçus identiques (injection CDP) |
| 27 (Échap), 8, 461 | main.js:13 | sans objet (navigateur, webOS) | — | garder | — |
| `keyup` après OK et Retour (`heldKeys`) | main.js:1842-1849 | incertain : aucune source ne garantit le `keyup` ; non relevé sur la TV | — | adapter | Un appui « tenu » expire 700 ms après la dernière répétition. Recette : « OK maintenu = un seul lancement » |
| Couleurs 403-406, médias, chiffres, Exit 10182 | — | il faut `registerKey` ; Exit est géré par le système | [Remote Control][rc] | garder (ignorées) | Recette « touches non gérées » : sans effet, 0 erreur |
| Touche Home | — | touche système, qu'une app web ne peut pas intercepter. Mesuré : Home ouvre Samsung Home ; revenir dans CleanFrame retrouve le focus | [TVInputDevice API][tvi] | — | Voir [plan-b](plan-b.md) § 9 |

## D. JavaScript (syntaxe et API web)

| Élément | Fichier:ligne | Tizen 6.0 | Source | Action | Ce que ma-tv a fait |
| --- | --- | --- | --- | --- | --- |
| Syntaxe ES5 stricte (IIFE, `var`, `function`) | main.js:3, device.js:3, compat-tizen6.js:6 | oui (0 exception sur la TV, mesuré) | Scan du code (0 `=>`, `let`/`const`, gabarit, `?.`, `??`) | garder | Barrière `JS_BLOCKERS` : `?.`, `??`, `\|\|=`, `.at()`, `replaceAll`, `Object.hasOwn`, `structuredClone`, membres privés… L'analyseur (`strip_js`) vide chaînes, commentaires et littéraux regex avant la recherche ; il arrête le build s'il se désynchronise ou rencontre un gabarit `${…}` |
| `Promise`, `Promise.all` | main.js:226 | oui (Chrome 32) | [BCD Promise](https://github.com/mdn/browser-compat-data/blob/main/javascript/builtins/Promise.json) | garder | — |
| `document.fonts.load` / `.ready` / `.check`, `FontFace.status` | main.js:210-245 | oui (`document.fonts.check` répond sur la TV, mesuré). Samsung : « FontFaceSet No » (interface globale) | [BCD FontFaceSet](https://github.com/mdn/browser-compat-data/blob/main/api/FontFaceSet.json) | garder | Repli de l'auteur sans API et délai de 3 s. `ready.then` sans `catch` (main.js:239) : risque mineur de rejet non géré |
| `FontFace.variationSettings` | main.js:168, 175, 181 | non. Deux lectures de MDN se contredisent (Chrome 140 ou jamais) | [BCD FontFace](https://github.com/mdn/browser-compat-data/blob/main/api/FontFace.json) | garder | Sans effet (simple propriété), ne touche que Newsreader |
| `TextMetrics.actualBoundingBox*` (77), `fontBoundingBox*` (87) | main.js:177-178 | non | [BCD TextMetrics](https://github.com/mdn/browser-compat-data/blob/main/api/TextMetrics.json) | garder | Replis `\|\| size * …` de l'auteur. Recette : géométrie à ±4 px de la référence |
| `canvas.measureText().width` | main.js:177, 270 | oui | [BCD][bcd] | garder | — |
| CSSOM `cssRules`, `deleteRule`, `insertRule` | main.js:194-206 (`retryFontFaces`) | oui | [BCD][bcd] | garder | — |
| `matchMedia('(prefers-reduced-motion: reduce)')` | main.js:79 | incertain : Chrome 74 selon MDN, « No » selon Samsung | [BCD @media](https://github.com/mdn/browser-compat-data/blob/main/css/at-rules/media.json) | garder | Protégé (`window.matchMedia &&`) ; au pire vaut false |
| `localStorage` (clé `cleanframe.home.v1`) | main.js:326, 377, 385 | oui. Conservé lors d'une mise à jour en place selon Samsung, effacé à la désinstallation. Mise à jour en place sur cette TV **non vérifiée** | [FAQ données](https://developer.samsung.com/smarttv/develop/faq/data-and-file-handling.html) | garder | Clé de l'auteur inchangée. Recette : « réglages conservés après relance ». `serialise()` enregistre aussi les apps de marque (ma-tv) |
| `HTMLImageElement.decode()` | main.js:1635 | oui (64). Sur la TV, contourner `decode()` ferait gagner ≈ 0,3 s au démarrage avec photo (mesuré, essai jetable) | [BCD HTMLImageElement](https://github.com/mdn/browser-compat-data/blob/main/api/HTMLImageElement.json) | garder | Protégé (`if (im.decode)`). Optimisation **non implémentée** ([plan-b](plan-b.md) § 7) |
| `focus({ preventScroll: true })` | main.js:1776 | oui (64) | [BCD][bcd] | garder | Repli `focus()` |
| `requestAnimationFrame` | main.js:1209, 1248 | oui | [Samsung][wes] | garder | — |
| `visibilitychange`, `focus`, `blur` | main.js:1850-1853 | oui. Mesuré : retour dans CleanFrame après une autre app ou la touche Home, focus conservé. Après 1 min de veille, la TV rallume sur Samsung Home : CleanFrame n'est pas reprise | [Samsung][wes] (Page Visibility : Yes) | garder | Recette « masquage-reprise » |
| `style.setProperty('--…')` (propriétés personnalisées) | main.js:1011, 1221 | oui (49) | [BCD][bcd] | garder | — |
| `getBoundingClientRect`, `getClientRects`, `getComputedStyle` | main.js (nombreux) | oui | [BCD][bcd] | garder | `compat-tizen6.js:86` enveloppe `getBoundingClientRect` pour appliquer le polyfill `gap` avant chaque mesure (seulement si le flex gap manque, donc sur la TV) |
| `innerHTML` + `esc()` | main.js:107, 308 | oui | — | garder | — |
| `new Image()` (sondes SVG) | main.js:126-134 (`probeMark`) | incertain : la [FAQ Q19][faq] dit « SVG not supported » ; aucune anomalie signalée sur la TV, sans relevé dédié | — | garder | Rien. En cas d'échec, `.mark.is-bad` masque l'icône **sans** monogramme : voir [plan-b](plan-b.md) § 4 |
| `'webkitMaskImage' in style` | main.js:125 | oui (préfixé) | [BCD mask-image][mask] | garder | — |
| Horloge `getHours() % 12` | main.js:1067 | oui | ES5 | garder | Format 12 h de l'auteur conservé (passage à 24 h non fait) |
| `MutationObserver`, `Element.matches` | compat-tizen6.js:81, 73 | oui (Chrome 26 et 34). Polyfill actif sur la TV (mesuré) | [BCD][bcd] | adapter (ajout) | Utilisés par le polyfill `gap` |
| Crochets de test `window.ShoreQA` | main.js:1879-1880 | oui | — | garder | Utilisés par la recette et par `tv-inspect.mjs` (instants « accueil utilisable » et « écran complet ») |

## E. CSS (`app/style.css`)

Les conversions portent sur la copie du paquet (`dist/ma-tv/stage/`) : les fichiers de l'auteur ne changent pas. Les commentaires CSS sont retirés avant conversion (jamais réécrits). Comptes relevés dans `dist/ma-tv/build.json`.

| Élément | Fichier:ligne | Tizen 6.0 | Source | Action | Ce que ma-tv a fait |
| --- | --- | --- | --- | --- | --- |
| `inset` (6 occurrences) | style.css:114, 115, 203, 292, 423, 484 | **non** (Chrome 87). Sans correction : boîtes de 0×0 et libellés du Dock et de « All apps » invisibles | [caniuse inset](https://caniuse.com/mdn-css_properties_inset), [BCD inset](https://github.com/mdn/browser-compat-data/blob/main/css/properties/inset.json) | adapter | `adapt_css` : remplacé par `top/right/bottom/left` (×6). Une valeur avec fonction (`calc`, `var`) n'est pas découpée : la barrière « inset non converti » arrête le build. `inset-inline/block` aussi |
| `gap` dans des conteneurs flex (37 déclarations, dont 3 à 0) | style.css:38 → 574 | **non** (Chrome 84). `@supports (gap: …)` répond vrai à tort en M76 (gap de grille) | [caniuse flexbox-gap](https://caniuse.com/flexbox-gap), [BCD gap](https://github.com/mdn/browser-compat-data/blob/main/css/properties/gap.json) | adapter | Polyfill `app/compat-tizen6.js` : marges calculées sur 35 sélecteurs (`ma-tv-gap.js`), actif seulement si `flexGapWorks()` est faux. **Actif sur la TV ; coût ≈ 150 ms au démarrage** (mesuré). Règles CSS générées pour les `::before/::after` (`html.cf-no-flexgap`). Recette : positions à ±4 px de Chrome 155 |
| `:focus-visible` (2 occurrences) | style.css:524 | **non** (Chrome 86) : sélecteur inconnu, toute la règle tombe | [caniuse focus-visible](https://caniuse.com/css-focus-visible) | adapter | Converti en `:focus` (×2). Pas de souris sur la TV |
| `font-synthesis: none` | style.css:577, main.js:157 | non (Chrome 97) | [caniuse font-synthesis](https://caniuse.com/mdn-css_properties_font-synthesis) | garder (accepté) | Avertissement au build. Les graisses fixes évitent le faux gras |
| `font-optical-sizing: none` | style.css:589-592 | non (Chrome 79). Samsung dit « Yes » : contradiction | [caniuse font-optical-sizing](https://caniuse.com/mdn-css_properties_font-optical-sizing) | garder (accepté) | Avertissement au build |
| `font-variation-settings "opsz"` (Newsreader) | style.css:589-594 | incertain : MDN (Chrome 62) contre Samsung (« No ») ; la recette montre que M76 ignore les variations | [BCD font-variation-settings](https://github.com/mdn/browser-compat-data/blob/main/css/properties/font-variation-settings.json) | garder | Newsreader, police facultative, n'est **pas** convertie : risque résiduel |
| `@media (prefers-reduced-motion)` (5 blocs) | style.css:371, 539, 540, 552, 599 | incertain (Chrome 74 contre Samsung « No ») | [BCD @media](https://github.com/mdn/browser-compat-data/blob/main/css/at-rules/media.json) | garder | Sans risque |
| `-webkit-mask-image`, `-size`, `-repeat` et `mask-*` | style.css:96-98, 112, 204 ; main.js:146 | oui grâce au préfixe (sans préfixe : Chrome 120). Masquer les masques ne change pas le temps de démarrage sur la TV (mesuré) | [BCD mask-image][mask] | garder | Barrière : dans une même règle, un `mask` sans son équivalent `-webkit-` arrête le build (idem `background-clip: text`) |
| Propriétés personnalisées, `var()`, `calc()` dans les dégradés | style.css:2-12, 96-98 | oui (49) | [Samsung][wes], [BCD][bcd] | garder | — |
| `linear-gradient`, `radial-gradient` | style.css (nombreux) | oui (Chrome 26), malgré certaines lignes « No » de Samsung. Masquer les voiles en dégradé ne change pas le démarrage (mesuré) | [BCD][bcd] | garder | Ne pas les retirer à tort |
| `object-fit`, `object-position` | style.css:27, 80, 115, 193, 237, 500, 530 | oui (32) | [BCD][bcd] | garder | — |
| `will-change: transform` | style.css:99, 100, 170, 261 | oui (36). Sur la TV, la rastérisation est logicielle au démarrage (≈ 8 s de travail cumulé des « tile workers », mesuré) ; effet propre de `will-change` **non isolé** | [BCD][bcd] | garder | — |
| `transition`, `@keyframes`, `cubic-bezier`, `transform` | style.css:136, 228-229, 598 et environ 47 transitions | oui. Fluidité sur la TV **non mesurée** (aucune gêne signalée lors de l'essai à la télécommande) | [Samsung][wes] | garder | — |
| `font-variant-numeric: tabular-nums` | style.css:40, 252, 322 | oui (52) | [BCD][bcd] | garder | — |
| Fonctions récentes **absentes** aujourd'hui : `aspect-ratio`, `:is/:where/:has`, `:not()` en liste, `clamp/min/max`, propriétés logiques, `translate/rotate/scale`, requêtes de conteneur, `@layer`, `@media` par intervalle, imbrication, couleurs CSS 4/5, unités `dvh`… | — | non | [BCD][bcd], [caniuse][ciu] | — | Barrière `CSS_BLOCKERS`, ancrée sur une position de déclaration (pas de faux positif sur un nom de classe) : leur apparition en amont arrête la mise à jour |

## F. Polices et médias

| Élément | Fichier:ligne | Tizen 6.0 | Source | Action | Ce que ma-tv a fait |
| --- | --- | --- | --- | --- | --- |
| Manrope variable, `font-weight: 400 700` (police par défaut) | assets/fonts.css:1 | **non en pratique** : Chromium 76 l'affiche à sa graisse par défaut, 200 (mesuré dans la recette). Samsung : « No » ; caniuse : « oui depuis 62/66 » | [caniuse variable-fonts](https://caniuse.com/variable-fonts) | adapter | Graisses fixes 400, 500 et 600 (`ma-tv/assets/fonts/`, produites avec fontTools par `ma-tv/tools/static-fonts.py`, licence OFL conservée). Le fichier variable est retiré du paquet. **Chargées sur la TV** (mesuré) |
| Geist variable (`300 400`) | assets/typefaces.css:2 | non en pratique (même cause) | idem | adapter | Graisses fixes 300 et 400 |
| Newsreader variable (400 + axe `opsz`) | assets/typefaces.css:3 | incertain | idem | garder | Non convertie (police facultative). Rendu en M76 **non vérifié** |
| Empreintes des polices de l'auteur | ma-tv/assets/fonts/SOURCES.json | — | — | — | Le build avertit si l'auteur change ses fichiers (graisses fixes périmées) |
| `size-adjust`, `ascent/descent/line-gap-override` | assets/typefaces.css:2-3 | non (Chrome 92 et 87) | [caniuse size-adjust](https://caniuse.com/mdn-css_at-rules_font-face_size-adjust), [caniuse ascent-override](https://caniuse.com/mdn-css_at-rules_font-face_ascent-override) | garder (accepté) | Métriques de Geist et Newsreader un peu différentes |
| `font-display: swap` (Manrope), `block` (Geist, Newsreader) | assets/fonts.css:1, typefaces.css:2-3 | oui (60) | [Samsung][wes] | garder | Avec `block`, le texte reste invisible jusqu'à 3 s si Geist ou Newsreader est choisie |
| WOFF2, TTF | assets/ | oui (WOFF2 : Chrome 36) | [Samsung][wes] | garder | — |
| JPEG (15 fonds 1920 px, 60 matières) | assets/wallpapers, assets/materials ; main.js:1632-1660 | oui. **C'est le goulot du démarrage sur la TV** : écran complet avec photo en 3,7-3,9 s contre 0,72-0,78 s en fond Dark/Light (mesuré). Format JPEG de base ou progressif : 3,6-3,9 s ; le fond de 1,1 Mo : 4,6 s. Lecture des mêmes fichiers par XHR : 44-221 ms, donc le délai est dans le pipeline d'images du moteur sous charge (mesuré ; cause exacte **non vérifiée**) | [FAQ Q19][faq] (JPG et PNG recommandés) | garder | Paquet de 15,8 Mo (`build.json`). Replis : [plan-b](plan-b.md) § 7 |
| Icônes SVG (masques et `<img>`) et pictogrammes SVG en ligne | assets/icons/*.svg, main.js:60-75, 126-147 | incertain : FAQ Q19 « SVG not supported » contre Chromium 76, qui les affiche (recette). Masquer les logos SVG ne change pas le démarrage (mesuré) | [FAQ Q19][faq] | garder | Rien. Plan B en PNG : [plan-b](plan-b.md) § 4 |
| `icon.png` | app/icon.png | oui | [FAQ Q19][faq] | garder | — |

## G. HTML

| Élément | Fichier:ligne | Tizen 6.0 | Source | Action | Ce que ma-tv a fait |
| --- | --- | --- | --- | --- | --- |
| `main`, `nav`, `section role=dialog`, `hidden`, `aria-*` | index.html:13-88 | oui (`main` : Chrome 26) | [BCD main](https://github.com/mdn/browser-compat-data/blob/main/html/elements/main.json) | garder | — |
| `meta viewport` et `fit()` (scène 1920×1080 mise à l'échelle) | index.html:5, main.js:1787 | oui. La TV expose 1920 × 1080, DPR 1 (mesuré) : échelle 1 | [Managing Screen Resolution](https://developer.samsung.com/smarttv/develop/guides/fundamentals/managing-screen-resolution.html) | garder | — |
| `lang="en-AU"`, textes en anglais | index.html:2 | oui | — | garder | Traduction hors périmètre |
| Ordre des scripts | index.html:89 (ancre `device.js`) | — | — | adapter | `ma-tv-config.js`, `ma-tv-gap.js` et `compat-tizen6.js` sont injectés avant `device.js`. Si l'ancre disparaît, le build s'arrête |
| Script ou style en ligne dans le HTML | — | — | — | — | Barrière : interdits (les autres barrières ne les inspecteraient pas) |

## H. Commandes de la chaîne d'outils (Mac ↔ TV)

| Commande | Utilisée par | Tizen 6.0 | Source | Remarque |
| --- | --- | --- | --- | --- |
| `GET :8001/api/v2/` | `lib.tv_api`, `tv.py info`, garde-fou `guard_tv` | oui (mesuré) | [Debugging][dbg] | Lecture seule. JSON avec caractères de contrôle bruts : lu avec `strict=False` |
| `sdb connect <IP_TV>:26101`, `capability` | `tv.py connect/capability` | oui (mesuré) | [SDB](https://docs.tizen.org/application/tizen-studio/common-tools/smart-development-bridge) | Port interne, impossible de l'« ouvrir » ([TV Device][tvd]) |
| `sdb shell 0 applist` | `tv.py applist`, contrôles d'installation | oui (mesuré, 393 lignes) | non documenté ; utilisé par [Samsung Wits][wits] | `sdb shell` interactif désactivé (`intershell_support`) |
| `tizen security-profiles list` | `sign.py`, `tv.py permit` | sans objet (Mac) ; profil `<PROFIL>` actif (mesuré) | aide du CLI installé | `permit` refuse de continuer si le profil actif n'est pas `<PROFIL>` |
| `tizen package -t wgt -s <PROFIL> -o …` | `sign.py` | **oui** : « Package (…) is created successfully » (mesuré) | [CLI Samsung][cli] (option `-o` non documentée sur cette page) | Mots de passe tenus par le profil (Certificate Manager) ; repli Trousseau si le CLI les demande |
| `tizen install-permit -s <IP_TV>:26101` | `tv.py permit` | **oui** : « Install Permitted » (mesuré) | [Web Inspector](https://developer.samsung.com/SmartTV/develop/getting-started/using-sdk/web-inspector.html), [jellyfin-tizen](https://github.com/jellyfin/jellyfin-tizen) (non officiel) | Lié au certificat distributeur : à refaire après son renouvellement (**non vérifié**) |
| `tizen install -s … -n … -- <dir>` | `tv.py install` (1er choix) | **oui** en 6.0 : « install completed » (mesuré) | [CLI Samsung][cli] | Sortie peu fiable : en cas de refus, une ligne trompeuse peut rester. ma-tv exige le message de succès **et** l'absence de marque d'échec (`install failed`, `Failed to`…) **et** la présence dans `applist` |
| `sdb push` + `sdb shell 0 vd_appinstall` | `tv.py install` (repli) | **oui**, la commande s'exécute (mesuré lors du refus en 6.5, même diagnostic que `tizen install`) | non documenté ; [Samsung Wits][wits] | Nom distant fixe, écrasé à chaque fois |
| `tizen run -p` | `tv.py launch` | **oui** : « successfully launched » (mesuré) | [CLI Samsung][cli] | Repli `sdb shell 0 was_execute` : **non utilisé** jusqu'ici |
| `tizen uninstall -p` / `sdb shell 0 vd_appuninstall` | `tv.py uninstall` | **non vérifié** | [CLI Samsung][cli], [Wits][wits] | Doc : `-p` = ID d'app ; aide du CLI : « package id ». Contrôle final par `applist` |
| `sdb shell 0 was_kill <APP_ID>` puis `sdb shell 0 debug <APP_ID>` + `sdb forward tcp:N tcp:N` | `tv.py debug` | **oui** (mesuré). Sans `was_kill`, `debug` reste bloqué si l'app tourne déjà ; ensuite il affiche « port: NNNNN » | [Wits][wits] ; [Forum](https://forum.developer.samsung.com/t/force-debug-port/10309) (non officiel) | Le port change à chaque lancement. `Page.captureScreenshot` ne marche pas avec l'inspecteur de cette TV (mesuré) |
| Télécommande réseau `wss://<IP_TV>:8002` | `tools/remote.mjs` | oui (mesuré) | [Home Assistant](https://www.home-assistant.io/integrations/samsungtv/) (non officiel) | Appairage une fois (invite à accepter dans les 30 s environ) |

[wes]: https://developer.samsung.com/smarttv/develop/specifications/web-engine-specifications.html
[bcd]: https://github.com/mdn/browser-compat-data
[ciu]: https://caniuse.com/
[app60]: https://samsungtizenos.com/docs/application/web/api/6.0.0/tv/device_api/tv/tizen/application
[appsam]: https://developer.samsung.com/smarttv/develop/api-references/tizen-web-device-api-references/application-api.html
[rc]: https://developer.samsung.com/smarttv/develop/guides/user-interaction/remote-control.html
[tvi]: https://developer.samsung.com/smarttv/develop/api-references/tizen-web-device-api-references/tvinputdevice-api.html
[faq]: https://developer.samsung.com/smarttv/develop/faq/specifications-and-feature-support.html
[cfg]: https://developer.samsung.com/smarttv/develop/guides/fundamentals/configuring-tv-applications.html
[cfx]: https://github.com/Samsung/tizen-docs/blob/master/docs/application/web/reference/config-xml.md
[mask]: https://github.com/mdn/browser-compat-data/blob/main/css/properties/mask-image.json
[cli]: https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/command-line-interface.html
[dbg]: https://developer.samsung.com/smarttv/develop/extension-libraries/smart-view-sdk/receiver-apps/debugging.html
[tvd]: https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-device.html
[wits]: https://github.com/Samsung/Wits/blob/master/lib/appLaunchHelper.js
