/* ma-tv : réglages de la TV d'Alexis (Samsung UE43AU7105, Tizen 6.0), lus par device.js et main.js.
   IDs relevés sur la TV le 2026-10-20 (`python3 ma-tv/tv.py applist`). Au build, ma-tv/build.py fusionne
   la section "local" de .local/ma-tv.json par-dessus. Hors de ce fichier, l'app de l'auteur est inchangée. */
window.CleanFrameLocal = {
  // Apps dont l'auteur fournit le logo (assets/icons) et installées sur cette TV.
  primaryApps: [
    { id: 'netflix', name: 'Netflix', mark: true, appId: 'org.tizen.netflix-app' },
    { id: 'youtube', name: 'YouTube', mark: true, appId: '9Ur5IzDKqV.TizenYouTube' },
    { id: 'primevideo', name: 'Prime Video', mark: true, appId: 'org.tizen.primevideo' },
    { id: 'disneyplus', name: 'Disney+', mark: true, appId: 'MCmYXNxgcu.DisneyPlus' },
    { id: 'appletv', name: 'Apple TV', mark: true, appId: 'com.samsung.tv.aria-video' }
  ],
  // Autres apps de la TV (monogramme ou icône de la TV), nommées dès le démarrage.
  extraApps: [
    { appId: 'kIciSQlYEM.plex', name: 'Plex' },
    { appId: 'aLlph042JZ.arte', name: 'ARTE' },
    { appId: 'QY16tZ64E3.francetv', name: 'france.tv' },
    { appId: 'Ol7HVEXtqh.6play', name: 'M6+' },
    { appId: 'Jz7aUrV2Q4.Twitch', name: 'Twitch' },
    { appId: 'yu1NM3vHsU.DAZN', name: 'DAZN' },
    { appId: 'RffagId0eC.SfrSport', name: 'RMC Sport' }
  ],
  // Accueil au premier lancement (9 au plus ; ensuite, l'ordre se règle à la télécommande et est conservé).
  defaultHome: ['youtube', 'netflix', 'kIciSQlYEM.plex', 'aLlph042JZ.arte', 'QY16tZ64E3.francetv', 'appletv',
    'Jz7aUrV2Q4.Twitch', 'yu1NM3vHsU.DAZN', 'RffagId0eC.SfrSport'],
  // Langue et format de l'heure par défaut (modifiables ensuite dans Réglages → Langue et heure).
  locale: { lang: 'fr', clock: '24h' },
  // Contrôles masqués : Art Mode (org.tizen.art-app existe, mais la TV déclare FrameTVSupport=false).
  hideUtils: ['art'],
  // Écrans Samsung ouverts par « Samsung Home » et « TV settings » (IDs présents sur cette TV).
  // 'hide' = mettre CleanFrame en arrière-plan à la place.
  system: { home: 'com.samsung.tv.csfs', settings: 'com.samsung.tv.coba.setting' }
};
