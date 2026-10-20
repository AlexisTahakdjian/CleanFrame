/* ma-tv : compatibilité Tizen 6.0 (moteur Chromium 76, TV 2021).
   Chromium 76 lit `gap` mais ne l'applique pas aux conteneurs flex (support : Chrome 84). Ce script
   reproduit l'espacement par des marges, uniquement si le moteur en a besoin : aucun effet ailleurs.
   ma-tv/build.py injecte la liste des sélecteurs qui déclarent un gap (window.CleanFrameGapSelectors). */
(function () {
  'use strict';
  var selectors = (window.CleanFrameGapSelectors || []).filter(function (s) {
    try { document.querySelector(s); return true; } catch (e) { return false; }
  });
  if (!selectors.length || !window.MutationObserver || flexGapWorks()) return;
  var query = selectors.join(','), touched = [], observer;

  function flexGapWorks() {
    var box = document.createElement('div');
    box.style.cssText = 'display:flex;flex-direction:column;row-gap:1px;position:absolute;visibility:hidden';
    box.appendChild(document.createElement('div')); box.appendChild(document.createElement('div'));
    document.documentElement.appendChild(box);
    var works = box.scrollHeight === 1;
    box.parentNode.removeChild(box);
    return works;
  }
  function px(value) { var n = parseFloat(value); return isNaN(n) ? 0 : n; }
  // Éléments qui participent au flux flex (ni absolus, ni masqués) et nœuds texte visibles.
  function items(el) {
    var out = [], node, style;
    for (node = el.firstChild; node; node = node.nextSibling) {
      if (node.nodeType === 3) { if (/\S/.test(node.nodeValue)) out.push(node); continue; }
      if (node.nodeType !== 1) continue;
      style = window.getComputedStyle(node);
      if (style.display === 'none' || style.position === 'absolute' || style.position === 'fixed') continue;
      out.push(node);
    }
    return out;
  }
  function apply() {
    var i, el, plan = [], style, dir, gap, list, j, a, b, side;
    // 1. Effacer nos marges précédentes pour relire les marges d'origine de l'auteur.
    for (i = 0; i < touched.length; i++) touched[i].el.style[touched[i].prop] = touched[i].was;
    touched = [];
    // 2. Lire : conteneurs flex visibles avec un gap non nul.
    var els = document.querySelectorAll(query);
    for (i = 0; i < els.length; i++) {
      el = els[i]; style = window.getComputedStyle(el);
      if (style.display.indexOf('flex') < 0) continue;
      dir = style.flexDirection;
      gap = px(dir.indexOf('column') === 0 ? style.rowGap : style.columnGap);
      if (!gap) continue;
      list = items(el);
      for (j = 0; j + 1 < list.length; j++) {
        a = list[j]; b = list[j + 1];
        // La marge va après l'élément a ; sinon (a est du texte) avant l'élément b.
        side = { row: ['marginRight', 'marginLeft'], 'row-reverse': ['marginLeft', 'marginRight'],
          column: ['marginBottom', 'marginTop'], 'column-reverse': ['marginTop', 'marginBottom'] }[dir] || ['marginRight', 'marginLeft'];
        if (a.nodeType === 1) plan.push({ el: a, prop: side[0], add: gap, base: px(window.getComputedStyle(a)[side[0]]) });
        else if (b.nodeType === 1) plan.push({ el: b, prop: side[1], add: gap, base: px(window.getComputedStyle(b)[side[1]]) });
      }
    }
    // 3. Écrire en une fois (une seule mise en page).
    for (i = 0; i < plan.length; i++) {
      touched.push({ el: plan[i].el, prop: plan[i].prop, was: plan[i].el.style[plan[i].prop] });
      plan[i].el.style[plan[i].prop] = (plan[i].base + plan[i].add) + 'px';
    }
    // Nos propres écritures ne doivent pas relancer un passage.
    if (observer) observer.takeRecords();
  }
  function relevant(records) {
    var i, r, t;
    for (i = 0; i < records.length; i++) {
      r = records[i];
      if (r.type !== 'attributes' || r.attributeName !== 'style') return true;
      // Les transforms animés de l'auteur changent `style` à chaque image : ignorer ceux sans effet sur le flux.
      t = r.target;
      if (t.parentNode && t.parentNode.nodeType === 1 && t.parentNode.matches && t.parentNode.matches(query)) return true;
    }
    return false;
  }
  // Applique tout de suite les modifications en attente (avant une mesure synchrone de l'auteur).
  function flush() { if (observer) { var records = observer.takeRecords(); if (records.length && relevant(records)) apply(); } }
  function start() {
    // Appliqué dans le même tour que la modification (avant l'affichage) : pas d'image sans espacement.
    observer = new MutationObserver(function (records) { if (relevant(records)) apply(); });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class', 'hidden', 'style'] });
    // L'auteur mesure parfois juste après un innerHTML, avant la microtâche de l'observateur : on vide la file
    // avant chaque getBoundingClientRect (uniquement sur un moteur sans flex gap, donc sur la TV).
    var measure = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function () { flush(); return measure.apply(this, arguments); };
    // Pour les règles CSS générées par ma-tv/build.py (pseudo-éléments, que le JS ne peut pas décaler).
    document.documentElement.className += ' cf-no-flexgap';
    window.CleanFrameCompat = { flexGap: 'polyfill', refresh: apply, flush: flush };
    apply();
  }
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
}());
