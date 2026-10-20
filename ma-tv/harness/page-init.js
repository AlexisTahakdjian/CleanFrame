/* ma-tv : script injecté dans la page de test avant tout autre script (ES5, compatible Chromium 76).
   - imite strictement l'API Tizen publique utilisée par l'app (et note tout autre accès) ;
   - mesure le temps jusqu'à l'écran prêt ;
   - permet de simuler masquage/reprise, stockage et catalogue en échec.
   Configuration : window.__maTvTest = { mock, catalog, launch, catalogMode, selfId, seed, hidden } */
(function () {
  'use strict';
  var T = window.__maTvTest || {};
  var tv = window.__tv = { calls: [], unknown: [], catalogCalls: 0, launchMode: T.launch || 'ok', catalogMode: T.catalogMode || 'ok' };

  if (T.seed !== undefined && !sessionStorage.getItem('__ma_tv_seeded')) {
    if (T.seed === null) localStorage.clear(); else localStorage.setItem('cleanframe.home.v1', JSON.stringify(T.seed));
    sessionStorage.setItem('__ma_tv_seeded', '1');
  }
  window.__setHidden = function (value) {
    Object.defineProperty(document, 'hidden', { configurable: true, get: function () { return value; } });
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: function () { return value ? 'hidden' : 'visible'; } });
    document.dispatchEvent(new Event('visibilitychange'));
  };
  // Écran prêt : première image où l'app se déclare prête (polices, fond et photo affichés).
  window.__readyAt = 0;
  (function watch() {
    if (window.ShoreQA && typeof window.ShoreQA.ready === 'function' && window.ShoreQA.ready()) {
      window.__readyAt = performance.now(); return;
    }
    requestAnimationFrame(watch);
  }());

  if (!T.mock) return;
  function strict(name, target) {
    if (!window.Proxy) return target;
    return new Proxy(target, { get: function (t, k) {
      if (typeof k === 'string' && !(k in t) && k !== 'then' && k !== 'toJSON') tv.unknown.push(name + '.' + k);
      return t[k];
    } });
  }
  function later(fn) { setTimeout(fn, 0); }
  var app = {
    getAppsInfo: function (ok, fail) {
      tv.catalogCalls++;
      later(function () {
        if (tv.catalogMode === 'fail') fail({ name: 'UnknownError', message: 'Catalogue indisponible (test)' });
        else ok((T.catalog || []).map(function (a) { return { id: a.id, name: a.name, show: a.show !== false, iconPath: a.iconPath || '' }; }));
      });
    },
    launch: function (id, ok, fail) {
      tv.calls.push({ method: 'launch', id: id });
      if (tv.launchMode === 'silent') return;
      var installed = (T.catalog || []).some(function (a) { return a.id === id; }) || (T.system || []).indexOf(id) >= 0;
      later(function () {
        if (tv.launchMode === 'fail' || !installed) fail({ name: 'NotFoundError', message: 'Application introuvable (test) : ' + id });
        else ok();
      });
    },
    launchAppControl: function (control, id, ok, fail) {
      tv.calls.push({ method: 'launchAppControl', id: id });
      later(function () { if ((T.system || []).indexOf(id) >= 0) ok(); else fail({ name: 'NotFoundError', message: 'Application introuvable (test) : ' + id }); });
    },
    getCurrentApplication: function () {
      return strict('Application', {
        appInfo: { id: T.selfId || 'test.CleanFrame', name: 'CleanFrame' },
        hide: function () { tv.calls.push({ method: 'hide' }); },
        exit: function () { tv.calls.push({ method: 'exit' }); }
      });
    }
  };
  window.tizen = strict('tizen', {
    ApplicationControlData: function (key, value) { this.key = key; this.value = value; },
    ApplicationControl: function (operation, uri, mime, category, data) { this.operation = operation; this.data = data; },
    application: strict('tizen.application', app),
    tvinputdevice: strict('tizen.tvinputdevice', {
      registerKey: function (k) { tv.calls.push({ method: 'registerKey', key: k }); },
      registerKeyBatch: function (k) { tv.calls.push({ method: 'registerKeyBatch', keys: k }); },
      unregisterKey: function () {}, getSupportedKeys: function () { return []; }
    })
  });
}());
