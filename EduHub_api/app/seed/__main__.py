"""Point d'entrée en ligne de commande : `python -m app.seed`."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import settings
from app.seed import executer
from app.seed.contexte import VOLUMETRIES


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed",
        description="Génère le jeu de données fictives complet de la plateforme EduHub.",
    )
    parser.add_argument(
        "--echelle",
        choices=sorted(VOLUMETRIES),
        default=settings.seed_scale,
        help="Volume de données à produire (défaut : %(default)s).",
    )
    parser.add_argument(
        "--graine",
        type=int,
        default=settings.seed_random_seed,
        help="Graine aléatoire, pour reproduire exactement un jeu de données.",
    )
    arguments = parser.parse_args()

    statistiques = asyncio.run(executer(arguments.echelle, arguments.graine))

    largeur = max((len(nom) for nom in statistiques), default=0)
    print("\nVolumes générés :")
    for nom, total in sorted(statistiques.items(), key=lambda item: -item[1]):
        print(f"  {nom.ljust(largeur)}  {total:>9,}".replace(",", " "))
    print(f"\n  {'TOTAL'.ljust(largeur)}  {sum(statistiques.values()):>9,}".replace(",", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
