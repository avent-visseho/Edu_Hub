#!/usr/bin/env python
"""Regénère deploy_ment/contraintes.txt depuis l'environnement de développement.

pyproject.toml déclare des minimums (« >= ») : c'est ce qu'il faut pour
développer, mais une image construite dans six mois n'installerait pas les
mêmes versions que celle d'aujourd'hui. Ce script relève l'arbre de
dépendances exact du .venv courant et le fige.

    python deploy_ment/figer-dependances.py

À relancer après chaque mise à jour volontaire des dépendances, puis à
redéployer. Les outils de développement (pytest, ruff, mypy…) sont ignorés :
ils ne sont pas installés dans l'image.
"""

from __future__ import annotations

import re
import sys
import tomllib
from importlib.metadata import PackageNotFoundError, distribution, distributions
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

RACINE = Path(__file__).resolve().parent.parent
PYPROJECT = RACINE / "pyproject.toml"
SORTIE = RACINE / "deploy_ment" / "contraintes.txt"

ENTETE = """# EduHub — versions figées pour la production
#
# Fichier généré : ne le modifiez pas à la main, relancez
#   python deploy_ment/figer-dependances.py
#
# pyproject.toml déclare des minimums (« >= »), ce qui est juste pour
# développer mais dangereux pour déployer : deux constructions à six mois
# d'intervalle n'installeraient pas les mêmes versions. Le cas s'est présenté
# ici — une installation libre résout SQLAlchemy 2.1, alors que le code a été
# écrit et vérifié sur la 2.0.
#
# Ce fichier ne fait que contraindre : il n'installe rien de lui-même, c'est
# toujours pyproject.toml qui décide de la liste des paquets.
"""


def canonique(nom: str) -> str:
    """Normalise un nom de distribution (PEP 503) : « Pillow » et « pillow »
    désignent le même paquet, « typing_extensions » et « typing-extensions »
    aussi."""
    return re.sub(r"[-_.]+", "-", nom).lower()


def inventaire() -> dict[str, tuple[str, str]]:
    """Nom canonique → (nom déclaré, version) pour tout ce qui est installé."""
    trouves: dict[str, tuple[str, str]] = {}
    for dist in distributions():
        nom = dist.metadata["Name"]
        if nom:
            trouves[canonique(nom)] = (nom, dist.version)
    return trouves


def fermeture(racines: list[str], environnement: dict[str, str]) -> set[str]:
    """Ensemble canonique des paquets réellement nécessaires à l'exécution.

    On part des dépendances déclarées dans pyproject.toml et on suit les
    « Requires-Dist » des paquets installés. Les marqueurs d'environnement sont
    évalués pour la plateforme cible (Linux, CPython 3.12) et les extras ne sont
    suivis que s'ils ont été demandés — sans quoi on ramasserait, par exemple,
    toute la chaîne de test de httpx.
    """
    a_traiter = [(Requirement(brut), frozenset()) for brut in racines]
    vus: set[str] = set()

    while a_traiter:
        exigence, extras_parents = a_traiter.pop()
        if exigence.marker and not any(
            exigence.marker.evaluate({**environnement, "extra": extra})
            for extra in (extras_parents or {""})
        ):
            continue

        cle = canonique(exigence.name)
        extras = frozenset(exigence.extras)
        signature = f"{cle}[{','.join(sorted(extras))}]"
        if signature in vus:
            continue
        vus.add(signature)

        try:
            metadonnees = distribution(exigence.name)
        except PackageNotFoundError:
            print(f"  ! {exigence.name} n'est pas installé — ignoré", file=sys.stderr)
            continue

        for brut in metadonnees.requires or []:
            a_traiter.append((Requirement(brut), extras))

    return {signature.split("[", 1)[0] for signature in vus}


def main() -> int:
    if not (RACINE / ".venv").exists():
        print("Aucun .venv à la racine d'EduHub_api : rien à figer.", file=sys.stderr)
        return 1

    projet = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    installe = inventaire()
    environnement = {**default_environment(), "extra": ""}

    necessaires = fermeture(projet["dependencies"], environnement)
    # Le projet lui-même est installé en mode éditable : il n'a rien à faire
    # dans un fichier de contraintes.
    necessaires.discard(canonique(projet["name"]))

    lignes, manquants = [], []
    for cle in sorted(necessaires):
        if cle in installe:
            nom, version = installe[cle]
            lignes.append(f"{nom}=={version}")
        else:
            manquants.append(cle)

    SORTIE.write_text(ENTETE + "\n" + "\n".join(lignes) + "\n", encoding="utf-8")

    print(f"{SORTIE.relative_to(RACINE)} : {len(lignes)} paquets figés")
    if manquants:
        print("  ! absents de l'environnement :", ", ".join(manquants), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
