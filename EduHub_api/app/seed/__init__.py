"""Générateur de données fictives du Bénin éducatif simulé.

Le générateur produit un jeu de données cohérent de bout en bout : chaque
apprenant appartient à une classe, d'un établissement, d'une commune, d'un
département ; ses notes alimentent ses moyennes, son bulletin, sa candidature à
un examen, son résultat, son diplôme, puis son orientation et son insertion.
"""

from __future__ import annotations

import time

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.logging import get_logger, setup_logging
from app.seed.contexte import VOLUMETRIES, ContexteSeed

logger = get_logger("seed")

#: Étapes exécutées dans l'ordre, chacune s'appuyant sur les précédentes.
ETAPES: tuple[tuple[str, str], ...] = (
    ("Référentiels et années académiques", "app.seed.etape_referentiels"),
    ("Rôles, permissions et structures", "app.seed.etape_identite"),
    ("Établissements et infrastructures", "app.seed.etape_etablissements"),
    ("Enseignants, apprenants et parents", "app.seed.etape_personnes"),
    ("Classes, inscriptions et assiduité", "app.seed.etape_scolarite"),
    ("Évaluations, notes et bulletins", "app.seed.etape_evaluations"),
    ("Examens, concours et diplômes", "app.seed.etape_examens"),
    ("Vie étudiante, projets et emploi", "app.seed.etape_vie"),
    ("Gouvernance, règles et indicateurs", "app.seed.etape_gouvernance"),
)


async def executer(echelle: str | None = None, graine: int | None = None) -> dict[str, int]:
    """Exécute l'ensemble des étapes du générateur et renvoie les volumes produits."""
    import importlib

    setup_logging()
    echelle = echelle or settings.seed_scale
    volumetrie = VOLUMETRIES[echelle]

    logger.info("Génération des données — échelle « %s » : %s", echelle, volumetrie.libelle)
    depart = time.perf_counter()

    async with SessionFactory() as session:
        contexte = ContexteSeed(
            session=session,
            volumetrie=volumetrie,
            graine=graine if graine is not None else settings.seed_random_seed,
        )

        for libelle, module_nom in ETAPES:
            etape_depart = time.perf_counter()
            module = importlib.import_module(module_nom)
            await module.generer(contexte)

            # Les comptes d'administration dépendent des structures créées.
            if module_nom.endswith("etape_identite"):
                await module.generer_comptes_administration(contexte)

            await session.commit()
            logger.info("  ✔ %s (%.1f s)", libelle, time.perf_counter() - etape_depart)

    duree = time.perf_counter() - depart
    total = sum(contexte.statistiques.values())
    logger.info("Génération terminée : %d lignes en %.1f s.", total, duree)
    return contexte.statistiques
