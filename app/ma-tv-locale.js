/* ma-tv : langue de l'interface et format de l'heure, réglables dans Settings → « Langue et heure ».
   - Traduction à l'affichage : les textes anglais de l'auteur sont remplacés dans la page (le texte d'origine est
     gardé, ce qui permet de revenir à l'anglais). Le code de l'auteur reste en anglais : ses mises à jour
     fusionnent sans conflit ; un texte nouveau non traduit reste simplement en anglais (signalé par le build).
   - Réglages enregistrés à part (localStorage 'cleanframe.ma-tv.v1'), valeurs par défaut dans ma-tv-config.js.
   ES5 uniquement (Chromium 76 / Tizen 6.0). */
(function () {
  'use strict';
  var KEY = 'cleanframe.ma-tv.v1', LOCAL = window.CleanFrameLocal || {}, DEFAULTS = LOCAL.locale || {};
  var prefs = { lang: DEFAULTS.lang || 'fr', clock: DEFAULTS.clock || '24h' };
  try { var saved = JSON.parse(localStorage.getItem(KEY) || 'null'); if (saved) { if (saved.lang === 'fr' || saved.lang === 'en') prefs.lang = saved.lang; if (saved.clock === '24h' || saved.clock === '12h') prefs.clock = saved.clock; } } catch (e) {}

  var NB = ' '; // espace insécable avant ? : (typographie française)
  var FR = {
    // Accueil et contrôles
    'All apps': 'Toutes les applis', 'Settings': 'Réglages', 'Art Mode': 'Mode Art', 'Arrange': 'Organiser',
    'Home controls': 'Commandes de l’accueil', 'Leave Home?': 'Quitter l’accueil' + NB + '?', 'Open Samsung Home?': 'Ouvrir l’accueil Samsung' + NB + '?',
    'Stay': 'Rester', 'Samsung Home': 'Accueil Samsung', 'Back': 'Retour', 'Home is full': 'Accueil complet', 'Add app': 'Ajouter une appli',
    'No apps on Home': 'Aucune appli sur l’accueil', 'Add apps': 'Ajouter des applis',
    'Home holds nine apps. Remove one first.': 'L’accueil contient 9 applis au plus. Retirez-en une d’abord.',
    'Home needs one app': 'L’accueil doit garder une appli', 'Not saved. OK tries again.': 'Non enregistré. OK pour réessayer.',
    // Réglages
    'Background': 'Fond', 'Layout': 'Disposition', 'Typography': 'Police', 'Focus': 'Sélection', 'Apps on Home': 'Applis de l’accueil',
    'Samsung': 'Samsung', 'Home and TV settings': 'Accueil et réglages TV', 'Rotation': 'Rotation', 'Background type': 'Type de fond',
    'Wallpaper': 'Fond d’écran', 'App display': 'Affichage des applis', 'Focus style': 'Style de sélection', 'Material': 'Matière',
    'Apps': 'Applis', 'Font': 'Police', 'Appearance': 'Apparence',
    'Choose Photo to use wallpaper and rotation.': 'Choisir Photo pour utiliser les fonds d’écran et la rotation.',
    'Materials are available with a Photo background.': 'Les matières sont disponibles avec un fond Photo.',
    'Choose Glass focus or the Dock layout to use materials.': 'Choisir la sélection Verre ou la disposition Dock pour utiliser les matières.',
    'Choose Photo in Background to use rotation.': 'Choisir Photo dans Fond pour utiliser la rotation.',
    'Timed changes pause while Settings or another panel is open.': 'Les changements programmés s’interrompent tant que Réglages ou un autre panneau est ouvert.',
    'Open Samsung’s Home screen': 'Ouvrir l’écran d’accueil Samsung', 'TV settings': 'Réglages TV',
    'Picture, sound and network settings': 'Image, son et réseau', 'Open selected group': 'Ouvrir le groupe choisi',
    'Try again': 'Réessayer', 'Retry this change': 'Réessayer ce changement', 'Apply selected setting': 'Appliquer le réglage choisi',
    'Choose a wallpaper': 'Choisir un fond d’écran', 'Choose a rotation interval': 'Choisir l’intervalle de rotation',
    'Open on the TV': 'Ouvrir sur la TV', 'Retry this photo': 'Réessayer cette photo', 'Apply selected photo': 'Appliquer la photo choisie',
    'Applied': 'Appliqué', 'Preview': 'Aperçu', 'Back cancels this change.': 'Retour annule ce changement.',
    'Couldn’t save this change.': 'Impossible d’enregistrer ce changement.', 'Couldn’t load this appearance.': 'Impossible de charger cette apparence.',
    'Couldn’t save. Nothing changed.': 'Échec de l’enregistrement. Rien n’a changé.', 'your choice': 'votre choix',
    // Valeurs
    'Dark': 'Sombre', 'Light': 'Clair', 'Photo': 'Photo', 'List': 'Liste', 'Dock': 'Dock', 'Type': 'Typographie', 'Glass': 'Verre',
    'Soft': 'Doux', 'Frost': 'Givré', 'Clear tint': 'Teinte claire', 'Icons': 'Icônes', 'Icons and text': 'Icônes et texte', 'Text': 'Texte',
    'Both': 'Les deux', 'Fixed': 'Fixe', 'Each time Home opens': 'À chaque ouverture de l’accueil', 'Every 5 minutes': 'Toutes les 5 minutes',
    'Every 15 minutes': 'Toutes les 15 minutes', 'Every hour': 'Toutes les heures',
    // Éditeur et catalogue
    'Undo': 'Annuler', 'Done': 'Terminé', 'Nothing to undo': 'Rien à annuler', 'Remove from Home': 'Retirer de l’accueil',
    'Recently removed': 'Retirées récemment', 'Other installed apps': 'Autres applis installées', 'Add to Home': 'Ajouter à l’accueil',
    'Not on Home': 'Hors de l’accueil', 'Then scroll': 'Puis faire défiler', 'On Home': 'Sur l’accueil',
    'Loading installed apps…': 'Chargement des applis installées…', 'No installed apps found.': 'Aucune appli installée trouvée.',
    'Could not read installed apps.': 'Impossible de lire la liste des applis installées.', 'Last app': 'Dernière appli',
    // Messages de device.js
    'The TV could not open this screen.': 'La TV n’a pas pu ouvrir cet écran.',
    'Try again, or press the remote’s Home button to return to CleanFrame.': 'Réessayez. Pour revenir à CleanFrame : Home, puis CleanFrame en tête des applis.',
    'The TV did not respond. Please try again.': 'La TV n’a pas répondu. Réessayez.',
    'Open CleanFrame on the TV to use this control.': 'Ouvrez CleanFrame sur la TV pour utiliser cette commande.',
    'The web preview cannot control the TV.': 'L’aperçu web ne peut pas piloter la TV.', 'This app has no launch target.': 'Cette appli n’a pas de cible de lancement.',
    // Fonds d'écran (catalogue de l'auteur)
    'Misty coast': 'Côte brumeuse', 'Quiet cove': 'Crique paisible', 'Forest mist': 'Brume en forêt', 'Mountain valley': 'Vallée de montagne',
    'Desert stars': 'Étoiles du désert', 'Blue peaks': 'Sommets bleus', 'Bridge at dusk': 'Pont au crépuscule', 'Sunlit ridges': 'Crêtes ensoleillées',
    'Golden hour': 'Heure dorée', 'Sunlit summits': 'Sommets ensoleillés', 'Gold Coast dusk': 'Crépuscule sur la Gold Coast',
    'Sydney Harbour': 'Port de Sydney', 'Amber hills': 'Collines ambrées', 'Mint wave': 'Vague menthe', 'Alpine glow': 'Lueur alpine',
    // Réglages ma-tv
    'Language and time': 'Langue et heure', 'Language': 'Langue', 'Clock': 'Horloge', '24-hour': '24 h', '12-hour': '12 h',
    // Libellés d'accessibilité
    'TV stage, 1920 by 1080. Click it, then use the arrow keys, Enter for OK and Escape for Back.': 'Écran TV 1920 × 1080. Flèches pour se déplacer, Entrée pour OK, Échap pour Retour.'
  };
  // Phrases assemblées par le code de l'auteur (nom d'appli, numéro…) : modèle → traduction.
  var lower = function (s) { return s.charAt(0).toLowerCase() + s.slice(1); };
  var PATTERNS = [
    [/^Remove (.+) from Home$/, function (m) { return 'Retirer ' + m[1] + ' de l’accueil'; }],
    [/^Add (.+) to Home$/, function (m) { return 'Ajouter ' + m[1] + ' à l’accueil'; }],
    [/^Remove (.+)$/, function (m) { return 'Retirer ' + m[1]; }],
    [/^Restore (.+)$/, function (m) { return 'Remettre ' + m[1]; }],
    [/^Add (.+)$/, function (m) { return 'Ajouter ' + m[1]; }],
    [/^Move (.+)$/, function (m) { return 'Déplacer ' + m[1]; }],
    [/^Undo (.+)$/, function (m) { return 'Annuler' + NB + ': ' + lower(t(m[1].charAt(0).toUpperCase() + m[1].slice(1))); }],
    [/^Undone: (.+)\.$/, function (m) { return 'Annulé' + NB + ': ' + lower(t(m[1])) + '.'; }],
    [/^(.+) is in Recently removed\. OK puts it back\.$/, function (m) { return m[1] + ' est dans Retirées récemment. OK la remet.'; }],
    [/^(.+) is on Home, position (\d+)\.$/, function (m) { return m[1] + ' est sur l’accueil, position ' + m[2] + '.'; }],
    [/^(.+) moved to position (\d+)\.$/, function (m) { return m[1] + ' passe en position ' + m[2] + '.'; }],
    [/^(.+) stays installed\.$/, function (m) { return m[1] + ' reste installée.'; }],
    [/^Moving (.+)\. OK places it, Back puts it back\.$/, function (m) { return 'Déplacement de ' + m[1] + '. OK pour poser, Retour pour annuler.'; }],
    [/^(\d+) apps?$/, function (m) { return m[1] + (m[1] === '1' ? ' appli' : ' applis'); }],
    [/^(\d+) of (\d+)$/, function (m) { return m[1] + ' sur ' + m[2]; }],
    [/^Return to (.+)$/, function (m) { return 'Revenir ' + ({ Settings: 'aux Réglages', Background: 'au Fond' }[m[1]] || 'à ' + t(m[1])); }],
    [/^Loading (.+)…$/, function (m) { return 'Chargement de ' + t(m[1]) + '…'; }],
    [/^Preparing (.+)…$/, function (m) { return 'Préparation de ' + t(m[1]) + '…'; }],
    [/^Applying (.+)…$/, function (m) { return 'Application de ' + t(m[1]) + '…'; }],
    [/^Couldn’t load (.+?)\.( Your current choice is kept\.)?$/, function (m) { return 'Impossible de charger ' + t(m[1]) + '.' + (m[2] ? ' Votre choix actuel est conservé.' : ''); }],
    [/^Couldn’t save (.+?)\.( Your current choice is kept\.)?$/, function (m) { return 'Impossible d’enregistrer ' + t(m[1]) + '.' + (m[2] ? ' Votre choix actuel est conservé.' : ''); }],
    [/^(.+) Your current choice is kept\.$/, function (m) { return t(m[1]) + ' Votre choix actuel est conservé.'; }],
    [/^Wallpaper (.+)$/, function (m) { return 'Fond d’écran ' + t(m[1]); }]
  ];

  // Traduction d'un texte (sans les espaces de bord). Texte inconnu : inchangé.
  function t(text) {
    if (prefs.lang !== 'fr' || typeof text !== 'string') return text;
    var core = text.replace(/^\s+|\s+$/g, ''), out, i, m;
    if (!core || !/[A-Za-z]/.test(core)) return text;
    out = FR.hasOwnProperty(core) ? FR[core] : null;
    for (i = 0; out === null && i < PATTERNS.length; i++) { m = PATTERNS[i][0].exec(core); if (m) out = PATTERNS[i][1](m); }
    // Valeurs composées par le code (« Glass, Soft ») : chaque partie traduite si toutes sont connues.
    if (out === null && core.indexOf(', ') > 0) {
      var parts = core.split(', '), done = parts.map(function (p) { return t(p); });
      if (done.every(function (d, j) { return d !== parts[j]; })) out = done.join(', ');
    }
    return out === null ? text : text.replace(core, out);
  }

  // ---------- Traduction de la page (texte d'origine gardé dans _cfEn) ----------
  function textNode(n) {
    if (n._cfOut !== undefined && n.nodeValue !== n._cfOut) n._cfEn = undefined; // l'auteur a changé le texte
    var source = n._cfEn !== undefined ? n._cfEn : n.nodeValue, translated = t(source);
    if (translated !== n.nodeValue) { n._cfEn = source; n._cfOut = translated; n.nodeValue = translated; }
  }
  function attribute(el, name) {
    var store = '_cf_' + name, value = el.getAttribute(name);
    if (value === null) return;
    if (el[store + 'Out'] !== undefined && value !== el[store + 'Out']) el[store] = undefined;
    var source = el[store] !== undefined ? el[store] : value, translated = t(source);
    if (translated !== value) { el[store] = source; el[store + 'Out'] = translated; el.setAttribute(name, translated); }
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { textNode(root); return; }
    if (root.nodeType !== 1) return;
    if (root.tagName === 'SCRIPT' || root.tagName === 'STYLE') return;
    attribute(root, 'aria-label');
    var tw = document.createTreeWalker(root, 5 /* éléments + texte */, null, false), n;
    while ((n = tw.nextNode())) { if (n.nodeType === 3) textNode(n); else attribute(n, 'aria-label'); }
  }
  var observer;
  function start() {
    document.documentElement.lang = prefs.lang === 'fr' ? 'fr-FR' : 'en';
    walk(document.body);
    observer = new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var r = records[i], j;
        if (r.type === 'characterData') textNode(r.target);
        else if (r.type === 'attributes') attribute(r.target, r.attributeName);
        else for (j = 0; j < r.addedNodes.length; j++) walk(r.addedNodes[j]);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['aria-label'] });
  }
  function retranslate() { document.documentElement.lang = prefs.lang === 'fr' ? 'fr-FR' : 'en'; walk(document.body); if (observer) observer.takeRecords(); }

  // ---------- Réglages « Langue et heure » (intégrés à l'écran Settings de l'auteur) ----------
  function save() { try { localStorage.setItem(KEY, JSON.stringify(prefs)); return true; } catch (e) { return false; } }
  function choice(action, label, applied) { return { action: action, axis: 'ma-tv', value: action, label: label, applied: applied }; }
  window.CleanFrameMaTv = {
    t: t,
    prefs: function () { return { lang: prefs.lang, clock: prefs.clock }; },
    clock24: function () { return prefs.clock === '24h'; },
    settingsRows: function () {
      return [{ id: 'locale', label: 'Language and time', value: (prefs.lang === 'fr' ? 'Français' : 'English') + ', ' + t(prefs.clock === '24h' ? '24-hour' : '12-hour') }];
    },
    sections: function () {
      return [
        { id: 'lang', title: 'Language', horizontal: true, items: [choice('ma-tv.lang.fr', 'Français', prefs.lang === 'fr'), choice('ma-tv.lang.en', 'English', prefs.lang === 'en')] },
        { id: 'clock', title: 'Clock', horizontal: true, items: [choice('ma-tv.clock.24h', '24-hour', prefs.clock === '24h'), choice('ma-tv.clock.12h', '12-hour', prefs.clock === '12h')] }
      ];
    },
    ok: function (action) {
      var part = action.split('.');
      if (part[1] === 'lang' && (part[2] === 'fr' || part[2] === 'en')) prefs.lang = part[2];
      if (part[1] === 'clock' && (part[2] === '24h' || part[2] === '12h')) prefs.clock = part[2];
      save();
      // Le rendu de l'auteur suit (press → render) ; la page déjà affichée est retraduite tout de suite.
      setTimeout(retranslate, 0);
    }
  };
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
}());
