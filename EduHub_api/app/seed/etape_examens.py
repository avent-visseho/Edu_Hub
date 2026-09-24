"""Étape 7 — Examens et concours : de la candidature au diplôme.

Reproduit la chaîne complète : création de l'examen, session, séries, épreuves,
pièces requises, candidatures, étude des dossiers, répartition par centre et par
salle, convocations, surveillance, correction, saisie des notes, délibération,
résultats, contentieux, budget et archivage.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from app.models.diplome import DiplomeDelivre, StatutDiplome
from app.models.examen import (
    AffectationSurveillance,
    BudgetExamen,
    Candidat,
    CentreComposition,
    Contentieux,
    Convocation,
    Copie,
    Correcteur,
    DecisionExamen,
    DepenseExamen,
    DocumentCandidat,
    EpreuveArchivee,
    EpreuveExamen,
    Examen,
    IncidentExamen,
    Jury,
    LigneBudgetaire,
    MembreJury,
    MotifRejetPiece,
    NatureExamen,
    NoteExamen,
    PieceRequise,
    PropositionPersonnel,
    RegleMention,
    ResultatExamen,
    RoleSurveillance,
    SalleComposition,
    SerieExamen,
    SessionExamen,
    StatutContentieux,
    StatutDossier,
    StatutNoteExamen,
    StatutPiece,
    StatutProposition,
    StatutSession,
    TypeCandidature,
    TypeContentieux,
    TypeConvocation,
    TypeSession,
)
from app.seed import donnees, scolaire
from app.seed.contexte import ContexteSeed, logger
from app.utils.calculs import (
    ElementNote,
    calculer_rangs,
    determiner_mention,
    moyenne_ponderee,
    taux,
    totaux_ponderes,
)
from app.utils.codes import (
    generer_code_anonymat,
    generer_code_verification,
    generer_numero_candidat,
    generer_numero_diplome,
    generer_numero_table,
    generer_reference,
)

#: Examens nationaux simulés : code, nom, sigle, type, direction, niveau source.
EXAMENS_NATIONAUX: tuple[tuple[str, str, str, str, str, str], ...] = (
    (
        "CEP",
        "Certificat d'études primaires",
        "CEP",
        "CEP",
        "DEC-MEMP",
        "CM2",
    ),
    (
        "BEPC",
        "Brevet d'études du premier cycle",
        "BEPC",
        "BEPC",
        "DEC-MESFTP",
        "3E",
    ),
    (
        "BAC",
        "Baccalauréat de l'enseignement secondaire",
        "BAC",
        "BAC",
        "DOB",
        "TLE",
    ),
)

#: Concours simulés : code, nom, sigle, type, direction, places.
CONCOURS: tuple[tuple[str, str, str, str, str, int], ...] = (
    (
        "CONC-ENS",
        "Concours d'entrée à l'École normale supérieure",
        "ENS",
        "CONC_ENS",
        "DOB",
        250,
    ),
    (
        "CONC-RECRUT",
        "Concours de recrutement d'enseignants",
        "CRE",
        "CONC_RECRUT",
        "DEC-MESFTP",
        1200,
    ),
)

#: Barème de mentions appliqué aux examens nationaux.
MENTIONS = (
    ("Passable", 10.0, 12.0),
    ("Assez bien", 12.0, 14.0),
    ("Bien", 14.0, 16.0),
    ("Très bien", 16.0, 18.0),
    ("Excellent", 18.0, 20.0),
)

#: Pièces exigées de tout candidat.
PIECES_OBLIGATOIRES = ("PHOTO", "ACTE_NAISSANCE", "CERTIFICAT")
PIECES_CANDIDAT_LIBRE = ("QUITTANCE", "CNI")

#: Lignes budgétaires types d'une session.
LIGNES_BUDGET = (
    ("SURV", "Indemnités des surveillants", "PERSONNEL", 0.28),
    ("CORR", "Indemnités des correcteurs", "PERSONNEL", 0.24),
    ("CHEF", "Indemnités des chefs de centre", "PERSONNEL", 0.08),
    ("JURY", "Indemnités des membres de jury", "PERSONNEL", 0.06),
    ("IMPR", "Impression et reprographie des sujets", "LOGISTIQUE", 0.15),
    ("TRANS", "Transport et acheminement", "LOGISTIQUE", 0.10),
    ("MAT", "Matériel et fournitures", "LOGISTIQUE", 0.06),
    ("SEC", "Sécurité et santé", "LOGISTIQUE", 0.03),
)


async def generer(ctx: ContexteSeed) -> None:
    await _examens(ctx)
    await _sessions(ctx)
    logger.info("Examens, sessions, candidats et résultats générés.")


# ------------------------------------------------------------------
#  Configuration des examens
# ------------------------------------------------------------------


async def _examens(ctx: ContexteSeed) -> None:
    examens, regles = [], []

    def ajouter(code, nom, sigle, type_code, direction, nature, **extra):
        ident = ctx.enregistrer("examen", code, ctx.nouvel_id())
        direction_id = ctx.recuperer("structure", direction)
        ministere = next((m for c, _, _, m, _ in donnees.DIRECTIONS if c == direction), "MESFTP")
        ligne = {
            "id": ident,
            "code": code,
            "nom": nom,
            "sigle": sigle,
            "nature": nature,
            "type_examen_id": ctx.recuperer("type_examen", type_code),
            "ministere_id": ctx.recuperer("structure", ministere),
            "direction_responsable_id": direction_id,
            "conditions_admission": "Être régulièrement inscrit et avoir un dossier validé.",
            "reglement": "Le règlement officiel de l'examen s'applique à tous les candidats.",
            "frais_officiel": 0.0,
            "frais_candidat_libre": float(ctx.entier(5000, 15000)),
            "moyenne_admission": 10.0,
            "actif": True,
        }
        ligne.update(extra)
        examens.append(ligne)
        for rang, (libelle, seuil_min, seuil_max) in enumerate(MENTIONS):
            regles.append(
                {
                    "id": ctx.nouvel_id(),
                    "examen_id": ident,
                    "libelle": libelle,
                    "seuil_min": seuil_min,
                    "seuil_max": seuil_max,
                    "ordre": rang,
                }
            )
        return ident

    for code, nom, sigle, type_code, direction, niveau in EXAMENS_NATIONAUX:
        ctx.cache("niveau_source_examen")[code] = niveau
        ajouter(
            code,
            nom,
            sigle,
            type_code,
            direction,
            NatureExamen.EXAMEN,
            niveau_requis_id=ctx.recuperer("niveau", niveau),
            diplome_delivre_id=ctx.recuperer("diplome", code),
        )

    for code, nom, sigle, type_code, direction, places in CONCOURS:
        ajouter(
            code,
            nom,
            sigle,
            type_code,
            direction,
            NatureExamen.CONCOURS,
            places_offertes=places,
            moyenne_admission=float(ctx.entier(9, 12)),
        )

    await ctx.inserer(Examen, examens)
    await ctx.inserer(RegleMention, regles)


# ------------------------------------------------------------------
#  Sessions
# ------------------------------------------------------------------


async def _sessions(ctx: ContexteSeed) -> None:
    annee = date.today().year

    for code_examen, nom, sigle, _, _, niveau_source in EXAMENS_NATIONAUX:
        await _session_complete(
            ctx,
            code_examen=code_examen,
            nom_examen=nom,
            sigle=sigle,
            annee=annee,
            niveau_source=niveau_source,
            avec_series=code_examen == "BAC",
            delivre_diplome=True,
        )

    for code_examen, nom, sigle, _, _, _ in CONCOURS:
        await _session_complete(
            ctx,
            code_examen=code_examen,
            nom_examen=nom,
            sigle=sigle,
            annee=annee,
            niveau_source=None,
            avec_series=False,
            delivre_diplome=False,
        )


async def _session_complete(
    ctx: ContexteSeed,
    *,
    code_examen: str,
    nom_examen: str,
    sigle: str,
    annee: int,
    niveau_source: str | None,
    avec_series: bool,
    delivre_diplome: bool,
) -> None:
    """Déroule une session entière, de l'ouverture des inscriptions à l'archivage."""
    horodatage = datetime.now(UTC)
    id_examen = ctx.recuperer("examen", code_examen)
    code_session = f"{code_examen}-{annee}-N"
    id_session = ctx.nouvel_id()
    ctx.enregistrer("session", code_session, id_session)

    series = list(scolaire.SERIES_GENERALES) if avec_series else []
    epreuves = _epreuves(ctx, id_session, code_session, code_examen, series, annee)
    candidats, documents = _candidats(
        ctx, id_session, code_session, code_examen, sigle, annee, niveau_source, series
    )
    centres, salles = _centres(ctx, id_session, code_session, candidats)
    _repartir(ctx, candidats, centres, salles)

    propositions, affectations = _surveillance(ctx, id_session, centres, salles)
    correcteurs = _correcteurs(ctx, id_session, code_session, epreuves)
    copies, notes = _composition(ctx, id_session, candidats, epreuves, correcteurs)
    jurys, membres, resultats = _deliberation(
        ctx, id_session, code_session, nom_examen, candidats, notes, epreuves, centres
    )
    convocations = _convocations(ctx, id_session, code_session, candidats, affectations)
    contentieux = _contentieux(ctx, id_session, candidats, resultats, epreuves)
    budget, lignes_budget, depenses = _budget(ctx, id_session, code_session, candidats, centres)
    incidents = _incidents(ctx, id_session, centres, candidats, epreuves)
    archives = _archives(ctx, id_session, code_examen, sigle, annee, epreuves)
    diplomes = (
        _diplomes(ctx, id_session, sigle, annee, candidats, resultats) if delivre_diplome else []
    )

    admis = sum(1 for r in resultats if r["decision"] == DecisionExamen.ADMIS)
    presents = sum(1 for c in candidats if c["statut_dossier"] != StatutDossier.REJETE)
    moyennes = [r["moyenne"] for r in resultats if r["moyenne"] is not None]

    session = {
        "id": id_session,
        "examen_id": id_examen,
        "annee_id": ctx.recuperer("annee", "courante"),
        "code": code_session,
        "libelle": f"{nom_examen} — session normale {annee}",
        "type_session": TypeSession.NORMALE,
        "annee": annee,
        "statut": StatutSession.RESULTATS_PUBLIES,
        "inscriptions_debut": date(annee, 1, 15),
        "inscriptions_fin": date(annee, 3, 31),
        "date_debut": date(annee, 6, 10),
        "date_fin": date(annee, 6, 20),
        "date_publication_resultats": date(annee, 7, 20),
        "date_limite_contentieux": date(annee, 8, 5),
        "nombre_inscrits": len(candidats),
        "nombre_presents": presents,
        "nombre_absents": len(candidats) - presents,
        "nombre_admis": admis,
        "taux_reussite": taux(admis, presents or 1),
        "moyenne_generale": moyenne_ponderee([ElementNote(m, 1.0) for m in moyennes]),
        "resultats_publies_le": horodatage,
    }

    await ctx.inserer(SessionExamen, [session])
    if series:
        await ctx.inserer(
            SerieExamen,
            [
                {
                    "id": ctx.nouvel_id(),
                    "session_id": id_session,
                    "serie_id": ctx.recuperer("serie", code_serie),
                    "ouverte": True,
                }
                for code_serie in series
            ],
        )
    await ctx.inserer(EpreuveExamen, [e["ligne"] for e in epreuves])
    await ctx.inserer(PieceRequise, _pieces_requises(ctx, id_session))
    await ctx.inserer(CentreComposition, [c["ligne"] for c in centres])
    await ctx.inserer(SalleComposition, [s["ligne"] for s in salles])
    await ctx.inserer(Candidat, [c["ligne"] for c in candidats])
    await ctx.inserer(DocumentCandidat, documents)
    await ctx.inserer(PropositionPersonnel, propositions)
    await ctx.inserer(AffectationSurveillance, [a["ligne"] for a in affectations])
    await ctx.inserer(Correcteur, [c["ligne"] for c in correcteurs])
    await ctx.inserer(Copie, copies)
    await ctx.inserer(NoteExamen, notes)
    await ctx.inserer(Jury, jurys)
    await ctx.inserer(MembreJury, membres)
    await ctx.inserer(ResultatExamen, resultats)
    await ctx.inserer(Convocation, convocations)
    await ctx.inserer(IncidentExamen, incidents)
    await ctx.inserer(Contentieux, contentieux)
    await ctx.inserer(BudgetExamen, [budget])
    await ctx.inserer(LigneBudgetaire, lignes_budget)
    await ctx.inserer(DepenseExamen, depenses)
    await ctx.inserer(EpreuveArchivee, archives)
    await ctx.inserer(DiplomeDelivre, diplomes)

    logger.info(
        "Session %s : %d candidats, %d admis (%.1f %%).",
        code_session,
        len(candidats),
        admis,
        session["taux_reussite"] or 0.0,
    )


# ------------------------------------------------------------------
#  Épreuves et pièces requises
# ------------------------------------------------------------------


def _epreuves(
    ctx: ContexteSeed,
    id_session,
    code_session: str,
    code_examen: str,
    series: list[str],
    annee: int,
) -> list[dict]:
    """Construit les épreuves de la session, par série le cas échéant."""
    epreuves: list[dict] = []
    debut = date(annee, 6, 10)

    if series:
        for code_serie in series:
            programme = scolaire.PROGRAMME_PAR_SERIE[code_serie]
            for rang, (code_matiere, coefficient) in enumerate(programme):
                if code_matiere == "EPS":
                    continue
                epreuves.append(
                    _epreuve(
                        ctx,
                        id_session,
                        code_session,
                        code_matiere,
                        code_serie,
                        float(coefficient),
                        debut + timedelta(days=rang // 2),
                        rang,
                    )
                )
    else:
        matieres = (
            ("FRA", 4.0),
            ("MATH", 4.0),
            ("ANG", 2.0),
            ("SVT", 2.0),
            ("PC", 2.0),
            ("HG", 2.0),
        )
        if code_examen == "CEP":
            matieres = (("FRA", 3.0), ("MATH", 3.0), ("EVEIL", 2.0), ("HG", 1.0))
        elif code_examen.startswith("CONC"):
            matieres = (("FRA", 3.0), ("MATH", 3.0), ("ECM", 2.0), ("ANG", 1.0))
        for rang, (code_matiere, coefficient) in enumerate(matieres):
            epreuves.append(
                _epreuve(
                    ctx,
                    id_session,
                    code_session,
                    code_matiere,
                    None,
                    coefficient,
                    debut + timedelta(days=rang // 2),
                    rang,
                )
            )
    return epreuves


def _epreuve(
    ctx, id_session, code_session, code_matiere, code_serie, coefficient, jour, rang
) -> dict:
    ident = ctx.nouvel_id()
    libelle_matiere = next(
        (libelle for code, libelle, *_ in scolaire.MATIERES if code == code_matiere),
        code_matiere,
    )
    return {
        "id": ident,
        "matiere": code_matiere,
        "serie": code_serie,
        "coefficient": coefficient,
        "ligne": {
            "id": ident,
            "session_id": id_session,
            "serie_id": ctx.recuperer("serie", code_serie) if code_serie else None,
            "matiere_id": ctx.recuperer("matiere", code_matiere),
            "code": f"{code_session}-{code_serie or 'GEN'}-{code_matiere}",
            "libelle": f"Épreuve de {libelle_matiere}"
            + (f" — série {code_serie}" if code_serie else ""),
            "date_epreuve": jour,
            "heure_debut": time(8, 0) if rang % 2 == 0 else time(14, 0),
            "duree_minutes": ctx.choix([120, 180, 240]),
            "bareme": 20.0,
            "coefficient": coefficient,
            "note_eliminatoire": 3.0 if coefficient >= 4 else None,
            "obligatoire": True,
            "facultative": False,
            "pratique": code_matiere in {"TECHNO", "ATELIER"},
            "orale": False,
            "instructions": "Aucun document ni appareil électronique n'est autorisé.",
        },
    }


def _pieces_requises(ctx: ContexteSeed, id_session) -> list[dict]:
    lignes = []
    for rang, code_type in enumerate(PIECES_OBLIGATOIRES):
        lignes.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "type_document_id": ctx.recuperer("type_document", code_type),
                "obligatoire": True,
                "consignes": "Document lisible, en couleur, au format PDF ou image.",
                "ordre": rang,
            }
        )
    for rang, code_type in enumerate(PIECES_CANDIDAT_LIBRE, start=len(PIECES_OBLIGATOIRES)):
        lignes.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "type_document_id": ctx.recuperer("type_document", code_type),
                "type_candidature": TypeCandidature.LIBRE,
                "obligatoire": True,
                "consignes": "Exigé uniquement des candidats libres.",
                "ordre": rang,
            }
        )
    return lignes


# ------------------------------------------------------------------
#  Candidatures
# ------------------------------------------------------------------


def _candidats(
    ctx: ContexteSeed,
    id_session,
    code_session: str,
    code_examen: str,
    sigle: str,
    annee: int,
    niveau_source: str | None,
    series: list[str],
) -> tuple[list[dict], list[dict]]:
    """Inscrit les élèves du niveau concerné, plus une part de candidats libres."""
    cible = ctx.volumetrie.candidats_par_session
    candidats: list[dict] = []
    documents: list[dict] = []
    horodatage = datetime.now(UTC)

    # --- Candidats officiels, issus des classes du niveau terminal du cycle ---
    viviers: list[tuple[dict, dict]] = []
    if niveau_source:
        for code_classe in ctx.cache("classes_par_niveau").get(niveau_source, []):
            info = ctx.cache("classe_info")[code_classe]
            for membre in info["apprenants"]:
                viviers.append((membre, info))
    ctx.rng.shuffle(viviers)
    viviers = viviers[: int(cible * 0.85)]

    sequence = 0
    for membre, info in viviers:
        sequence += 1
        code_etablissement = info["etablissement"]
        info_etablissement = ctx.cache("etablissement_info")[code_etablissement]
        candidats.append(
            _candidat(
                ctx,
                id_session=id_session,
                code_examen=code_examen,
                annee=annee,
                sequence=sequence,
                nom=membre["nom"],
                prenoms=membre["prenoms"],
                sexe=membre["sexe"],
                date_naissance=membre["date_naissance"],
                apprenant_id=membre["id"],
                utilisateur_id=membre.get("utilisateur_id"),
                etablissement_id=info_etablissement["id"],
                departement=info_etablissement["departement"],
                commune=info_etablissement["commune"],
                serie=ctx.choix(series) if series else None,
                type_candidature=TypeCandidature.OFFICIEL,
                handicap=membre["handicap"],
                horodatage=horodatage,
            )
        )

    # --- Candidats libres ---
    for _ in range(max(0, cible - len(candidats))):
        sequence += 1
        sexe = ctx.sexe()
        nom, prenoms = ctx.identite(sexe)
        code_departement = ctx.choix([c for c, _, _, _, _ in donnees.DEPARTEMENTS])
        code_commune = ctx.choix(ctx.cache("communes_par_departement")[code_departement])
        candidats.append(
            _candidat(
                ctx,
                id_session=id_session,
                code_examen=code_examen,
                annee=annee,
                sequence=sequence,
                nom=nom,
                prenoms=prenoms,
                sexe=sexe,
                date_naissance=date(
                    annee - ctx.entier(16, 34), ctx.entier(1, 12), ctx.entier(1, 28)
                ),
                apprenant_id=None,
                utilisateur_id=None,
                etablissement_id=None,
                departement=code_departement,
                commune=code_commune,
                serie=ctx.choix(series) if series else None,
                type_candidature=TypeCandidature.LIBRE,
                handicap=None,
                horodatage=horodatage,
            )
        )

    # --- Pièces jointes du dossier ---
    for candidat in candidats:
        pieces = list(PIECES_OBLIGATOIRES)
        if candidat["ligne"]["type_candidature"] == TypeCandidature.LIBRE:
            pieces += list(PIECES_CANDIDAT_LIBRE)
        for code_type in pieces:
            rejetee = candidat["ligne"]["statut_dossier"] == StatutDossier.REJETE and (
                code_type == pieces[0]
            )
            documents.append(
                {
                    "id": ctx.nouvel_id(),
                    "candidat_id": candidat["id"],
                    "type_document_id": ctx.recuperer("type_document", code_type),
                    "nom_fichier": f"{code_type.lower()}-{candidat['numero']}.pdf",
                    "chemin_stockage": (
                        f"candidatures/{code_session}/{candidat['numero']}/{code_type.lower()}.pdf"
                    ),
                    "type_mime": "application/pdf",
                    "taille_octets": ctx.entier(80_000, 1_800_000),
                    "version": 1,
                    "statut": StatutPiece.REJETEE if rejetee else StatutPiece.VALIDEE,
                    "motif_rejet": MotifRejetPiece.ILLISIBLE if rejetee else None,
                    "commentaire": "Document illisible, à fournir de nouveau." if rejetee else None,
                    "verifie_le": horodatage,
                }
            )

    return candidats, documents


def _candidat(
    ctx: ContexteSeed,
    *,
    id_session,
    code_examen: str,
    annee: int,
    sequence: int,
    nom: str,
    prenoms: str,
    sexe: str,
    date_naissance: date,
    apprenant_id,
    utilisateur_id,
    etablissement_id,
    departement: str,
    commune: str,
    serie: str | None,
    type_candidature: TypeCandidature,
    handicap,
    horodatage: datetime,
) -> dict:
    """Construit une candidature et son statut de dossier."""
    ident = ctx.nouvel_id()
    numero = generer_numero_candidat(code_examen, annee, sequence)

    # 4 % des dossiers sont rejetés, 3 % restent incomplets.
    tirage = ctx.rng.random()
    if tirage < 0.04:
        statut = StatutDossier.REJETE
    elif tirage < 0.07:
        statut = StatutDossier.INCOMPLET
    else:
        statut = StatutDossier.VALIDE

    type_handicap = (
        handicap.value if handicap is not None and hasattr(handicap, "value") else "AUCUN"
    )

    return {
        "id": ident,
        "numero": numero,
        "serie": serie,
        "departement": departement,
        "etablissement_id": etablissement_id,
        "apprenant_id": apprenant_id,
        "statut_dossier": statut,
        "ligne": {
            "id": ident,
            "numero_candidat": numero,
            "session_id": id_session,
            "serie_id": ctx.recuperer("serie", serie) if serie else None,
            "apprenant_id": apprenant_id,
            "utilisateur_id": utilisateur_id,
            "etablissement_id": etablissement_id,
            "departement_id": ctx.recuperer("departement", departement),
            "nom": nom,
            "prenoms": prenoms,
            "sexe": sexe,
            "date_naissance": date_naissance,
            "lieu_naissance": _libelle_commune(commune),
            "nationalite": "Béninoise",
            "telephone": ctx.telephone(),
            "type_candidature": type_candidature,
            "statut_dossier": statut,
            "date_soumission": horodatage,
            "date_validation": horodatage if statut == StatutDossier.VALIDE else None,
            "motif_rejet": "Pièces non conformes après relance."
            if statut == StatutDossier.REJETE
            else None,
            "montant_frais": float(ctx.entier(5000, 15000))
            if type_candidature == TypeCandidature.LIBRE
            else 0.0,
            "statut_paiement": "PAID" if type_candidature == TypeCandidature.LIBRE else "PENDING",
            "type_handicap": type_handicap,
            "tiers_temps": type_handicap != "AUCUN",
            "amenagements_demandes": None
            if type_handicap == "AUCUN"
            else "Aménagements conformes au dossier médical.",
        },
    }


def _libelle_commune(code_commune: str) -> str:
    code_departement, index = code_commune.split("-")
    return donnees.COMMUNES[code_departement][int(index) - 1]


# ------------------------------------------------------------------
#  Centres, salles et répartition des candidats
# ------------------------------------------------------------------


def _centres(
    ctx: ContexteSeed, id_session, code_session: str, candidats: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Ouvre un ou plusieurs centres par département, selon le nombre de candidats."""
    par_departement: dict[str, int] = {}
    for candidat in candidats:
        par_departement[candidat["departement"]] = (
            par_departement.get(candidat["departement"], 0) + 1
        )

    centres: list[dict] = []
    salles: list[dict] = []
    numero_centre = 0

    for code_departement, effectif in sorted(par_departement.items()):
        potentiels = (
            ctx.cache("centres_potentiels").get(code_departement)
            or (ctx.cache("communes_par_departement")[code_departement])
        )
        nombre_centres = max(1, min(len(potentiels), effectif // 220 + 1))

        for rang in range(nombre_centres):
            numero_centre += 1
            code_centre = f"{code_session}-C{numero_centre:03d}"
            id_centre = ctx.nouvel_id()

            support = potentiels[rang % len(potentiels)]
            info = ctx.cache("etablissement_info").get(support)
            nom_centre = (
                f"Centre de composition — {info['nom']}"
                if info
                else f"Centre de composition — {code_departement} {rang + 1}"
            )
            chef = _chef_de_centre(ctx, support)

            centre = {
                "id": id_centre,
                "code": code_centre,
                "departement": code_departement,
                "capacite": 0,
                "salles": [],
                "chef": chef,
                "ligne": {
                    "id": id_centre,
                    "session_id": id_session,
                    "etablissement_id": info["id"] if info else None,
                    "departement_id": ctx.recuperer("departement", code_departement),
                    "commune_id": ctx.recuperer("commune", info["commune"]) if info else None,
                    "code": code_centre,
                    "nom": nom_centre,
                    "adresse": info["nom"] if info else nom_centre,
                    "capacite": 0,
                    "nombre_candidats": 0,
                    "nombre_salles": 0,
                    "chef_centre_id": chef["id"] if chef else None,
                    "chef_centre_nom": chef["nom_complet"] if chef else None,
                    "chef_centre_telephone": chef["telephone"] if chef else ctx.telephone(),
                    "accessible_handicap": ctx.probabilite(0.55),
                    "actif": True,
                },
            }
            centres.append(centre)

            # Salles de composition, issues des salles réelles quand elles existent.
            disponibles = ctx.cache("salles_examen").get(support, [])
            nombre_salles = max(3, min(12, effectif // (nombre_centres * 30) + 1))
            for index in range(nombre_salles):
                id_salle = ctx.nouvel_id()
                source = disponibles[index] if index < len(disponibles) else None
                capacite = source[2] if source else ctx.entier(24, 40)
                ligne = {
                    "id": id_salle,
                    "centre_id": id_centre,
                    "salle_id": source[0] if source else None,
                    "code": f"{code_centre}-S{index + 1:02d}",
                    "nom": source[1] if source else f"Salle {index + 1}",
                    "batiment": source[3] if source else "Bâtiment principal",
                    "capacite": capacite,
                    "nombre_candidats": 0,
                    "accessible_handicap": index == 0,
                    "salle_amenagee": index == 0,
                }
                salle = {
                    "id": id_salle,
                    "centre": centre,
                    "capacite": capacite,
                    "occupes": 0,
                    "amenagee": index == 0,
                    "ligne": ligne,
                }
                salles.append(salle)
                centre["salles"].append(salle)
                centre["capacite"] += capacite

            centre["ligne"]["capacite"] = centre["capacite"]
            centre["ligne"]["nombre_salles"] = len(centre["salles"])

    return centres, salles


def _chef_de_centre(ctx: ContexteSeed, code_etablissement: str | None) -> dict | None:
    enseignants = ctx.cache("enseignants_par_etablissement").get(code_etablissement or "", [])
    return ctx.choix(enseignants) if enseignants else None


def _repartir(
    ctx: ContexteSeed, candidats: list[dict], centres: list[dict], salles: list[dict]
) -> None:
    """Affecte chaque candidat retenu à un centre, une salle et une place.

    Les candidats bénéficiant d'aménagements sont orientés en priorité vers la
    salle aménagée de leur centre.
    """
    salles_par_departement: dict[str, list[dict]] = {}
    for salle in salles:
        salles_par_departement.setdefault(salle["centre"]["departement"], []).append(salle)

    compteurs: dict[str, int] = {}

    for candidat in candidats:
        if candidat["statut_dossier"] == StatutDossier.REJETE:
            continue

        disponibles = salles_par_departement.get(candidat["departement"]) or salles
        amenagement_requis = candidat["ligne"]["type_handicap"] != "AUCUN"

        cible = next(
            (
                s
                for s in disponibles
                if s["amenagee"] and s["occupes"] < s["capacite"] and amenagement_requis
            ),
            None,
        ) or next((s for s in disponibles if s["occupes"] < s["capacite"]), None)

        if cible is None:
            cible = disponibles[-1]

        cible["occupes"] += 1
        centre = cible["centre"]
        place = cible["occupes"]

        compteurs[centre["code"]] = compteurs.get(centre["code"], 0) + 1
        numero_table = generer_numero_table(
            centre["code"].rsplit("-", 1)[-1], compteurs[centre["code"]]
        )

        candidat["ligne"].update(
            {
                "centre_id": centre["id"],
                "salle_composition_id": cible["id"],
                "numero_place": place,
                "numero_table": numero_table,
                "statut_dossier": StatutDossier.CONVOQUE,
            }
        )
        candidat["statut_dossier"] = StatutDossier.CONVOQUE
        candidat["centre"] = centre
        candidat["salle"] = cible
        candidat["numero_table"] = numero_table
        candidat["place"] = place

    for salle in salles:
        salle["ligne"]["nombre_candidats"] = salle["occupes"]
        salle["ligne"]["place_debut"] = 1 if salle["occupes"] else None
        salle["ligne"]["place_fin"] = salle["occupes"] or None

    for centre in centres:
        centre["ligne"]["nombre_candidats"] = sum(s["occupes"] for s in centre["salles"])


# ------------------------------------------------------------------
#  Surveillance et correction
# ------------------------------------------------------------------


def _surveillance(
    ctx: ContexteSeed, id_session, centres: list[dict], salles: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Propositions des établissements puis affectations retenues."""
    propositions: list[dict] = []
    affectations: list[dict] = []
    horodatage = datetime.now(UTC)

    for centre in centres:
        chef = centre["chef"]
        if chef:
            affectations.append(
                _affectation(
                    ctx, id_session, centre, None, chef, RoleSurveillance.CHEF_CENTRE, 45_000
                )
            )

        viviers = [
            enseignant
            for code_etablissement in ctx.cache("centres_potentiels").get(centre["departement"], [])
            for enseignant in ctx.cache("enseignants_par_etablissement").get(code_etablissement, [])
        ] or [
            enseignant
            for liste in ctx.cache("enseignants_par_etablissement").values()
            for enseignant in liste
        ]
        if not viviers:
            continue

        for salle in centre["salles"]:
            for _ in range(2):
                enseignant = ctx.choix(viviers)
                affectations.append(
                    _affectation(
                        ctx,
                        id_session,
                        centre,
                        salle,
                        enseignant,
                        RoleSurveillance.SURVEILLANT,
                        18_000,
                    )
                )

        for role, indemnite in (
            (RoleSurveillance.SECRETAIRE, 25_000),
            (RoleSurveillance.OPERATEUR_SAISIE, 22_000),
            (RoleSurveillance.SECURITE, 15_000),
            (RoleSurveillance.SANTE, 20_000),
        ):
            enseignant = ctx.choix(viviers)
            affectations.append(
                _affectation(ctx, id_session, centre, None, enseignant, role, indemnite)
            )

    # Chaque affectation résulte d'une proposition d'établissement.
    for affectation in affectations:
        agent = affectation["agent"]
        propositions.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "etablissement_id": affectation["etablissement_id"],
                "enseignant_id": agent["id"],
                "role_propose": affectation["ligne"]["role"],
                "nom_complet": agent["nom_complet"],
                "telephone": agent.get("telephone"),
                "statut": StatutProposition.RETENUE,
                "decide_le": horodatage,
            }
        )

    return propositions, affectations


def _affectation(ctx, id_session, centre, salle, agent, role, indemnite) -> dict:
    ident = ctx.nouvel_id()
    etablissement_code = next(
        (
            code
            for code, liste in ctx.cache("enseignants_par_etablissement").items()
            if any(e["id"] == agent["id"] for e in liste)
        ),
        None,
    )
    etablissement_id = (
        ctx.cache("etablissement_info")[etablissement_code]["id"] if etablissement_code else None
    )
    return {
        "id": ident,
        "agent": agent,
        "etablissement_id": etablissement_id,
        "centre": centre,
        "ligne": {
            "id": ident,
            "session_id": id_session,
            "centre_id": centre["id"],
            "salle_composition_id": salle["id"] if salle else None,
            "enseignant_id": agent["id"],
            "role": role,
            "nom_complet": agent["nom_complet"],
            "telephone": agent.get("telephone"),
            "heure_prise_service": time(7, 0),
            "indemnite": float(indemnite),
            "present": True,
            "responsabilites": f"Mission de {role.value.lower().replace('_', ' ')}.",
        },
    }


def _correcteurs(
    ctx: ContexteSeed, id_session, code_session: str, epreuves: list[dict]
) -> list[dict]:
    """Constitue le pool de correcteurs, un chef par épreuve."""
    correcteurs: list[dict] = []
    numero = 0

    for epreuve in epreuves:
        vivier = ctx.cache("enseignants_par_matiere").get(epreuve["matiere"], [])
        pool = ctx.echantillon(vivier, 3) if vivier else []
        for rang, enseignant_id in enumerate(pool):
            numero += 1
            ident = ctx.nouvel_id()
            nom_complet = _nom_enseignant(ctx, enseignant_id)
            correcteur = {
                "id": ident,
                "epreuve": epreuve,
                "copies": [],
                "ligne": {
                    "id": ident,
                    "session_id": id_session,
                    "epreuve_id": epreuve["id"],
                    "enseignant_id": enseignant_id,
                    "matiere_id": ctx.recuperer("matiere", epreuve["matiere"]),
                    "serie_id": ctx.recuperer("serie", epreuve["serie"])
                    if epreuve["serie"]
                    else None,
                    "code_correcteur": f"C{numero:05d}",
                    "nom_complet": nom_complet,
                    "telephone": ctx.telephone(),
                    "est_chef_correcteur": rang == 0,
                    "copies_attribuees": 0,
                    "copies_corrigees": 0,
                    "indemnite": 0.0,
                    "actif": True,
                },
            }
            correcteurs.append(correcteur)
            epreuve.setdefault("correcteurs", []).append(correcteur)

    return correcteurs


def _nom_enseignant(ctx: ContexteSeed, enseignant_id) -> str:
    for liste in ctx.cache("enseignants_par_etablissement").values():
        for enseignant in liste:
            if enseignant["id"] == enseignant_id:
                return enseignant["nom_complet"]
    return "Correcteur désigné"


# ------------------------------------------------------------------
#  Composition, correction et saisie des notes
# ------------------------------------------------------------------


def _composition(
    ctx: ContexteSeed,
    id_session,
    candidats: list[dict],
    epreuves: list[dict],
    correcteurs: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Produit les copies anonymées, leur correction et les notes définitives."""
    copies: list[dict] = []
    notes: list[dict] = []
    horodatage = datetime.now(UTC)

    epreuves_par_serie: dict[str | None, list[dict]] = {}
    for epreuve in epreuves:
        epreuves_par_serie.setdefault(epreuve["serie"], []).append(epreuve)

    for candidat in candidats:
        if candidat["statut_dossier"] != StatutDossier.CONVOQUE:
            continue

        applicables = epreuves_par_serie.get(candidat["serie"]) or epreuves_par_serie.get(None, [])
        if not applicables:
            continue

        # Absentéisme : 3 % des candidats convoqués ne composent pas.
        absent_total = ctx.probabilite(0.03)
        aptitude = ctx.rng.gauss(10.6, 2.9)
        candidat["notes"] = []

        for epreuve in applicables:
            id_copie = ctx.nouvel_id()
            correcteur = ctx.choix(epreuve["correcteurs"]) if epreuve.get("correcteurs") else None

            if absent_total or ctx.probabilite(0.01):
                statut = StatutNoteExamen.ABSENT
                valeur = None
            elif ctx.probabilite(0.003):
                statut = StatutNoteExamen.FRAUDE
                valeur = 0.0
            else:
                statut = StatutNoteExamen.SAISIE
                valeur = round(max(0.0, min(20.0, aptitude + ctx.rng.gauss(0, 2.4))) * 4) / 4

            note_seconde = None
            double = ctx.probabilite(0.12) and valeur is not None
            if double:
                note_seconde = round(max(0.0, min(20.0, valeur + ctx.rng.gauss(0, 1.1))) * 4) / 4
            note_finale = (
                round((valeur + note_seconde) / 2, 2) if note_seconde is not None else valeur
            )

            copies.append(
                {
                    "id": id_copie,
                    "session_id": id_session,
                    "epreuve_id": epreuve["id"],
                    "candidat_id": candidat["id"],
                    "correcteur_id": correcteur["id"] if correcteur else None,
                    "code_anonymat": generer_code_anonymat(),
                    "lot": f"L{ctx.entier(1, 40):03d}",
                    "nombre_feuillets": ctx.entier(1, 4),
                    "note_correcteur": valeur,
                    "note_second_correcteur": note_seconde,
                    "note_finale": note_finale,
                    "double_correction": double,
                    "ecart_significatif": bool(
                        note_seconde is not None and abs(note_seconde - valeur) >= 3
                    ),
                    "corrigee": statut is not StatutNoteExamen.ABSENT,
                    "corrigee_le": horodatage if statut is not StatutNoteExamen.ABSENT else None,
                    "validee": True,
                }
            )
            if correcteur:
                correcteur["ligne"]["copies_attribuees"] += 1
                if statut is not StatutNoteExamen.ABSENT:
                    correcteur["ligne"]["copies_corrigees"] += 1
                correcteur["ligne"]["indemnite"] += 350.0

            if note_finale is not None and note_finale <= 2 and epreuve["coefficient"] >= 4:
                statut = StatutNoteExamen.NOTE_ELIMINATOIRE

            notes.append(
                {
                    "id": ctx.nouvel_id(),
                    "session_id": id_session,
                    "candidat_id": candidat["id"],
                    "epreuve_id": epreuve["id"],
                    "copie_id": id_copie,
                    "valeur": note_finale,
                    "valeur_sur_20": note_finale,
                    "coefficient": epreuve["coefficient"],
                    "points": None
                    if note_finale is None
                    else round(note_finale * epreuve["coefficient"], 2),
                    "statut": statut,
                    "validee": True,
                    "modifiee_apres_contentieux": False,
                }
            )
            candidat["notes"].append(
                {
                    "epreuve": epreuve,
                    "valeur": note_finale,
                    "statut": statut,
                    "coefficient": epreuve["coefficient"],
                }
            )

        candidat["statut_dossier"] = StatutDossier.CORRIGE
        candidat["ligne"]["statut_dossier"] = StatutDossier.CORRIGE

    return copies, notes


# ------------------------------------------------------------------
#  Jurys, délibération et résultats
# ------------------------------------------------------------------


def _deliberation(
    ctx: ContexteSeed,
    id_session,
    code_session: str,
    nom_examen: str,
    candidats: list[dict],
    notes: list[dict],
    epreuves: list[dict],
    centres: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Calcule les moyennes, applique les règles d'admission et arrête les résultats."""
    jurys: list[dict] = []
    membres: list[dict] = []
    resultats: list[dict] = []
    horodatage = datetime.now(UTC)

    # Un jury par centre.
    jury_par_centre: dict = {}
    for rang, centre in enumerate(centres, start=1):
        id_jury = ctx.nouvel_id()
        jury_par_centre[centre["id"]] = id_jury
        president = centre["chef"]
        jurys.append(
            {
                "id": id_jury,
                "session_id": id_session,
                "centre_id": centre["id"],
                "code": f"{code_session}-J{rang:03d}",
                "libelle": f"Jury de délibération — {centre['ligne']['nom']}",
                "president_nom": president["nom_complet"] if president else "Président désigné",
                "president_enseignant_id": president["id"] if president else None,
                "date_deliberation": date.today(),
                "lieu": centre["ligne"]["nom"],
                "nombre_candidats": centre["ligne"]["nombre_candidats"],
                "nombre_admis": 0,
                "cloture": True,
            }
        )
        for index in range(4):
            enseignant = _membre_jury(ctx, centre)
            membres.append(
                {
                    "id": ctx.nouvel_id(),
                    "jury_id": id_jury,
                    "enseignant_id": enseignant["id"] if enseignant else None,
                    "nom_complet": enseignant["nom_complet"]
                    if enseignant
                    else f"Membre {index + 1}",
                    "qualite": ctx.choix(
                        ["Enseignant titulaire", "Inspecteur", "Conseiller pédagogique"]
                    ),
                    "est_president": False,
                    "est_rapporteur": index == 0,
                    "present": True,
                    "indemnite": 30_000.0,
                }
            )

    # Moyennes et décisions.
    moyennes_nationales: dict[str, float | None] = {}
    par_departement: dict[str, dict[str, float | None]] = {}
    par_etablissement: dict[str, dict[str, float | None]] = {}

    for candidat in candidats:
        if candidat["statut_dossier"] != StatutDossier.CORRIGE:
            continue

        lignes = candidat.get("notes", [])
        elements = [
            ElementNote(ligne["valeur"], ligne["coefficient"])
            for ligne in lignes
            if ligne["valeur"] is not None
        ]
        absent = not elements
        moyenne = moyenne_ponderee(elements)
        points, coefficients = totaux_ponderes(elements)
        eliminatoire = any(
            ligne["statut"] is StatutNoteExamen.NOTE_ELIMINATOIRE for ligne in lignes
        )
        fraude = any(ligne["statut"] is StatutNoteExamen.FRAUDE for ligne in lignes)

        # Repêchage du jury : jusqu'à 0,5 point pour les candidats proches du seuil.
        points_jury = 0.0
        if moyenne is not None and 9.4 <= moyenne < 10 and not eliminatoire:
            points_jury = round(ctx.rng.uniform(0.1, 0.6), 2)

        moyenne_finale = None if moyenne is None else round(moyenne + points_jury, 2)

        if fraude:
            decision = DecisionExamen.EXCLU
        elif absent:
            decision = DecisionExamen.ABSENT
        elif eliminatoire:
            decision = DecisionExamen.NON_ADMIS
        elif moyenne_finale is not None and moyenne_finale >= 10:
            decision = DecisionExamen.ADMIS
        else:
            decision = DecisionExamen.NON_ADMIS

        candidat["moyenne"] = moyenne_finale
        candidat["decision"] = decision
        candidat["statut_dossier"] = (
            StatutDossier.ADMIS if decision is DecisionExamen.ADMIS else StatutDossier.NON_ADMIS
        )
        candidat["ligne"]["statut_dossier"] = candidat["statut_dossier"]

        moyennes_nationales[str(candidat["id"])] = moyenne_finale
        par_departement.setdefault(candidat["departement"], {})[str(candidat["id"])] = (
            moyenne_finale
        )
        if candidat["etablissement_id"]:
            par_etablissement.setdefault(str(candidat["etablissement_id"]), {})[
                str(candidat["id"])
            ] = moyenne_finale

        centre = candidat.get("centre")
        resultats.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "candidat_id": candidat["id"],
                "jury_id": jury_par_centre.get(centre["id"]) if centre else None,
                "serie_id": ctx.recuperer("serie", candidat["serie"])
                if candidat["serie"]
                else None,
                "etablissement_id": candidat["etablissement_id"],
                "departement_id": ctx.recuperer("departement", candidat["departement"]),
                "total_points": points,
                "total_coefficients": coefficients,
                "moyenne": moyenne_finale,
                "mention": determiner_mention(moyenne_finale)
                if decision is DecisionExamen.ADMIS
                else None,
                "decision": decision,
                "repeche": points_jury > 0,
                "points_jury": points_jury,
                "motivation_jury": "Repêchage accordé par le jury." if points_jury else None,
                "publie": True,
                "publie_le": horodatage,
                "code_verification": generer_code_verification(),
                "_candidat": candidat,
            }
        )

    # Rangs national, départemental et par établissement.
    rangs_nationaux = calculer_rangs(moyennes_nationales)
    rangs_departementaux = {
        cle: rang
        for departement, valeurs in par_departement.items()
        for cle, rang in calculer_rangs(valeurs).items()
    }
    rangs_etablissement = {
        cle: rang
        for etablissement, valeurs in par_etablissement.items()
        for cle, rang in calculer_rangs(valeurs).items()
    }

    admis_par_jury: dict = {}
    for resultat in resultats:
        cle = str(resultat["candidat_id"])
        resultat["rang_national"] = rangs_nationaux.get(cle)
        resultat["rang_departemental"] = rangs_departementaux.get(cle)
        resultat["rang_etablissement"] = rangs_etablissement.get(cle)
        if resultat["decision"] is DecisionExamen.ADMIS and resultat["jury_id"]:
            admis_par_jury[resultat["jury_id"]] = admis_par_jury.get(resultat["jury_id"], 0) + 1
        resultat.pop("_candidat", None)

    for jury in jurys:
        jury["nombre_admis"] = admis_par_jury.get(jury["id"], 0)

    return jurys, membres, resultats


def _membre_jury(ctx: ContexteSeed, centre: dict) -> dict | None:
    viviers = [
        enseignant
        for code in ctx.cache("centres_potentiels").get(centre["departement"], [])
        for enseignant in ctx.cache("enseignants_par_etablissement").get(code, [])
    ]
    return ctx.choix(viviers) if viviers else None


# ------------------------------------------------------------------
#  Convocations, incidents, contentieux, budget, archives, diplômes
# ------------------------------------------------------------------


def _convocations(
    ctx: ContexteSeed,
    id_session,
    code_session: str,
    candidats: list[dict],
    affectations: list[dict],
) -> list[dict]:
    """Émet les convocations des candidats et des agents d'examen."""
    convocations: list[dict] = []

    for candidat in candidats:
        centre = candidat.get("centre")
        if centre is None:
            continue
        convocations.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "type_convocation": TypeConvocation.CANDIDAT,
                "candidat_id": candidat["id"],
                "numero": f"CONV-{candidat['numero']}",
                "destinataire": f"{candidat['ligne']['prenoms']} {candidat['ligne']['nom']}",
                "centre_nom": centre["ligne"]["nom"],
                "salle_nom": candidat["salle"]["ligne"]["nom"],
                "numero_place": candidat.get("place"),
                "date_convocation": date.today(),
                "heure_convocation": time(7, 0),
                "consignes": (
                    "Se présenter une heure avant le début de la première épreuve, "
                    "muni de cette convocation et d'une pièce d'identité."
                ),
                "code_verification": generer_code_verification(),
                "imprimee": True,
            }
        )

    types_agents = {
        RoleSurveillance.CHEF_CENTRE: TypeConvocation.CHEF_CENTRE,
        RoleSurveillance.SURVEILLANT: TypeConvocation.SURVEILLANT,
        RoleSurveillance.OPERATEUR_SAISIE: TypeConvocation.OPERATEUR_SAISIE,
    }
    for rang, affectation in enumerate(affectations, start=1):
        type_convocation = types_agents.get(affectation["ligne"]["role"])
        if type_convocation is None:
            continue
        convocations.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "type_convocation": type_convocation,
                "affectation_id": affectation["id"],
                "numero": f"CONV-AG-{code_session}-{rang:06d}",
                "destinataire": affectation["ligne"]["nom_complet"],
                "centre_nom": affectation["centre"]["ligne"]["nom"],
                "salle_nom": None,
                "date_convocation": date.today(),
                "heure_convocation": time(6, 30),
                "consignes": "Prise de service obligatoire la veille des épreuves.",
                "code_verification": generer_code_verification(),
                "imprimee": True,
            }
        )

    return convocations


def _incidents(
    ctx: ContexteSeed, id_session, centres: list[dict], candidats: list[dict], epreuves: list[dict]
) -> list[dict]:
    """Quelques incidents de salle, pour alimenter les rapports de centre."""
    categories = (
        ("Retard de candidat", "FAIBLE"),
        ("Tentative de fraude", "GRAVE"),
        ("Malaise de candidat", "MOYENNE"),
        ("Erreur sur le sujet distribué", "GRAVE"),
        ("Coupure d'électricité", "MOYENNE"),
    )
    incidents = []
    convoques = [c for c in candidats if c.get("centre")]

    for centre in centres:
        if not ctx.probabilite(0.35):
            continue
        categorie, gravite = ctx.choix(categories)
        candidat = ctx.choix(convoques) if convoques else None
        incidents.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "centre_id": centre["id"],
                "candidat_id": candidat["id"] if candidat else None,
                "epreuve_id": ctx.choix(epreuves)["id"] if epreuves else None,
                "reference": generer_reference("INC"),
                "categorie": categorie,
                "gravite": gravite,
                "description": f"{categorie} constaté au centre {centre['ligne']['nom']}.",
                "date_incident": datetime.now(UTC),
                "declare_par": centre["ligne"]["chef_centre_nom"],
                "mesures_prises": "Procès-verbal établi et transmis à la direction des examens.",
                "clos": ctx.probabilite(0.7),
            }
        )
    return incidents


def _contentieux(
    ctx: ContexteSeed,
    id_session,
    candidats: list[dict],
    resultats: list[dict],
    epreuves: list[dict],
) -> list[dict]:
    """Réclamations des candidats non admis et leur instruction."""
    non_admis = [r for r in resultats if r["decision"] is DecisionExamen.NON_ADMIS and r["moyenne"]]
    candidats_par_id = {c["id"]: c for c in candidats}
    lignes = []

    for rang, resultat in enumerate(ctx.echantillon(non_admis, max(1, len(non_admis) // 25)), 1):
        candidat = candidats_par_id.get(resultat["candidat_id"])
        if candidat is None:
            continue

        type_contentieux = ctx.choix(list(TypeContentieux))
        favorable = ctx.probabilite(0.28)
        note_avant = resultat["moyenne"]
        note_apres = round(note_avant + ctx.rng.uniform(0.2, 1.4), 2) if favorable else None

        lignes.append(
            {
                "id": ctx.nouvel_id(),
                "session_id": id_session,
                "candidat_id": candidat["id"],
                "epreuve_id": ctx.choix(epreuves)["id"] if epreuves else None,
                "numero": f"CONT-{candidat['numero']}-{rang:03d}",
                "type_contentieux": type_contentieux,
                "objet": f"Réclamation relative à : {type_contentieux.value.lower()}",
                "expose": (
                    "Le candidat conteste le résultat proclamé et sollicite "
                    "la vérification de ses copies et le recalcul de sa moyenne."
                ),
                "statut": StatutContentieux.TRANCHEE_FAVORABLE
                if favorable
                else StatutContentieux.TRANCHEE_DEFAVORABLE,
                "date_depot": date.today(),
                "date_recevabilite": date.today(),
                "date_instruction": date.today(),
                "date_decision": date.today(),
                "instructeur_nom": "Commission des contentieux",
                "conclusion": "Recalcul effectué, décision révisée."
                if favorable
                else "Aucune erreur constatée, décision confirmée.",
                "note_avant": note_avant,
                "note_apres": note_apres,
                "decision_revisee": DecisionExamen.ADMIS
                if favorable and note_apres and note_apres >= 10
                else None,
                "frais_dossier": 2000.0,
                "notifie_le": datetime.now(UTC),
            }
        )
    return lignes


def _budget(
    ctx: ContexteSeed, id_session, code_session: str, candidats: list[dict], centres: list[dict]
) -> tuple[dict, list[dict], list[dict]]:
    """Budget de la session, ventilé par ligne, avec quelques dépenses justifiées."""
    id_budget = ctx.nouvel_id()
    montant_total = float(len(candidats) * ctx.entier(3500, 6500))
    recettes = float(
        sum(c["ligne"]["montant_frais"] for c in candidats if c["ligne"]["montant_frais"])
    )

    lignes, depenses = [], []
    engage_total = 0.0
    paye_total = 0.0

    for code, libelle, categorie, part in LIGNES_BUDGET:
        id_ligne = ctx.nouvel_id()
        prevu = round(montant_total * part, 2)
        engage = round(prevu * ctx.rng.uniform(0.75, 1.0), 2)
        paye = round(engage * ctx.rng.uniform(0.6, 1.0), 2)
        engage_total += engage
        paye_total += paye

        lignes.append(
            {
                "id": id_ligne,
                "budget_id": id_budget,
                "code": f"{code_session}-{code}",
                "libelle": libelle,
                "categorie": categorie,
                "montant_prevu": prevu,
                "montant_engage": engage,
                "montant_paye": paye,
            }
        )

        for centre in ctx.echantillon(centres, min(3, len(centres))):
            depenses.append(
                {
                    "id": ctx.nouvel_id(),
                    "ligne_id": id_ligne,
                    "centre_id": centre["id"],
                    "reference": generer_reference("DEP"),
                    "objet": f"{libelle} — {centre['ligne']['nom']}",
                    "beneficiaire": centre["ligne"]["chef_centre_nom"],
                    "fournisseur": None if categorie == "PERSONNEL" else "Fournisseur agréé",
                    "montant": round(paye / max(1, len(centres)), 2),
                    "date_depense": date.today(),
                    "statut_paiement": "PAID",
                }
            )

    budget = {
        "id": id_budget,
        "session_id": id_session,
        "code": f"BUD-{code_session}",
        "libelle": f"Budget de la session {code_session}",
        "montant_prevu": montant_total,
        "montant_engage": round(engage_total, 2),
        "montant_paye": round(paye_total, 2),
        "recettes_inscriptions": recettes,
        "devise": "XOF",
        "valide": True,
        "exercice": date.today().year,
    }
    return budget, lignes, depenses


def _archives(
    ctx: ContexteSeed, id_session, code_examen: str, sigle: str, annee: int, epreuves: list[dict]
) -> list[dict]:
    """Archive les sujets de la session et de quelques sessions antérieures."""
    lignes = []
    id_examen = ctx.recuperer("examen", code_examen)

    for decalage in range(0, 4):
        annee_archive = annee - decalage
        for epreuve in epreuves:
            libelle_matiere = next(
                (libelle for code, libelle, *_ in scolaire.MATIERES if code == epreuve["matiere"]),
                epreuve["matiere"],
            )
            lignes.append(
                {
                    "id": ctx.nouvel_id(),
                    "reference": f"ARCH-{sigle}-{annee_archive}-{epreuve['matiere']}"
                    f"-{epreuve['serie'] or 'GEN'}-{ctx.suivant('archive'):05d}",
                    "titre": f"{sigle} {annee_archive} — {libelle_matiere}"
                    + (f" (série {epreuve['serie']})" if epreuve["serie"] else ""),
                    "examen_id": id_examen,
                    "session_id": id_session if decalage == 0 else None,
                    "matiere_id": ctx.recuperer("matiere", epreuve["matiere"]),
                    "serie_id": ctx.recuperer("serie", epreuve["serie"])
                    if epreuve["serie"]
                    else None,
                    "niveau_id": ctx.recuperer(
                        "niveau", ctx.cache("niveau_source_examen").get(code_examen, "")
                    ),
                    "nature": NatureExamen.EXAMEN
                    if not code_examen.startswith("CONC")
                    else NatureExamen.CONCOURS,
                    "annee": annee_archive,
                    "duree_minutes": epreuve["ligne"]["duree_minutes"],
                    "bareme": 20.0,
                    "coefficient": epreuve["coefficient"],
                    "sujet_url": f"archives/{sigle}/{annee_archive}/{epreuve['matiere']}-sujet.pdf",
                    "corrige_url": f"archives/{sigle}/{annee_archive}/"
                    f"{epreuve['matiere']}-corrige.pdf",
                    "mots_cles": f"{sigle},{epreuve['matiere']},{annee_archive}",
                    "nombre_telechargements": ctx.entier(0, 4200),
                    "public": True,
                }
            )
    return lignes


def _diplomes(
    ctx: ContexteSeed,
    id_session,
    sigle: str,
    annee: int,
    candidats: list[dict],
    resultats: list[dict],
) -> list[dict]:
    """Délivre un diplôme à chaque lauréat."""
    candidats_par_id = {c["id"]: c for c in candidats}
    diplomes = []
    sequence = 0

    for resultat in resultats:
        if resultat["decision"] is not DecisionExamen.ADMIS:
            continue
        candidat = candidats_par_id.get(resultat["candidat_id"])
        if candidat is None:
            continue

        sequence += 1
        ligne = candidat["ligne"]
        diplomes.append(
            {
                "id": ctx.nouvel_id(),
                "numero": generer_numero_diplome(sigle, annee, sequence),
                "code_verification": generer_code_verification(),
                "apprenant_id": candidat["apprenant_id"],
                "candidat_id": candidat["id"],
                "session_id": id_session,
                "diplome_ref_id": ctx.recuperer("diplome", sigle),
                "etablissement_id": candidat["etablissement_id"],
                "titulaire_nom": f"{ligne['prenoms']} {ligne['nom']}",
                "titulaire_date_naissance": ligne["date_naissance"],
                "titulaire_lieu_naissance": ligne["lieu_naissance"],
                "intitule": f"Diplôme du {sigle}",
                "serie_libelle": candidat["serie"],
                "session_libelle": f"Session normale {annee}",
                "annee": annee,
                "moyenne": resultat["moyenne"],
                "mention": resultat["mention"],
                "statut": StatutDiplome.EMIS,
                "date_delivrance": date(annee, 9, 1),
                "signataire": "Le Directeur des examens et concours",
                "qualite_signataire": "Directeur",
                "nombre_verifications": ctx.entier(0, 12),
            }
        )
    return diplomes
