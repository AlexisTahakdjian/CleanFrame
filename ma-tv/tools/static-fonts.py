"""ma-tv : instances statiques des polices variables de l'auteur, pour Chromium 76 / Tizen 6.0.

Constat (recette ma-tv) : Chromium 76 affiche une police variable à sa graisse par défaut et ignore
font-weight en plage comme font-variation-settings. Manrope (défaut 200) apparaissait donc trop fin.
La doc Samsung (Web Engine Specifications) indique aussi « No » pour ces fonctions en Tizen 6.0.

Ce script découpe les fichiers variables EXACTS de app/ en graisses fixes (fontTools, licence OFL sans
« Reserved Font Name » : modification autorisée, licence conservée). Les fichiers produits sont versionnés
dans ma-tv/assets/fonts/ : le build n'a besoin d'aucune dépendance. À relancer seulement si l'auteur
change ses polices (le build le signale grâce à SOURCES.json).

Usage : .local/venv/bin/python ma-tv/tools/static-fonts.py   (venv : pip install fonttools brotli)
"""
from pathlib import Path
import hashlib
import json

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ma-tv/assets/fonts'
# Graisses réellement utilisées par l'app (style.css, FONTS dans main.js).
FONTS = [
    ('app/assets/manrope.woff2', 'manrope', 'Manrope', [400, 500, 600]),
    ('app/assets/fonts/geist/Geist-Variable.ttf', 'geist', 'Study Geist', [300, 400]),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {}
    for source, slug, family, weights in FONTS:
        data = (ROOT / source).read_bytes()
        sources[source] = hashlib.sha256(data).hexdigest()
        for weight in weights:
            font = TTFont(ROOT / source)
            static = instancer.instantiateVariableFont(font, {'wght': weight}, updateFontNames=False)
            static.flavor = 'woff2'
            target = OUT / f'{slug}-{weight}.woff2'
            static.save(target)
            print(f'{target.relative_to(ROOT)}  ({target.stat().st_size // 1024} Ko, {family} {weight})')
    (OUT / 'SOURCES.json').write_text(json.dumps({'generated_from_sha256': sources}, indent=2) + '\n')


if __name__ == '__main__':
    main()
