"""Étape 1 — Référentiels : territoire, nomenclatures, années académiques."""

from __future__ import annotations

from datetime import date

from app.models.referentiel import (
    Arrondissement,
    Commune,
    Cycle,
    Departement,
    Diplome,
    OrdreEnseignement,
    StatutEtablissement,
    TypeBourse,
    TypeDocument,
    TypeEtablissement,
    TypeExamen,
    TypeFormation,
    TypeHandicapRef,
    TypeSalle,
    Village,
)
from app.models.scolarite import (
    AnneeAcademique,
    Filiere,
    Matiere,
    MatiereNiveau,
    Niveau,
    Periode,
    Serie,
    TypePeriode,
)
from app.seed import donnees, scolaire
from app.seed.contexte import ContexteSeed, logger


async def generer(ctx: ContexteSeed) -> None:
    await _territoire(ctx)
    await _nomenclatures(ctx)
    await _structure_academique(ctx)
    await _annees(ctx)
    logger.info("Référentiels générés.")


# ------------------------------------------------------------------


async def _territoire(ctx: ContexteSeed) -> None:
    """12 départements, 77 communes, arrondissements et villages."""
    departements, communes, arrondissements, villages = [], [], [], []

    for ordre, (code, libelle, chef_lieu, lat, lon) in enumerate(donnees.DEPARTEMENTS):
        ident = ctx.nouvel_id()
        ctx.enregistrer("departement", code, ident)
        departements.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "chef_lieu": chef_lieu,
                "latitude": lat,
                "longitude": lon,
                "population": ctx.entier(400_000, 1_400_000),
                "actif": True,
                "ordre": ordre,
            }
        )

        for index, nom_commune in enumerate(donnees.COMMUNES[code], start=1):
            code_commune = f"{code}-{index:02d}"
            id_commune = ctx.nouvel_id()
            ctx.enregistrer("commune", code_commune, id_commune)
            ctx.cache("communes_par_departement").setdefault(code, []).append(code_commune)
            latitude, longitude = ctx.coordonnees(lat, lon, 0.45)
            communes.append(
                {
                    "id": id_commune,
                    "code": code_commune,
                    "libelle": nom_commune,
                    "departement_id": ident,
                    "latitude": latitude,
                    "longitude": longitude,
                    "population": ctx.entier(25_000, 350_000),
                    "actif": True,
                    "ordre": index,
                }
            )

            for rang in range(1, ctx.entier(2, 5)):
                code_arrondissement = f"{code_commune}-{rang:02d}"
                id_arrondissement = ctx.nouvel_id()
                lat_a, lon_a = ctx.coordonnees(latitude, longitude, 0.12)
                arrondissements.append(
                    {
                        "id": id_arrondissement,
                        "code": code_arrondissement,
                        "libelle": f"{nom_commune} {rang}",
                        "commune_id": id_commune,
                        "latitude": lat_a,
                        "longitude": lon_a,
                        "actif": True,
                        "ordre": rang,
                    }
                )
                ctx.cache("arrondissements_par_commune").setdefault(code_commune, []).append(
                    id_arrondissement
                )

                for numero in range(1, ctx.entier(2, 4)):
                    villages.append(
                        {
                            "id": ctx.nouvel_id(),
                            "code": f"{code_arrondissement}-{numero:02d}",
                            "libelle": f"{nom_commune} quartier {rang}-{numero}",
                            "arrondissement_id": id_arrondissement,
                            "quartier_ville": ctx.probabilite(0.4),
                            "actif": True,
                            "ordre": numero,
                        }
                    )

    await ctx.inserer(Departement, departements)
    await ctx.inserer(Commune, communes)
    await ctx.inserer(Arrondissement, arrondissements)
    await ctx.inserer(Village, villages)


async def _nomenclatures(ctx: ContexteSeed) -> None:
    """Ordres d'enseignement, cycles, types et catégories de référence."""
    ordres = []
    for rang, (code, libelle) in enumerate(donnees.ORDRES_ENSEIGNEMENT):
        ident = ctx.enregistrer("ordre", code, ctx.nouvel_id())
        ordres.append({"id": ident, "code": code, "libelle": libelle, "actif": True, "ordre": rang})
    await ctx.inserer(OrdreEnseignement, ordres)

    cycles = []
    for rang, (code, libelle, code_ordre, duree) in enumerate(donnees.CYCLES):
        ident = ctx.enregistrer("cycle", code, ctx.nouvel_id())
        cycles.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "ordre_enseignement_id": ctx.recuperer("ordre", code_ordre),
                "duree_annees": duree,
                "actif": True,
                "ordre": rang,
            }
        )
    await ctx.inserer(Cycle, cycles)

    types_etab = []
    for rang, (code, libelle, code_ordre) in enumerate(donnees.TYPES_ETABLISSEMENT):
        ident = ctx.enregistrer("type_etablissement", code, ctx.nouvel_id())
        types_etab.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "ordre_enseignement_id": ctx.recuperer("ordre", code_ordre),
                "actif": True,
                "ordre": rang,
            }
        )
    await ctx.inserer(TypeEtablissement, types_etab)

    statuts = []
    for rang, (code, libelle) in enumerate(donnees.STATUTS_ETABLISSEMENT):
        ident = ctx.enregistrer("statut_etablissement", code, ctx.nouvel_id())
        statuts.append(
            {"id": ident, "code": code, "libelle": libelle, "actif": True, "ordre": rang}
        )
    await ctx.inserer(StatutEtablissement, statuts)

    salles = []
    for rang, (code, libelle) in enumerate(donnees.TYPES_SALLE):
        ident = ctx.enregistrer("type_salle", code, ctx.nouvel_id())
        salles.append({"id": ident, "code": code, "libelle": libelle, "actif": True, "ordre": rang})
    await ctx.inserer(TypeSalle, salles)

    documents = []
    for rang, (code, libelle, extensions, taille) in enumerate(donnees.TYPES_DOCUMENT):
        ident = ctx.enregistrer("type_document", code, ctx.nouvel_id())
        documents.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "extensions_autorisees": extensions,
                "taille_max_ko": taille,
                "actif": True,
                "ordre": rang,
            }
        )
    await ctx.inserer(TypeDocument, documents)

    examens = []
    for rang, (code, libelle, concours, code_ordre) in enumerate(donnees.TYPES_EXAMEN):
        ident = ctx.enregistrer("type_examen", code, ctx.nouvel_id())
        examens.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "est_concours": concours,
                "ordre_enseignement_id": ctx.recuperer("ordre", code_ordre),
                "actif": True,
                "ordre": rang,
            }
        )
    await ctx.inserer(TypeExamen, examens)

    bourses = []
    for rang, (code, libelle, montant) in enumerate(donnees.TYPES_BOURSE):
        ident = ctx.enregistrer("type_bourse", code, ctx.nouvel_id())
        bourses.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "montant_indicatif": montant,
                "actif": True,
                "ordre": rang,
            }
        )
    await ctx.inserer(TypeBourse, bourses)

    formations = []
    for rang, (code, libelle) in enumerate(donnees.TYPES_FORMATION):
        ident = ctx.enregistrer("type_formation", code, ctx.nouvel_id())
        formations.append(
            {"id": ident, "code": code, "libelle": libelle, "actif": True, "ordre": rang}
        )
    await ctx.inserer(TypeFormation, formations)

    handicaps = []
    for rang, (code, libelle, categorie, amenagements) in enumerate(donnees.TYPES_HANDICAP):
        ident = ctx.enregistrer("type_handicap", code, ctx.nouvel_id())
        handicaps.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "categorie": categorie,
                "amenagements": amenagements or None,
                "actif": True,
                "ordre": rang,
            }
        )
    await ctx.inserer(TypeHandicapRef, handicaps)

    diplomes = []
    for rang, (code, libelle, qualification, code_cycle) in enumerate(donnees.DIPLOMES):
        ident = ctx.enregistrer("diplome", code, ctx.nouvel_id())
        diplomes.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "niveau_qualification": qualification,
                "cycle_id": ctx.recuperer("cycle", code_cycle),
                "actif": True,
                "ordre": rang,
            }
        )
    await ctx.inserer(Diplome, diplomes)


async def _structure_academique(ctx: ContexteSeed) -> None:
    """Niveaux, séries, filières, matières et programmes par niveau."""
    niveaux = []
    for code, libelle, code_cycle, rang in scolaire.NIVEAUX:
        ident = ctx.enregistrer("niveau", code, ctx.nouvel_id())
        ctx.cache("cycle_du_niveau")[code] = code_cycle
        niveaux.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "cycle_id": ctx.recuperer("cycle", code_cycle),
                "rang": rang,
                "niveau_examen_id": ctx.recuperer(
                    "type_examen", scolaire.NIVEAU_EXAMEN.get(code, "")
                ),
                "actif": True,
            }
        )
    await ctx.inserer(Niveau, niveaux)

    series = []
    for code, libelle, code_cycle, technique in scolaire.SERIES:
        ident = ctx.enregistrer("serie", code, ctx.nouvel_id())
        series.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "cycle_id": ctx.recuperer("cycle", code_cycle),
                "technique": technique,
                "actif": True,
            }
        )
    await ctx.inserer(Serie, series)

    filieres = []
    for code, libelle, code_diplome, duree in scolaire.FILIERES:
        ident = ctx.enregistrer("filiere", code, ctx.nouvel_id())
        filieres.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "diplome_id": ctx.recuperer("diplome", code_diplome),
                "duree_annees": duree,
                "debouches": f"Métiers du secteur « {libelle} » et poursuite d'études.",
                "actif": True,
            }
        )
    await ctx.inserer(Filiere, filieres)

    matieres = []
    for code, libelle, abreviation, domaine, coefficient, volume in scolaire.MATIERES:
        ident = ctx.enregistrer("matiere", code, ctx.nouvel_id())
        matieres.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "abreviation": abreviation,
                "domaine": domaine,
                "coefficient_defaut": coefficient,
                "volume_horaire_defaut": volume,
                "actif": True,
            }
        )
    await ctx.inserer(Matiere, matieres)

    await _programmes(ctx)


async def _programmes(ctx: ContexteSeed) -> None:
    """Associe à chaque niveau — et à chaque série — ses matières et coefficients."""
    liens: list[dict] = []
    vus: set[tuple] = set()

    coefficients_defaut = {code: coef for code, _, _, _, coef, _ in scolaire.MATIERES}
    volumes_defaut = {code: vol for code, _, _, _, _, vol in scolaire.MATIERES}

    for code_niveau, _, code_cycle, _ in scolaire.NIVEAUX:
        if code_niveau in scolaire.NIVEAUX_SECOND_CYCLE:
            continue
        matieres = scolaire.PROGRAMME_PAR_NIVEAU.get(code_cycle)
        if not matieres:
            continue
        for code_matiere in matieres:
            cle = (code_matiere, code_niveau, None)
            if cle in vus:
                continue
            vus.add(cle)
            liens.append(
                {
                    "id": ctx.nouvel_id(),
                    "matiere_id": ctx.recuperer("matiere", code_matiere),
                    "niveau_id": ctx.recuperer("niveau", code_niveau),
                    "serie_id": None,
                    "coefficient": coefficients_defaut[code_matiere],
                    "volume_horaire": volumes_defaut[code_matiere],
                    "obligatoire": True,
                }
            )
        ctx.cache("matieres_du_niveau")[code_niveau] = list(matieres)

    for code_niveau in scolaire.NIVEAUX_SECOND_CYCLE:
        for code_serie, programme in scolaire.PROGRAMME_PAR_SERIE.items():
            ctx.cache("matieres_de_la_serie")[code_serie] = [m for m, _ in programme]
            ctx.cache("coefficients_de_la_serie")[code_serie] = dict(programme)
            for code_matiere, coefficient in programme:
                cle = (code_matiere, code_niveau, code_serie)
                if cle in vus:
                    continue
                vus.add(cle)
                liens.append(
                    {
                        "id": ctx.nouvel_id(),
                        "matiere_id": ctx.recuperer("matiere", code_matiere),
                        "niveau_id": ctx.recuperer("niveau", code_niveau),
                        "serie_id": ctx.recuperer("serie", code_serie),
                        "coefficient": float(coefficient),
                        "volume_horaire": volumes_defaut[code_matiere],
                        "obligatoire": True,
                    }
                )

    await ctx.inserer(MatiereNiveau, liens)


async def _annees(ctx: ContexteSeed) -> None:
    """Années académiques et périodes d'évaluation (trimestres)."""
    annee_courante = date.today().year
    premiere = annee_courante - ctx.volumetrie.annees + 1

    annees, periodes = [], []
    for decalage in range(ctx.volumetrie.annees):
        debut = premiere + decalage
        code = f"{debut}-{debut + 1}"
        ident = ctx.enregistrer("annee", code, ctx.nouvel_id())
        courante = debut == annee_courante
        ctx.cache("annees_ordonnees").setdefault("liste", []).append(code)
        if courante:
            ctx.enregistrer("annee", "courante", ident)
            ctx.enregistrer("annee_code", "courante", code)

        annees.append(
            {
                "id": ident,
                "code": code,
                "libelle": f"Année académique {code}",
                "annee_debut": debut,
                "annee_fin": debut + 1,
                "date_debut": date(debut, 9, 15),
                "date_fin": date(debut + 1, 7, 15),
                "courante": courante,
                "cloturee": debut < annee_courante,
            }
        )

        bornes = (
            (date(debut, 9, 15), date(debut, 12, 20)),
            (date(debut + 1, 1, 5), date(debut + 1, 3, 31)),
            (date(debut + 1, 4, 5), date(debut + 1, 6, 30)),
        )
        for numero, (debut_periode, fin_periode) in enumerate(bornes, start=1):
            code_periode = f"T{numero}"
            id_periode = ctx.nouvel_id()
            ctx.cache("periodes_par_annee").setdefault(code, []).append((code_periode, id_periode))
            periodes.append(
                {
                    "id": id_periode,
                    "annee_id": ident,
                    "code": code_periode,
                    "libelle": f"Trimestre {numero}",
                    "type_periode": TypePeriode.TRIMESTRE,
                    "numero": numero,
                    "date_debut": debut_periode,
                    "date_fin": fin_periode,
                    "coefficient": 1.0,
                    "saisie_ouverte": courante,
                    "notes_publiees": not courante or numero < 3,
                }
            )

    await ctx.inserer(AnneeAcademique, annees)
    await ctx.inserer(Periode, periodes)
