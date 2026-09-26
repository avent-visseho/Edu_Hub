"""Contexte partagé par les étapes du générateur de données."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import SeedScale
from app.core.logging import get_logger
from app.seed.frontiere import dans_le_pays
from app.seed.scolaire import NOMS, PRENOMS_FEMININS, PRENOMS_MASCULINS

logger = get_logger("seed")


@dataclass(frozen=True, slots=True)
class Volumetrie:
    """Volumes cibles d'une exécution du générateur."""

    etablissements: int
    apprenants: int
    enseignants: int
    classes_par_etablissement: int
    annees: int
    candidats_par_session: int
    entreprises: int
    projets: int
    livres: int
    cours: int

    @property
    def libelle(self) -> str:
        return (
            f"{self.etablissements} établissements, {self.apprenants} apprenants, "
            f"{self.enseignants} enseignants"
        )


VOLUMETRIES: dict[SeedScale, Volumetrie] = {
    "tiny": Volumetrie(12, 400, 60, 3, 2, 120, 8, 12, 60, 8),
    "small": Volumetrie(60, 2500, 300, 4, 3, 600, 20, 40, 200, 20),
    "medium": Volumetrie(250, 12000, 1400, 5, 3, 2500, 45, 90, 500, 40),
    "large": Volumetrie(1000, 50000, 5500, 6, 4, 9000, 90, 200, 1200, 80),
}


@dataclass
class ContexteSeed:
    """État partagé entre les étapes : générateur aléatoire, caches et compteurs."""

    session: AsyncSession
    volumetrie: Volumetrie
    graine: int = 2026
    rng: random.Random = field(init=False)
    caches: dict[str, dict[str, Any]] = field(default_factory=dict)
    compteurs: dict[str, int] = field(default_factory=dict)
    statistiques: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.graine)

    # ---------- Caches ----------

    def cache(self, nom: str) -> dict[str, Any]:
        """Table de correspondance `code métier → identifiant`, par famille."""
        return self.caches.setdefault(nom, {})

    def enregistrer(self, nom: str, code: str, valeur: Any) -> Any:
        self.cache(nom)[code] = valeur
        return valeur

    def recuperer(self, nom: str, code: str) -> Any:
        return self.cache(nom).get(code)

    # ---------- Compteurs ----------

    def suivant(self, nom: str) -> int:
        valeur = self.compteurs.get(nom, 0) + 1
        self.compteurs[nom] = valeur
        return valeur

    def comptabiliser(self, nom: str, nombre: int = 1) -> None:
        self.statistiques[nom] = self.statistiques.get(nom, 0) + nombre

    # ---------- Aléas utilitaires ----------

    def choix(self, population):
        return self.rng.choice(list(population))

    def echantillon(self, population, taille: int) -> list:
        population = list(population)
        taille = min(taille, len(population))
        return self.rng.sample(population, taille)

    def probabilite(self, seuil: float) -> bool:
        return self.rng.random() < seuil

    def entier(self, minimum: int, maximum: int) -> int:
        return self.rng.randint(minimum, maximum)

    def note(self, centre: float = 11.5, dispersion: float = 3.6) -> float:
        """Note sur 20 tirée d'une loi normale bornée, arrondie au quart de point."""
        valeur = self.rng.gauss(centre, dispersion)
        valeur = max(0.0, min(20.0, valeur))
        return round(valeur * 4) / 4

    def date_entre(self, debut: date, fin: date) -> date:
        ecart = (fin - debut).days
        return debut + timedelta(days=self.rng.randint(0, max(ecart, 0)))

    def coordonnees(self, latitude: float, longitude: float, rayon: float = 0.25):
        """Position dispersée autour d'un point de référence, dans le pays.

        Le tirage uniforme dans un carré ne connaît pas les frontières : autour
        de Cotonou il tombe dans le golfe de Guinée, à l'ouest il déborde au
        Togo. On retire donc tant que le point n'est pas sur le territoire, en
        resserrant progressivement le rayon pour que la boucle converge même
        lorsque le point de référence est lui-même proche d'une côte ou d'une
        frontière.

        Après vingt essais infructueux — le cas ne se présente pas avec les
        chefs-lieux actuels, mais un point de référence mal placé le
        provoquerait — on rend le point de référence lui-même plutôt que de
        boucler sans fin.
        """
        for essai in range(20):
            portee = rayon * (1 - essai / 25)
            candidat = (
                round(latitude + self.rng.uniform(-portee, portee), 6),
                round(longitude + self.rng.uniform(-portee, portee), 6),
            )
            if dans_le_pays(*candidat):
                return candidat
        return (round(latitude, 6), round(longitude, 6))

    # ---------- Identités ----------

    def identite(self, sexe: str) -> tuple[str, str]:
        """Produit un couple (nom, prénoms) cohérent avec le sexe."""
        prenoms_source = PRENOMS_FEMININS if sexe == "FEMININ" else PRENOMS_MASCULINS
        prenoms = self.choix(prenoms_source)
        if self.probabilite(0.35):
            prenoms = f"{prenoms} {self.choix(prenoms_source)}"
        return self.choix(NOMS), prenoms

    def sexe(self, part_feminine: float = 0.49) -> str:
        return "FEMININ" if self.probabilite(part_feminine) else "MASCULIN"

    def telephone(self) -> str:
        prefixe = self.choix(("01 9", "01 6", "01 4", "01 5"))
        return f"+229 {prefixe}{self.entier(1000000, 9999999)}"

    # ---------- Écriture en base ----------

    async def inserer(self, modele, lignes: list[dict[str, Any]], lot: int = 2000) -> None:
        """Insertion en masse par lots, avec horodatage automatique."""
        if not lignes:
            return
        for debut in range(0, len(lignes), lot):
            await self.session.execute(insert(modele), lignes[debut : debut + lot])
        nom = getattr(modele, "__tablename__", None) or getattr(modele, "name", str(modele))
        self.comptabiliser(nom, len(lignes))

    @staticmethod
    def nouvel_id() -> uuid.UUID:
        return uuid.uuid4()
