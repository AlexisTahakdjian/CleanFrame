/* ma-tv : réglages de la TV d'Alexis (Samsung UE43AU7105, Tizen 6.0), lus par device.js et main.js.
   Valeurs par défaut versionnées. Au build, ma-tv/build.py fusionne la section "local" de
   .local/ma-tv.json (IDs relevés sur la TV) par-dessus. Hors de ce fichier, l'app de l'auteur est inchangée. */
window.CleanFrameLocal = {
  // Apps proposées sur l'accueil au premier lancement. IDs à confirmer par `ma-tv/tv.py applist`.
  primaryApps: [
    { id: 'netflix', name: 'Netflix', mark: true, appId: 'org.tizen.netflix-app' },
    { id: 'youtube', name: 'YouTube', mark: true, appId: '9Ur5IzDKqV.TizenYouTube' },
    { id: 'primevideo', name: 'Prime Video', mark: true, appId: 'org.tizen.primevideo' }
  ],
  // Contrôles absents de cette TV : Art Mode est propre à The Frame (FrameTVSupport=false).
  hideUtils: ['art'],
  // Écrans Samsung ouverts par « Samsung Home » et « TV settings ». 'hide' = mettre CleanFrame en arrière-plan.
  system: { home: 'com.samsung.tv.csfs', settings: 'com.samsung.tv.coba.setting' }
};
