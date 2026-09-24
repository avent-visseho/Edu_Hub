"""Moteur de recherche — constructeur de requêtes et recherche globale.

Permet à l'administration d'interroger les données sans écrire de SQL :

    SI Département = Atlantique
    ET Type établissement = CEG
    ET Moyenne générale >= 18
    ALORS afficher les élèves
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.exceptions import ValidationError


class Operateur(StrEnum):
    """Opérateurs disponibles dans le constructeur de requêtes."""

    EGAL = "eq"
    DIFFERENT = "ne"
    SUPERIEUR = "gt"
    SUPERIEUR_EGAL = "gte"
    INFERIEUR = "lt"
    INFERIEUR_EGAL = "lte"
    CONTIENT = "contains"
    COMMENCE_PAR = "startswith"
    FINIT_PAR = "endswith"
    DANS = "in"
    PAS_DANS = "not_in"
    ENTRE = "between"
    EST_NUL = "is_null"
    NON_NUL = "not_null"


class Conjonction(StrEnum):
    ET = "AND"
    OU = "OR"


@dataclass(frozen=True, slots=True)
class Critere:
    """Critère élémentaire : champ, opérateur, valeur."""

    champ: str
    operateur: Operateur
    valeur: Any = None


@dataclass(frozen=True, slots=True)
class DescripteurChamp:
    """Champ exposé au constructeur de requêtes."""

    cle: str
    libelle: str
    colonne: InstrumentedAttribute
    type_valeur: str = "texte"
    choix: tuple[str, ...] = ()


class ConstructeurRequete:
    """Traduit des critères déclaratifs en clauses SQLAlchemy sûres.

    Seuls les champs explicitement déclarés sont interrogeables : aucune
    expression fournie par l'utilisateur n'est interprétée.
    """

    def __init__(self, entite: str, champs: Sequence[DescripteurChamp]) -> None:
        self.entite = entite
        self.champs = {champ.cle: champ for champ in champs}

    def decrire(self) -> list[dict[str, Any]]:
        """Expose les variables disponibles à l'interface du query builder."""
        return [
            {
                "cle": champ.cle,
                "libelle": champ.libelle,
                "type": champ.type_valeur,
                "choix": list(champ.choix),
                "operateurs": sorted(self._operateurs_pour(champ.type_valeur)),
            }
            for champ in self.champs.values()
        ]

    @staticmethod
    def _operateurs_pour(type_valeur: str) -> set[str]:
        communs = {Operateur.EGAL, Operateur.DIFFERENT, Operateur.EST_NUL, Operateur.NON_NUL}
        if type_valeur in {"nombre", "date"}:
            communs |= {
                Operateur.SUPERIEUR,
                Operateur.SUPERIEUR_EGAL,
                Operateur.INFERIEUR,
                Operateur.INFERIEUR_EGAL,
                Operateur.ENTRE,
            }
        if type_valeur == "texte":
            communs |= {Operateur.CONTIENT, Operateur.COMMENCE_PAR, Operateur.FINIT_PAR}
        if type_valeur in {"liste", "texte", "uuid"}:
            communs |= {Operateur.DANS, Operateur.PAS_DANS}
        return {operateur.value for operateur in communs}

    def _clause(self, critere: Critere):
        champ = self.champs.get(critere.champ)
        if champ is None:
            raise ValidationError(
                f"Champ « {critere.champ} » non interrogeable pour « {self.entite} ».",
                details={"champs_disponibles": sorted(self.champs)},
            )

        colonne = champ.colonne
        valeur = critere.valeur

        match critere.operateur:
            case Operateur.EGAL:
                return colonne == valeur
            case Operateur.DIFFERENT:
                return colonne != valeur
            case Operateur.SUPERIEUR:
                return colonne > valeur
            case Operateur.SUPERIEUR_EGAL:
                return colonne >= valeur
            case Operateur.INFERIEUR:
                return colonne < valeur
            case Operateur.INFERIEUR_EGAL:
                return colonne <= valeur
            case Operateur.CONTIENT:
                return colonne.ilike(f"%{valeur}%")
            case Operateur.COMMENCE_PAR:
                return colonne.ilike(f"{valeur}%")
            case Operateur.FINIT_PAR:
                return colonne.ilike(f"%{valeur}")
            case Operateur.DANS:
                return colonne.in_(_en_liste(valeur))
            case Operateur.PAS_DANS:
                return colonne.notin_(_en_liste(valeur))
            case Operateur.ENTRE:
                bornes = _en_liste(valeur)
                if len(bornes) != 2:
                    raise ValidationError("L'opérateur « entre » attend exactement deux bornes.")
                return colonne.between(bornes[0], bornes[1])
            case Operateur.EST_NUL:
                return colonne.is_(None)
            case Operateur.NON_NUL:
                return colonne.isnot(None)

        raise ValidationError(f"Opérateur « {critere.operateur} » non pris en charge.")

    def appliquer(
        self,
        statement: Select,
        criteres: Sequence[Critere],
        conjonction: Conjonction = Conjonction.ET,
    ) -> Select:
        """Applique les critères à une requête existante."""
        if not criteres:
            return statement
        clauses = [self._clause(critere) for critere in criteres]
        combinaison = and_(*clauses) if conjonction == Conjonction.ET else or_(*clauses)
        return statement.where(combinaison)

    def trier(self, statement: Select, champ: str | None, sens: str = "asc") -> Select:
        if not champ:
            return statement
        descripteur = self.champs.get(champ)
        if descripteur is None:
            return statement
        colonne = descripteur.colonne
        return statement.order_by(colonne.desc() if sens == "desc" else colonne.asc())


def _en_liste(valeur: Any) -> list[Any]:
    if isinstance(valeur, list | tuple | set):
        return list(valeur)
    if isinstance(valeur, str):
        return [element.strip() for element in valeur.split(",") if element.strip()]
    return [valeur]


def criteres_depuis_dict(donnees: Sequence[dict[str, Any]]) -> list[Critere]:
    """Convertit la charge utile JSON de l'interface en critères typés."""
    criteres: list[Critere] = []
    for element in donnees:
        try:
            operateur = Operateur(element["operateur"])
        except (KeyError, ValueError) as exc:
            raise ValidationError(
                f"Opérateur invalide : {element.get('operateur')!r}.",
                details={"operateurs_valides": [o.value for o in Operateur]},
            ) from exc
        criteres.append(
            Critere(champ=element["champ"], operateur=operateur, valeur=element.get("valeur"))
        )
    return criteres


async def compter(session: AsyncSession, statement: Select) -> int:
    """Compte les lignes d'une requête sans la matérialiser."""
    stmt = select(func.count()).select_from(statement.order_by(None).subquery())
    return int((await session.execute(stmt)).scalar_one())
