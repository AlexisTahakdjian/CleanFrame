# ma-tv : CleanFrame sur la Samsung UE43AU7105 d'Alexis

La branche `ma-tv` adapte [CleanFrame](https://github.com/nthnclrk/CleanFrame) (écran d'accueil pour The Frame, Tizen 9) à une Samsung **UE43AU7105KXXC** de 2021 : **Tizen 6.0, moteur Chromium 76**. Les fichiers de l'auteur restent intacts, à quelques lignes marquées `ma-tv` près ; le reste est appliqué au build, sur une copie. Aucun script de l'auteur n'est exécuté, et l'outil qui modifiait le Home natif a été retiré.

**État au 2026-10-20 :** installée, lancée et validée sur la TV ; 0 erreur console ; accueil utilisable en 0,5-0,65 s (photo complète en 3,7-3,9 s) ; certificats valables **jusqu'au 2027-10-20**.

## La commande de mise à jour

```sh
ma-tv/maj              # depuis la racine du dépôt, TV allumée
ma-tv/maj --dry-run    # voir les nouveautés de l'auteur sans rien changer
```

Elle récupère la version de l'auteur, fusionne, construit, teste dans Chromium 76, signe, installe et lance sur la TV ; `ma-tv` n'avance et le fork n'est publié **qu'une fois la TV validée**. Au moindre problème, tout s'arrête et rien ne change. Détails et options : [procédure](docs/procedure.md#mettre-à-jour--ma-tvmaj).

## Documentation

| Document | Contenu |
| --- | --- |
| [procedure](docs/procedure.md) | Pas à pas : prérequis du Mac, outils Samsung, mode développeur, certificats, sauvegarde, première installation, `ma-tv/maj`, conflit de fusion, inspecteur, fork public, renouvellement annuel des certificats |
| [resultats-tests](docs/resultats-tests.md) | Recette navigateur, mesures sur la TV, recette à la télécommande, verdict des critères |
| [modifications](docs/modifications.md) | Chaque changement de la branche : commit, raison, fichiers |
| [profil-tv](docs/profil-tv.md) | Fiche de la TV : système, moteur, capacités sdb, apps, contradictions avec la doc |
| [compatibilite](docs/compatibilite.md) | Chaque API, réglage, fonction JS et CSS face à Tizen 6.0, et ce que ma-tv en a fait |
| [risques](docs/risques.md) | Revue des risques : TV, certificats, réseau, fiabilité, mise à jour automatique |
| [plan-b](docs/plan-b.md) | Replis si une fonction ne marche pas, et comment basculer |
| [retour-arriere](docs/retour-arriere.md) | Revenir à une version validée, ou tout désinstaller dans l'ordre |

## Contenu du dossier

| Chemin | Rôle |
| --- | --- |
| `maj` | Raccourci de `update.py` |
| `update.py` | La mise à jour en une commande |
| `build.py` | Barrières et adaptations Tizen 6.0 → `dist/ma-tv/*.wgt` |
| `sign.py` | Signature avec le profil Samsung, contrôle du certificat auteur et des dates |
| `tv.py` | Commandes vers la TV (`info`, `connect`, `capability`, `applist`, `permit`, `install`, `launch`, `debug`, `uninstall`, `rollback`, `disconnect`), affichées et confirmées |
| `lib.py` | Configuration, journal, garde-fou d'identité de la TV |
| `harness/` | Recette Chromium 76 / référence (`run.mjs`) et inspection sur la TV (`tv-inspect.mjs`) |
| `tools/` | Télécommande réseau (`remote.mjs`), graisses fixes des polices (`static-fonts.py`) |
| `assets/fonts/` | Graisses fixes Manrope et Geist (OFL) |
| `config.example.json` | Valeurs par défaut versionnées |

Les valeurs privées (adresses, identité de l'app, jeton, chemins) sont dans `.local/ma-tv.json`, ignoré par git ; les certificats dans `~/SamsungCertificate/`. Ne jamais les publier : le fork est public.
