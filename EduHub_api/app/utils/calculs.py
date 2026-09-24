"""Calculs académiques : moyennes pondérées, rangs, mentions, taux."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

#: Barème de mentions par défaut, applicable si l'examen n'en définit aucun.
MENTIONS_DEFAUT: tuple[tuple[float, float, str], ...] = (
    (18.0, 20.0, "Excellent"),
    (16.0, 18.0, "Très bien"),
    (14.0, 16.0, "Bien"),
    (12.0, 14.0, "Assez bien"),
    (10.0, 12.0, "Passable"),
)

#: Appréciations automatiques sur une note sur 20.
APPRECIATIONS: tuple[tuple[float, str], ...] = (
    (18.0, "Excellent travail"),
    (16.0, "Très bon niveau"),
    (14.0, "Bon travail"),
    (12.0, "Assez bon travail"),
    (10.0, "Travail satisfaisant"),
    (8.0, "Travail insuffisant"),
    (5.0, "Travail très insuffisant"),
    (0.0, "Résultats préoccupants"),
)


@dataclass(frozen=True, slots=True)
class ElementNote:
    """Élément entrant dans le calcul d'une moyenne pondérée."""

    valeur: float
    coefficient: float = 1.0


def ramener_sur_20(valeur: float, bareme: float) -> float:
    """Convertit une note sur un barème quelconque en note sur 20."""
    if bareme <= 0:
        return round(valeur, 2)
    return round(valeur * 20.0 / bareme, 2)


def moyenne_simple(valeurs: Sequence[float]) -> float | None:
    valeurs_valides = [v for v in valeurs if v is not None]
    if not valeurs_valides:
        return None
    return round(sum(valeurs_valides) / len(valeurs_valides), 2)


def moyenne_ponderee(elements: Iterable[ElementNote]) -> float | None:
    """Moyenne pondérée par les coefficients."""
    total_points = 0.0
    total_coefficients = 0.0
    for element in elements:
        if element.valeur is None:
            continue
        total_points += element.valeur * element.coefficient
        total_coefficients += element.coefficient
    if total_coefficients == 0:
        return None
    return round(total_points / total_coefficients, 2)


def totaux_ponderes(elements: Iterable[ElementNote]) -> tuple[float, float]:
    """Renvoie (total des points, total des coefficients)."""
    total_points = 0.0
    total_coefficients = 0.0
    for element in elements:
        if element.valeur is None:
            continue
        total_points += element.valeur * element.coefficient
        total_coefficients += element.coefficient
    return round(total_points, 2), round(total_coefficients, 2)


def ecart_type(valeurs: Sequence[float]) -> float | None:
    valeurs_valides = [v for v in valeurs if v is not None]
    if len(valeurs_valides) < 2:
        return None
    moyenne = sum(valeurs_valides) / len(valeurs_valides)
    variance = sum((v - moyenne) ** 2 for v in valeurs_valides) / len(valeurs_valides)
    return round(variance**0.5, 2)


def calculer_rangs(valeurs: dict[str, float | None]) -> dict[str, int]:
    """Attribue un rang à chaque entrée, les ex æquo partageant le même rang.

    Les valeurs nulles sont classées en dernier.
    """
    classables = [(cle, val) for cle, val in valeurs.items() if val is not None]
    classables.sort(key=lambda item: item[1], reverse=True)

    rangs: dict[str, int] = {}
    rang_courant = 0
    precedente: float | None = None
    for position, (cle, valeur) in enumerate(classables, start=1):
        if valeur != precedente:
            rang_courant = position
            precedente = valeur
        rangs[cle] = rang_courant

    dernier = len(classables) + 1
    for cle, valeur in valeurs.items():
        if valeur is None:
            rangs[cle] = dernier
    return rangs


def determiner_mention(
    moyenne: float | None,
    baremes: Sequence[tuple[float, float, str]] | None = None,
) -> str | None:
    """Détermine la mention correspondant à une moyenne."""
    if moyenne is None:
        return None
    for seuil_min, seuil_max, libelle in baremes or MENTIONS_DEFAUT:
        if seuil_min <= moyenne <= seuil_max:
            return libelle
    return None


def determiner_appreciation(moyenne: float | None) -> str | None:
    if moyenne is None:
        return None
    for seuil, libelle in APPRECIATIONS:
        if moyenne >= seuil:
            return libelle
    return APPRECIATIONS[-1][1]


def taux(numerateur: float, denominateur: float) -> float:
    """Pourcentage arrondi à deux décimales, robuste au dénominateur nul."""
    if denominateur == 0:
        return 0.0
    return round(numerateur * 100.0 / denominateur, 2)


def progression(avant: float | None, apres: float | None) -> float | None:
    """Écart absolu entre deux moyennes successives."""
    if avant is None or apres is None:
        return None
    return round(apres - avant, 2)
