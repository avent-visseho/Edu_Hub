"""Services métiers du domaine examens et concours.

Regroupe les opérations lourdes de la chaîne : répartition des candidats,
anonymisation des copies, délibération et production des documents officiels.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.engines.reporting import BlocTableau, EnTeteDocument, generer_document
from app.models.diplome import DiplomeDelivre, StatutDiplome
from app.models.examen import (
    Candidat,
    CentreComposition,
    Convocation,
    Copie,
    DecisionExamen,
    EpreuveExamen,
    NoteExamen,
    RegleMention,
    ResultatExamen,
    SalleComposition,
    SessionExamen,
    StatutDossier,
    StatutNoteExamen,
    StatutSession,
    TypeConvocation,
)
from app.models.scolarite import Serie
from app.utils.calculs import (
    ElementNote,
    calculer_rangs,
    determiner_mention,
    moyenne_ponderee,
    ramener_sur_20,
    taux,
    totaux_ponderes,
)
from app.utils.codes import (
    generer_code_anonymat,
    generer_code_verification,
    generer_numero_diplome,
    generer_numero_table,
)


async def charger_session(session: AsyncSession, session_id: uuid.UUID) -> SessionExamen:
    stmt = (
        select(SessionExamen)
        .where(SessionExamen.id == session_id)
        .options(selectinload(SessionExamen.examen))
    )
    session_examen = (await session.execute(stmt)).scalar_one_or_none()
    if session_examen is None:
        raise NotFoundError("Session d'examen introuvable.")
    return session_examen


# ------------------------------------------------------------------
#  Répartition des candidats
# ------------------------------------------------------------------


async def repartir_candidats(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    par_departement: bool = True,
    prioriser_amenagements: bool = True,
    melanger_etablissements: bool = True,
) -> dict:
    """Affecte chaque candidat validé à un centre, une salle et une place.

    Les candidats bénéficiant d'aménagements sont placés en priorité dans les
    salles aménagées ; à défaut, les candidats d'un même établissement sont
    répartis entre les salles afin de limiter les risques de fraude.
    """
    session_examen = await charger_session(session, session_id)

    stmt = (
        select(SalleComposition, CentreComposition)
        .join(CentreComposition, CentreComposition.id == SalleComposition.centre_id)
        .where(CentreComposition.session_id == session_id, CentreComposition.actif.is_(True))
        .order_by(CentreComposition.code, SalleComposition.code)
    )
    salles = [(salle, centre) for salle, centre in (await session.execute(stmt)).all()]
    if not salles:
        raise BusinessRuleError(
            "Aucune salle de composition n'est déclarée : créez d'abord les centres."
        )

    stmt = (
        select(Candidat)
        .where(
            Candidat.session_id == session_id,
            Candidat.statut_dossier.in_([StatutDossier.VALIDE, StatutDossier.CONVOQUE]),
        )
        .order_by(Candidat.departement_id, Candidat.etablissement_id, Candidat.nom)
    )
    candidats = list((await session.execute(stmt)).scalars())
    if not candidats:
        raise BusinessRuleError("Aucun candidat validé n'est à répartir.")

    # Réinitialisation des compteurs.
    occupation: dict[uuid.UUID, int] = {salle.id: 0 for salle, _ in salles}
    compteur_centre: dict[uuid.UUID, int] = {}

    salles_par_departement: dict[uuid.UUID | None, list] = {}
    for salle, centre in salles:
        cle = centre.departement_id if par_departement else None
        salles_par_departement.setdefault(cle, []).append((salle, centre))

    if melanger_etablissements:
        # Alterne les établissements afin de disperser les candidats d'un même lycée.
        par_etablissement: dict[uuid.UUID | None, list[Candidat]] = {}
        for candidat in candidats:
            par_etablissement.setdefault(candidat.etablissement_id, []).append(candidat)
        entrelaces: list[Candidat] = []
        files = list(par_etablissement.values())
        while any(files):
            for file in files:
                if file:
                    entrelaces.append(file.pop(0))
        candidats = entrelaces

    non_affectes = 0
    for candidat in candidats:
        cle = candidat.departement_id if par_departement else None
        disponibles = salles_par_departement.get(cle) or salles

        cible = None
        if prioriser_amenagements and candidat.type_handicap.value != "AUCUN":
            cible = next(
                (
                    (salle, centre)
                    for salle, centre in disponibles
                    if salle.salle_amenagee and occupation[salle.id] < salle.capacite
                ),
                None,
            )
        if cible is None:
            cible = next(
                (
                    (salle, centre)
                    for salle, centre in disponibles
                    if occupation[salle.id] < salle.capacite
                ),
                None,
            )
        if cible is None:
            non_affectes += 1
            continue

        salle, centre = cible
        occupation[salle.id] += 1
        compteur_centre[centre.id] = compteur_centre.get(centre.id, 0) + 1

        candidat.centre_id = centre.id
        candidat.salle_composition_id = salle.id
        candidat.numero_place = occupation[salle.id]
        candidat.numero_table = generer_numero_table(centre.code[-5:], compteur_centre[centre.id])
        candidat.statut_dossier = StatutDossier.CONVOQUE

    details = []
    for salle, _ in salles:
        salle.nombre_candidats = occupation[salle.id]
        salle.place_debut = 1 if occupation[salle.id] else None
        salle.place_fin = occupation[salle.id] or None

    centres_vus: dict[uuid.UUID, CentreComposition] = {centre.id: centre for _, centre in salles}
    for centre in centres_vus.values():
        centre.nombre_candidats = compteur_centre.get(centre.id, 0)
        details.append(
            {
                "centre": centre.nom,
                "code": centre.code,
                "candidats": centre.nombre_candidats,
                "capacite": centre.capacite,
                "taux_occupation": taux(centre.nombre_candidats, centre.capacite or 1),
            }
        )

    session_examen.statut = StatutSession.REPARTITION
    await session.flush()

    return {
        "candidats_affectes": len(candidats) - non_affectes,
        "candidats_non_affectes": non_affectes,
        "centres_utilises": len([c for c in centres_vus.values() if c.nombre_candidats]),
        "salles_utilisees": len([s for s, _ in salles if occupation[s.id]]),
        "details": sorted(details, key=lambda item: -item["candidats"]),
    }


# ------------------------------------------------------------------
#  Copies
# ------------------------------------------------------------------


async def generer_copies(session: AsyncSession, session_id: uuid.UUID) -> dict:
    """Crée une copie anonymée par candidat convoqué et par épreuve applicable."""
    await charger_session(session, session_id)

    epreuves = list(
        (
            await session.execute(
                select(EpreuveExamen).where(EpreuveExamen.session_id == session_id)
            )
        ).scalars()
    )
    if not epreuves:
        raise BusinessRuleError("Aucune épreuve n'est définie pour cette session.")

    candidats = list(
        (
            await session.execute(
                select(Candidat).where(
                    Candidat.session_id == session_id,
                    Candidat.statut_dossier == StatutDossier.CONVOQUE,
                )
            )
        ).scalars()
    )

    existantes = {
        (copie.candidat_id, copie.epreuve_id)
        for copie in (
            await session.execute(select(Copie).where(Copie.session_id == session_id))
        ).scalars()
    }

    epreuves_par_serie: dict[uuid.UUID | None, list[EpreuveExamen]] = {}
    for epreuve in epreuves:
        epreuves_par_serie.setdefault(epreuve.serie_id, []).append(epreuve)

    creees = 0
    codes_utilises: set[str] = set()
    for candidat in candidats:
        applicables = epreuves_par_serie.get(candidat.serie_id) or epreuves_par_serie.get(None, [])
        for epreuve in applicables:
            if (candidat.id, epreuve.id) in existantes:
                continue
            code = generer_code_anonymat()
            while code in codes_utilises:
                code = generer_code_anonymat()
            codes_utilises.add(code)

            session.add(
                Copie(
                    session_id=session_id,
                    epreuve_id=epreuve.id,
                    candidat_id=candidat.id,
                    code_anonymat=code,
                    nombre_feuillets=1,
                )
            )
            creees += 1

    await session.flush()
    return {"copies_creees": creees, "candidats": len(candidats), "epreuves": len(epreuves)}


# ------------------------------------------------------------------
#  Délibération
# ------------------------------------------------------------------


async def deliberer(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    moyenne_admission: float | None = None,
    repechage_maximum: float = 0.5,
    appliquer_note_eliminatoire: bool = True,
    publier: bool = False,
) -> dict:
    """Calcule les moyennes, applique les règles d'admission et arrête les résultats."""
    session_examen = await charger_session(session, session_id)
    examen = session_examen.examen
    seuil = moyenne_admission or (examen.moyenne_admission if examen else 10.0)

    regles = list(
        (
            await session.execute(
                select(RegleMention)
                .where(RegleMention.examen_id == session_examen.examen_id)
                .order_by(RegleMention.seuil_min)
            )
        ).scalars()
    )
    baremes = [(r.seuil_min, r.seuil_max, r.libelle) for r in regles] or None

    stmt = (
        select(NoteExamen, EpreuveExamen)
        .join(EpreuveExamen, EpreuveExamen.id == NoteExamen.epreuve_id)
        .where(NoteExamen.session_id == session_id)
    )
    lignes = (await session.execute(stmt)).all()
    if not lignes:
        raise BusinessRuleError("Aucune note n'a été saisie pour cette session.")

    par_candidat: dict[uuid.UUID, list[tuple[NoteExamen, EpreuveExamen]]] = {}
    for note, epreuve in lignes:
        par_candidat.setdefault(note.candidat_id, []).append((note, epreuve))

    candidats = {
        candidat.id: candidat
        for candidat in (
            await session.execute(select(Candidat).where(Candidat.session_id == session_id))
        ).scalars()
    }
    resultats_existants = {
        resultat.candidat_id: resultat
        for resultat in (
            await session.execute(
                select(ResultatExamen).where(ResultatExamen.session_id == session_id)
            )
        ).scalars()
    }

    horodatage = datetime.now(UTC)
    moyennes_nationales: dict[str, float | None] = {}
    par_departement: dict[uuid.UUID | None, dict[str, float | None]] = {}
    par_etablissement: dict[uuid.UUID | None, dict[str, float | None]] = {}
    produits: list[ResultatExamen] = []

    for candidat_id, notes in par_candidat.items():
        candidat = candidats.get(candidat_id)
        if candidat is None:
            continue

        elements = [
            ElementNote(
                ramener_sur_20(note.valeur, epreuve.bareme), note.coefficient or epreuve.coefficient
            )
            for note, epreuve in notes
            if note.valeur is not None and note.statut is not StatutNoteExamen.ABSENT
        ]
        points, coefficients = totaux_ponderes(elements)
        moyenne = moyenne_ponderee(elements)

        eliminatoire = appliquer_note_eliminatoire and any(
            note.statut is StatutNoteExamen.NOTE_ELIMINATOIRE
            or (
                epreuve.note_eliminatoire is not None
                and note.valeur is not None
                and ramener_sur_20(note.valeur, epreuve.bareme) < epreuve.note_eliminatoire
            )
            for note, epreuve in notes
        )
        fraude = any(note.statut is StatutNoteExamen.FRAUDE for note, _ in notes)
        absent = not elements

        points_jury = 0.0
        if (
            moyenne is not None
            and not eliminatoire
            and not fraude
            and seuil - repechage_maximum <= moyenne < seuil
        ):
            points_jury = round(seuil - moyenne, 2)

        moyenne_finale = None if moyenne is None else round(moyenne + points_jury, 2)

        if fraude:
            decision = DecisionExamen.EXCLU
        elif absent:
            decision = DecisionExamen.ABSENT
        elif eliminatoire:
            decision = DecisionExamen.NON_ADMIS
        elif moyenne_finale is not None and moyenne_finale >= seuil:
            decision = DecisionExamen.ADMIS
        else:
            decision = DecisionExamen.NON_ADMIS

        resultat = resultats_existants.get(candidat_id)
        if resultat is None:
            resultat = ResultatExamen(session_id=session_id, candidat_id=candidat_id)
            session.add(resultat)

        resultat.serie_id = candidat.serie_id
        resultat.etablissement_id = candidat.etablissement_id
        resultat.departement_id = candidat.departement_id
        resultat.total_points = points
        resultat.total_coefficients = coefficients
        resultat.moyenne = moyenne_finale
        resultat.decision = decision
        resultat.mention = (
            determiner_mention(moyenne_finale, baremes)
            if decision is DecisionExamen.ADMIS
            else None
        )
        resultat.repeche = points_jury > 0
        resultat.points_jury = points_jury
        resultat.motivation_jury = "Repêchage accordé par le jury." if points_jury else None
        resultat.publie = publier
        resultat.publie_le = horodatage if publier else None
        resultat.code_verification = resultat.code_verification or generer_code_verification()

        candidat.statut_dossier = (
            StatutDossier.ADMIS if decision is DecisionExamen.ADMIS else StatutDossier.NON_ADMIS
        )

        moyennes_nationales[str(candidat_id)] = moyenne_finale
        par_departement.setdefault(candidat.departement_id, {})[str(candidat_id)] = moyenne_finale
        par_etablissement.setdefault(candidat.etablissement_id, {})[str(candidat_id)] = (
            moyenne_finale
        )
        produits.append(resultat)

    # Rangs.
    rangs_nationaux = calculer_rangs(moyennes_nationales)
    rangs_departementaux = {
        cle: rang
        for valeurs in par_departement.values()
        for cle, rang in calculer_rangs(valeurs).items()
    }
    rangs_etablissement = {
        cle: rang
        for valeurs in par_etablissement.values()
        for cle, rang in calculer_rangs(valeurs).items()
    }
    for resultat in produits:
        cle = str(resultat.candidat_id)
        resultat.rang_national = rangs_nationaux.get(cle)
        resultat.rang_departemental = rangs_departementaux.get(cle)
        resultat.rang_etablissement = rangs_etablissement.get(cle)

    admis = sum(1 for r in produits if r.decision is DecisionExamen.ADMIS)
    presents = sum(1 for r in produits if r.decision is not DecisionExamen.ABSENT)
    moyennes = [r.moyenne for r in produits if r.moyenne is not None]

    session_examen.nombre_presents = presents
    session_examen.nombre_absents = len(produits) - presents
    session_examen.nombre_admis = admis
    session_examen.taux_reussite = taux(admis, presents or 1)
    session_examen.moyenne_generale = moyenne_ponderee([ElementNote(m, 1.0) for m in moyennes])
    session_examen.statut = (
        StatutSession.RESULTATS_PUBLIES if publier else StatutSession.DELIBERATION
    )
    if publier:
        session_examen.resultats_publies_le = horodatage

    await session.flush()

    return {
        "candidats_deliberes": len(produits),
        "admis": admis,
        "non_admis": len(produits) - admis,
        "taux_reussite": session_examen.taux_reussite,
        "moyenne_generale": session_examen.moyenne_generale,
        "repeches": sum(1 for r in produits if r.repeche),
        "publie": publier,
    }


# ------------------------------------------------------------------
#  Diplômes et convocations
# ------------------------------------------------------------------


async def delivrer_diplomes(session: AsyncSession, session_id: uuid.UUID) -> dict:
    """Émet un diplôme pour chaque lauréat de la session."""
    session_examen = await charger_session(session, session_id)
    examen = session_examen.examen
    sigle = (examen.sigle or examen.code) if examen else "DIP"

    stmt = (
        select(ResultatExamen, Candidat)
        .join(Candidat, Candidat.id == ResultatExamen.candidat_id)
        .where(
            ResultatExamen.session_id == session_id,
            ResultatExamen.decision == DecisionExamen.ADMIS,
        )
        .order_by(ResultatExamen.rang_national)
    )
    laureats = (await session.execute(stmt)).all()

    existants = {
        diplome.candidat_id
        for diplome in (
            await session.execute(
                select(DiplomeDelivre).where(DiplomeDelivre.session_id == session_id)
            )
        ).scalars()
    }

    sequence = int(
        (
            await session.execute(
                select(func.count())
                .select_from(DiplomeDelivre)
                .where(DiplomeDelivre.annee == session_examen.annee)
            )
        ).scalar_one()
    )

    series = {serie.id: serie.code for serie in (await session.execute(select(Serie))).scalars()}

    emis = 0
    for resultat, candidat in laureats:
        if candidat.id in existants:
            continue
        sequence += 1
        emis += 1
        session.add(
            DiplomeDelivre(
                numero=generer_numero_diplome(sigle, session_examen.annee, sequence),
                code_verification=generer_code_verification(),
                apprenant_id=candidat.apprenant_id,
                candidat_id=candidat.id,
                session_id=session_id,
                diplome_ref_id=examen.diplome_delivre_id if examen else None,
                etablissement_id=candidat.etablissement_id,
                titulaire_nom=candidat.nom_complet,
                titulaire_date_naissance=candidat.date_naissance,
                titulaire_lieu_naissance=candidat.lieu_naissance,
                intitule=f"Diplôme du {sigle}",
                serie_libelle=series.get(candidat.serie_id),
                session_libelle=session_examen.libelle,
                annee=session_examen.annee,
                moyenne=resultat.moyenne,
                mention=resultat.mention,
                statut=StatutDiplome.EMIS,
                date_delivrance=date.today(),
                signataire="Le Directeur des examens et concours",
                qualite_signataire="Directeur",
            )
        )

    await session.flush()
    return {"diplomes_emis": emis, "laureats": len(laureats)}


async def generer_convocations(session: AsyncSession, session_id: uuid.UUID) -> dict:
    """Émet la convocation de chaque candidat convoqué."""
    session_examen = await charger_session(session, session_id)

    stmt = (
        select(Candidat, SalleComposition, CentreComposition)
        .join(SalleComposition, SalleComposition.id == Candidat.salle_composition_id)
        .join(CentreComposition, CentreComposition.id == Candidat.centre_id)
        .where(
            Candidat.session_id == session_id,
            Candidat.statut_dossier == StatutDossier.CONVOQUE,
        )
    )
    affectes = (await session.execute(stmt)).all()

    existantes = {
        convocation.candidat_id
        for convocation in (
            await session.execute(
                select(Convocation).where(
                    Convocation.session_id == session_id,
                    Convocation.type_convocation == TypeConvocation.CANDIDAT,
                )
            )
        ).scalars()
    }

    emises = 0
    for candidat, salle, centre in affectes:
        if candidat.id in existantes:
            continue
        emises += 1
        session.add(
            Convocation(
                session_id=session_id,
                type_convocation=TypeConvocation.CANDIDAT,
                candidat_id=candidat.id,
                numero=f"CONV-{candidat.numero_candidat}",
                destinataire=candidat.nom_complet,
                centre_nom=centre.nom,
                salle_nom=salle.nom,
                numero_place=candidat.numero_place,
                date_convocation=session_examen.date_debut,
                consignes=(
                    "Se présenter une heure avant la première épreuve, muni de cette "
                    "convocation et d'une pièce d'identité. Tout appareil électronique "
                    "est interdit dans la salle."
                ),
                code_verification=generer_code_verification(),
            )
        )

    if emises:
        session_examen.statut = StatutSession.CONVOCATIONS_EMISES
    await session.flush()
    return {"convocations_emises": emises, "candidats_convoques": len(affectes)}


def composer_pdf_convocation(convocation: Convocation, session_examen: SessionExamen) -> bytes:
    """Produit le PDF d'une convocation."""
    entete = EnTeteDocument(
        ministere="Ministère en charge de l'éducation",
        direction="Direction des examens et concours",
        titre="Convocation",
        sous_titre=session_examen.libelle,
    )
    informations = {
        "Destinataire": convocation.destinataire,
        "Numéro": convocation.numero,
        "Centre de composition": convocation.centre_nom or "—",
        "Salle": convocation.salle_nom or "—",
        "Place": str(convocation.numero_place or "—"),
        "Date": convocation.date_convocation.strftime("%d/%m/%Y")
        if convocation.date_convocation
        else "—",
        "Heure de convocation": convocation.heure_convocation.strftime("%H:%M")
        if convocation.heure_convocation
        else "07:00",
    }
    return generer_document(
        entete,
        [informations, convocation.consignes or ""],
        code_verification=convocation.code_verification,
    )


def composer_pdf_releve(
    resultat: ResultatExamen,
    candidat: Candidat,
    session_examen: SessionExamen,
    notes: list[tuple[NoteExamen, EpreuveExamen, str]],
) -> bytes:
    """Produit le relevé de notes d'un candidat."""
    entete = EnTeteDocument(
        ministere="Ministère en charge de l'éducation",
        direction="Direction des examens et concours",
        titre="Relevé de notes",
        sous_titre=session_examen.libelle,
    )
    identite = {
        "Candidat": candidat.nom_complet,
        "Numéro de candidat": candidat.numero_candidat,
        "Numéro de table": candidat.numero_table or "—",
        "Date de naissance": candidat.date_naissance.strftime("%d/%m/%Y"),
        "Lieu de naissance": candidat.lieu_naissance or "—",
    }
    tableau = BlocTableau(
        entetes=["Épreuve", "Note / 20", "Coefficient", "Points"],
        lignes=[
            [
                libelle,
                "—" if note.valeur is None else f"{note.valeur:.2f}".replace(".", ","),
                f"{note.coefficient:g}",
                "—" if note.points is None else f"{note.points:.2f}".replace(".", ","),
            ]
            for note, epreuve, libelle in notes
        ],
        alignements={1: "center", 2: "center", 3: "center"},
    )
    synthese = {
        "Total des points": f"{resultat.total_points or 0:.2f}".replace(".", ","),
        "Total des coefficients": f"{resultat.total_coefficients or 0:g}",
        "Moyenne": f"{resultat.moyenne:.2f}".replace(".", ",") if resultat.moyenne else "—",
        "Mention": resultat.mention or "—",
        "Décision": resultat.decision.value,
        "Rang national": str(resultat.rang_national or "—"),
    }
    return generer_document(
        entete,
        [identite, tableau, synthese],
        code_verification=resultat.code_verification,
    )


def composer_pdf_diplome(diplome: DiplomeDelivre) -> bytes:
    """Produit le diplôme imprimable."""
    entete = EnTeteDocument(
        republique="République du Bénin",
        ministere="Ministère en charge de l'éducation",
        titre=diplome.intitule,
        sous_titre=diplome.session_libelle or f"Session {diplome.annee}",
    )
    corps = {
        "Numéro": diplome.numero,
        "Titulaire": diplome.titulaire_nom,
        "Né(e) le": diplome.titulaire_date_naissance.strftime("%d/%m/%Y")
        if diplome.titulaire_date_naissance
        else "—",
        "À": diplome.titulaire_lieu_naissance or "—",
        "Série": diplome.serie_libelle or "—",
        "Moyenne": f"{diplome.moyenne:.2f}".replace(".", ",") if diplome.moyenne else "—",
        "Mention": diplome.mention or "—",
        "Délivré le": diplome.date_delivrance.strftime("%d/%m/%Y"),
        "Signataire": diplome.signataire or "—",
    }
    return generer_document(
        entete,
        [
            corps,
            "Le présent diplôme est délivré pour servir et valoir ce que de droit.",
        ],
        code_verification=diplome.code_verification,
    )
