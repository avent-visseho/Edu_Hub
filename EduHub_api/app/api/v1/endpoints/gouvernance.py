"""Gouvernance : tableaux de bord, recherche avancée, cartographie, alertes."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, or_, select

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.enums import Action
from app.engines import ai
from app.engines.analytics import (
    distribution_moyennes,
    effectifs_par_departement,
    resultats_par_departement,
    tableau_bord_national,
)
from app.engines.audit import journaliser
from app.engines.espace_personnel import (
    evolution_moyennes,
    indicateurs_eleve,
    indicateurs_enseignant,
    indicateurs_etablissement,
    indicateurs_parent,
    moyennes_par_classe,
    repartition_par_niveau,
)
from app.engines.portee import Portee, resoudre_perimetre
from app.engines.reporting import BlocTableau, EnTeteDocument, exporter_csv, generer_document
from app.engines.search import Conjonction, Critere, DescripteurChamp, Operateur
from app.models.apprenant import Apprenant
from app.models.diplome import DiplomeDelivre
from app.models.etablissement import Etablissement
from app.models.examen import Examen, SessionExamen
from app.models.personnel import Enseignant
from app.models.projet import Projet
from app.models.scolarite import AnneeAcademique, Classe
from app.models.systeme import (
    Alerte,
    IndicateurStatistique,
    JournalAudit,
    Rapport,
    RegleMetier,
    RequeteEnregistree,
)
from app.schemas.analytics import (
    AlerteLecture,
    DemandeRapport,
    IndicateurReponse,
    QuestionNaturelle,
    RechercheGlobaleResultat,
    RegleMetierEcriture,
    RegleMetierLecture,
    ReponseNaturelle,
    RequeteAvancee,
    RequeteEnregistreeEcriture,
    RequeteEnregistreeLecture,
    ResultatRecherche,
    SyntheseTerritoriale,
    TableauBord,
)
from app.services import recherche as service_recherche
from app.utils.codes import generer_reference

router = APIRouter()

#: Matières les plus utilisées dans les requêtes « moyenne en <matière> ».
MATIERES_CALCULEES = ("MATH", "FRA", "ANG", "SVT", "PC", "HG", "PHILO")


#: Libellés des champs calculés propres à certaines entités.
LIBELLES_CALCULES: dict[str, str] = {
    "taux_reussite": "Taux de réussite aux examens (%)",
    "moyenne_examen": "Moyenne obtenue aux examens",
    "nombre_salles": "Nombre de salles",
    "nombre_classes": "Nombre de classes",
}


def _champs_calcules(entite) -> list[dict]:
    """Variables dérivées, calculées à la volée par le moteur de recherche."""
    operateurs = ["eq", "ne", "gt", "gte", "lt", "lte", "between"]

    propres = service_recherche.CHAMPS_CALCULES_PAR_ENTITE.get(entite.cle, set())
    if propres:
        return [
            {
                "cle": cle,
                "libelle": LIBELLES_CALCULES.get(cle, cle),
                "type": "nombre",
                "choix": [],
                "operateurs": operateurs,
                "calcule": True,
            }
            for cle in sorted(propres)
        ]

    if entite.cle not in service_recherche.CLE_APPRENANT:
        return []

    champs = [
        {
            "cle": "moyenne_generale",
            "libelle": "Moyenne générale",
            "type": "nombre",
            "choix": [],
            "operateurs": operateurs,
            "calcule": True,
        },
        {
            "cle": "taux_absence",
            "libelle": "Taux d'absence (%)",
            "type": "nombre",
            "choix": [],
            "operateurs": operateurs,
            "calcule": True,
        },
        {
            "cle": "taux_presence",
            "libelle": "Taux de présence (%)",
            "type": "nombre",
            "choix": [],
            "operateurs": operateurs,
            "calcule": True,
        },
    ]
    champs += [
        {
            "cle": f"moyenne_matiere:{code}",
            "libelle": f"Moyenne en {code}",
            "type": "nombre",
            "choix": [],
            "operateurs": operateurs,
            "calcule": True,
        }
        for code in MATIERES_CALCULEES
    ]
    return champs


# ------------------------------------------------------------------
#  Tableaux de bord
# ------------------------------------------------------------------


@router.get(
    "/tableaux-de-bord/national",
    response_model=TableauBord,
    tags=["Gouvernance"],
    summary="Tableau de bord national",
    description="Chiffres clés du système éducatif et graphiques de pilotage.",
)
async def tableau_national(
    session: SessionDep,
    contexte: ContexteDep,
    annee_id: Annotated[uuid.UUID | None, Query()] = None,
) -> TableauBord:
    contexte.exiger("analytics", Action.READ)

    indicateurs = await tableau_bord_national(session, annee_id)
    territoires = await effectifs_par_departement(session, annee_id)
    distribution = await distribution_moyennes(session)

    stmt = (
        select(SessionExamen.libelle, SessionExamen.taux_reussite, SessionExamen.annee)
        .where(SessionExamen.taux_reussite.isnot(None))
        .order_by(SessionExamen.annee.desc())
        .limit(12)
    )
    reussite = [
        {"session": libelle, "annee": annee, "taux_reussite": taux}
        for libelle, taux, annee in (await session.execute(stmt)).all()
    ]

    stmt = (
        select(Apprenant.sexe, func.count())
        .where(Apprenant.supprime.is_(False))
        .group_by(Apprenant.sexe)
    )
    parite = [
        {"categorie": sexe.value, "effectif": total}
        for sexe, total in (await session.execute(stmt)).all()
    ]

    stmt = (
        select(Apprenant.type_handicap, func.count())
        .where(Apprenant.supprime.is_(False), Apprenant.type_handicap != "AUCUN")
        .group_by(Apprenant.type_handicap)
    )
    inclusion = [
        {"categorie": handicap.value, "effectif": total}
        for handicap, total in (await session.execute(stmt)).all()
    ]

    alertes = list(
        (
            await session.execute(
                select(Alerte)
                .where(Alerte.traitee.is_(False))
                .order_by(Alerte.niveau.desc())
                .limit(10)
            )
        ).scalars()
    )

    return TableauBord(
        perimetre="NATIONAL",
        perimetre_libelle="République du Bénin",
        indicateurs=[IndicateurReponse(**indicateur.en_dict()) for indicateur in indicateurs],
        graphiques={
            "effectifs_par_departement": territoires,
            "distribution_moyennes": distribution,
            "taux_reussite_sessions": reussite,
            "parite": parite,
            "inclusion": inclusion,
        },
        alertes=[
            {
                "id": str(alerte.id),
                "titre": alerte.titre,
                "niveau": alerte.niveau.value,
                "domaine": alerte.domaine,
                "message": alerte.message,
            }
            for alerte in alertes
        ],
    )


@router.get(
    "/tableaux-de-bord/territoires",
    response_model=list[SyntheseTerritoriale],
    tags=["Gouvernance"],
    summary="Synthèse par département",
)
async def synthese_territoriale(
    session: SessionDep,
    contexte: ContexteDep,
    session_examen_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[SyntheseTerritoriale]:
    contexte.exiger("analytics", Action.READ)

    effectifs = {ligne["code"]: ligne for ligne in await effectifs_par_departement(session)}
    resultats = (
        {
            ligne["code"]: ligne
            for ligne in await resultats_par_departement(session, session_examen_id)
        }
        if session_examen_id
        else {}
    )

    syntheses = []
    for code, ligne in effectifs.items():
        resultat = resultats.get(code, {})
        syntheses.append(
            SyntheseTerritoriale(
                code=code,
                libelle=ligne["departement"],
                etablissements=ligne["etablissements"],
                apprenants=ligne["apprenants"],
                candidats=resultat.get("candidats", 0),
                admis=resultat.get("admis", 0),
                taux_reussite=resultat.get("taux_reussite"),
                moyenne=resultat.get("moyenne"),
            )
        )
    return syntheses


@router.get(
    "/tableaux-de-bord/mon-tableau",
    response_model=TableauBord,
    tags=["Gouvernance"],
    summary="Tableau de bord propre au rôle de l'utilisateur",
    description=(
        "Indicateurs correspondant au rôle et au périmètre de l'appelant : sa moyenne "
        "et son assiduité pour un élève, ses enfants pour un parent, ses classes pour "
        "un enseignant, son établissement pour un chef d'établissement."
    ),
)
async def mon_tableau(session: SessionDep, contexte: ContexteDep) -> TableauBord:
    """Compose le tableau de bord de celui qui le demande.

    Le tableau national répond à la question d'un ministère. Celui-ci répond à
    celle d'un élève ou d'un enseignant, qui n'ont que faire des effectifs du
    pays. Aucun droit particulier n'est exigé : chacun a accès à ce qui le
    concerne, et le périmètre s'en charge.
    """
    perimetre = await resoudre_perimetre(session, contexte)
    roles = contexte.roles
    graphiques: dict[str, list[dict]] = {}

    if roles & {"SCHOOL_ADMIN", "SCHOOL_STAFF"}:
        indicateurs = await indicateurs_etablissement(session, perimetre)
        graphiques["effectifs_par_niveau"] = await repartition_par_niveau(
            session, perimetre.etablissements
        )
        graphiques["moyennes_par_classe"] = await moyennes_par_classe(
            session, perimetre.etablissements
        )
        perimetre_code, libelle = "ETABLISSEMENT", "Mon établissement"
    elif "TEACHER" in roles:
        indicateurs = await indicateurs_enseignant(session, contexte, perimetre)
        graphiques["moyennes_par_classe"] = await moyennes_par_classe(
            session, perimetre.etablissements
        )
        perimetre_code, libelle = "ENSEIGNANT", "Mes classes"
    elif "PARENT" in roles:
        indicateurs = await indicateurs_parent(session, perimetre)
        graphiques["evolution_moyennes"] = await evolution_moyennes(session, perimetre.apprenants)
        perimetre_code, libelle = "PARENT", "Mes enfants"
    elif perimetre.apprenants:
        indicateurs = await indicateurs_eleve(session, perimetre)
        graphiques["evolution_moyennes"] = await evolution_moyennes(session, perimetre.apprenants)
        perimetre_code, libelle = "ELEVE", "Ma scolarité"
    else:
        indicateurs = []
        perimetre_code, libelle = "PERSONNEL", "Mon espace"

    return TableauBord(
        perimetre=perimetre_code,
        perimetre_libelle=libelle,
        indicateurs=[IndicateurReponse(**indicateur.en_dict()) for indicateur in indicateurs],
        graphiques=graphiques,
        alertes=[],
    )


@router.get(
    "/tableaux-de-bord/mon-espace",
    tags=["Gouvernance"],
    summary="Tableau de bord adapté à l'utilisateur connecté",
    description="Compose la vue correspondant au rôle et au périmètre de l'utilisateur.",
)
async def mon_espace(session: SessionDep, contexte: ContexteDep) -> dict:
    roles = contexte.roles
    espace = {
        "utilisateur": contexte.utilisateur.nom_complet,
        "roles": sorted(roles),
        "niveau": contexte.niveau_max.value,
        "raccourcis": [],
    }

    if contexte.est_omnipotent or roles & {"MINISTRY_ADMIN", "DIRECTOR_ADMIN", "EXAM_ADMIN"}:
        espace["raccourcis"] = [
            {"libelle": "Tableau de bord national", "lien": "/tableaux-de-bord/national"},
            {"libelle": "Recherche avancée", "lien": "/recherche/avancee"},
            {"libelle": "Sessions d'examen", "lien": "/sessions"},
            {"libelle": "Cartographie", "lien": "/etablissements-carte/points"},
        ]
    elif roles & {"SCHOOL_ADMIN", "SCHOOL_STAFF"}:
        espace["raccourcis"] = [
            {"libelle": "Mes classes", "lien": "/classes"},
            {"libelle": "Mes élèves", "lien": "/apprenants"},
            {"libelle": "Bulletins", "lien": "/bulletins"},
        ]
    elif "TEACHER" in roles:
        espace["raccourcis"] = [
            {"libelle": "Mes évaluations", "lien": "/evaluations"},
            {"libelle": "Saisie des notes", "lien": "/evaluations"},
            {"libelle": "Appel", "lien": "/seances"},
        ]
    elif "STUDENT" in roles:
        espace["raccourcis"] = [
            {"libelle": "Mes bulletins", "lien": "/bulletins"},
            {"libelle": "Mes résultats", "lien": "/public/resultats"},
            {"libelle": "Mon transport", "lien": "/transport/lignes"},
        ]
    elif "PARENT" in roles:
        espace["raccourcis"] = [
            {"libelle": "Mes enfants", "lien": "/apprenants"},
            {"libelle": "Bulletins", "lien": "/bulletins"},
        ]

    if contexte.etablissements:
        etablissement = await session.get(Etablissement, next(iter(contexte.etablissements)))
        if etablissement is not None:
            espace["etablissement"] = {
                "id": str(etablissement.id),
                "nom": etablissement.nom,
                "code": etablissement.code,
            }

    return espace


# ------------------------------------------------------------------
#  Recherche avancée
# ------------------------------------------------------------------


@router.get(
    "/recherche/entites",
    tags=["Recherche"],
    summary="Entités interrogeables et leurs variables",
    description="Alimente le constructeur visuel de requêtes.",
)
async def entites_recherchables(contexte: ContexteDep) -> list[dict]:
    contexte.exiger("recherche_avancee", Action.READ)
    return [
        {
            "cle": entite.cle,
            "libelle": entite.libelle,
            "colonnes": [
                {"cle": colonne.cle, "libelle": colonne.libelle} for colonne in entite.colonnes
            ],
            "champs": entite.constructeur.decrire() + _champs_calcules(entite),
        }
        for entite in service_recherche.REGISTRE.values()
    ]


@router.post(
    "/recherche/avancee",
    response_model=ResultatRecherche,
    tags=["Recherche"],
    summary="Exécuter une requête du constructeur",
    description=(
        "Exemple : établissements du Littoral de plus de 1 000 élèves et de moins de 20 salles."
    ),
)
async def recherche_avancee(
    requete: RequeteAvancee,
    session: SessionDep,
    contexte: ContexteDep,
) -> ResultatRecherche:
    contexte.exiger("recherche_avancee", Action.READ)
    criteres = [
        Critere(champ=c.champ, operateur=Operateur(c.operateur), valeur=c.valeur)
        for c in requete.criteres
    ]
    resultat = await service_recherche.executer(
        session,
        requete.entite,
        criteres,
        conjonction=requete.conjonction,
        tri=requete.tri,
        sens=requete.sens,
        page=requete.page,
        taille=requete.taille,
    )
    return ResultatRecherche(**resultat)


@router.post(
    "/recherche/avancee/export",
    tags=["Recherche"],
    summary="Exporter le résultat d'une requête",
    response_class=Response,
)
async def exporter_recherche(
    requete: RequeteAvancee,
    session: SessionDep,
    contexte: ContexteDep,
    format_export: Annotated[str, Query(pattern="^(csv|json)$")] = "csv",
) -> Response:
    contexte.exiger("recherche_avancee", Action.EXPORT)
    criteres = [
        Critere(champ=c.champ, operateur=Operateur(c.operateur), valeur=c.valeur)
        for c in requete.criteres
    ]
    resultat = await service_recherche.executer(
        session,
        requete.entite,
        criteres,
        conjonction=requete.conjonction,
        tri=requete.tri,
        sens=requete.sens,
        page=1,
        taille=5000,
    )

    if format_export == "json":
        import json

        return Response(
            content=json.dumps(resultat, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{requete.entite}.json"'},
        )

    entetes = [colonne["libelle"] for colonne in resultat["colonnes"]]
    cles = [colonne["cle"] for colonne in resultat["colonnes"]]
    lignes = [[ligne.get(cle) for cle in cles] for ligne in resultat["lignes"]]
    return Response(
        content=exporter_csv(entetes, lignes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{requete.entite}.csv"'},
    )


@router.post(
    "/recherche/langage-naturel",
    response_model=ReponseNaturelle,
    tags=["Recherche"],
    summary="Poser une question en français",
    description=(
        "Traduit une question française en filtres structurés, puis exécute la "
        "requête. Exemple : « Montre-moi les élèves des CEG de Porto-Novo ayant "
        "au moins 17 de moyenne en mathématiques. »"
    ),
)
async def recherche_naturelle(
    demande: QuestionNaturelle,
    session: SessionDep,
    contexte: ContexteDep,
) -> ReponseNaturelle:
    contexte.exiger("recherche_avancee", Action.READ)
    interpretation = ai.interpreter(demande.question)

    reponse = ReponseNaturelle(
        question=interpretation.question,
        entite=interpretation.entite,
        confiance=round(interpretation.confiance, 2),
        explications=interpretation.explications,
        filtres=[
            {"champ": c.champ, "operateur": c.operateur.value, "valeur": c.valeur}
            for c in interpretation.criteres
        ],
    )

    if not demande.executer:
        return reponse

    # Seuls les critères correspondant à des champs connus sont appliqués.
    entite = service_recherche.obtenir_entite(interpretation.entite)
    champs_connus = set(entite.constructeur.champs)

    def applicable(champ: str) -> bool:
        resolu = service_recherche.resoudre_synonyme(entite.cle, champ)
        if resolu in champs_connus:
            return True
        return service_recherche.est_champ_calcule(resolu, entite.cle)

    retenus = [critere for critere in interpretation.criteres if applicable(critere.champ)]
    ignores = [c.champ for c in interpretation.criteres if c not in retenus]
    if ignores:
        reponse.explications.append(
            f"Critères ignorés car non applicables à « {entite.libelle} » : {', '.join(ignores)}."
        )

    resultat = await service_recherche.executer(
        session,
        interpretation.entite,
        retenus,
        conjonction=Conjonction.ET,
        page=1,
        taille=demande.taille,
    )
    reponse.resultat = ResultatRecherche(**resultat)
    return reponse


@router.get(
    "/recherche/suggestions",
    tags=["Recherche"],
    summary="Exemples de questions",
)
async def suggestions(contexte: ContexteDep) -> list[str]:
    contexte.exiger("recherche_avancee", Action.READ)
    return ai.suggestions()


@router.get(
    "/recherche/globale",
    response_model=list[RechercheGlobaleResultat],
    tags=["Recherche"],
    summary="Recherche transverse",
    description="Recherche un terme dans les apprenants, enseignants, établissements…",
)
async def recherche_globale(
    session: SessionDep,
    contexte: ContexteDep,
    q: Annotated[str, Query(min_length=2)],
    limite: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[RechercheGlobaleResultat]:
    contexte.exiger("recherche_avancee", Action.READ)
    terme = f"%{q.strip()}%"
    resultats: list[RechercheGlobaleResultat] = []

    stmt = (
        select(Apprenant)
        .where(
            Apprenant.supprime.is_(False),
            or_(
                Apprenant.nom.ilike(terme),
                Apprenant.prenoms.ilike(terme),
                Apprenant.identifiant_educatif.ilike(terme),
            ),
        )
        .limit(limite)
    )
    resultats += [
        RechercheGlobaleResultat(
            type="apprenant",
            id=apprenant.id,
            libelle=apprenant.nom_complet,
            description=apprenant.identifiant_educatif,
            lien=f"/apprenants/{apprenant.id}",
        )
        for apprenant in (await session.execute(stmt)).scalars()
    ]

    stmt = (
        select(Etablissement)
        .where(
            Etablissement.supprime.is_(False),
            or_(Etablissement.nom.ilike(terme), Etablissement.code.ilike(terme)),
        )
        .limit(limite)
    )
    resultats += [
        RechercheGlobaleResultat(
            type="etablissement",
            id=etablissement.id,
            libelle=etablissement.nom,
            description=etablissement.code,
            lien=f"/etablissements/{etablissement.id}",
        )
        for etablissement in (await session.execute(stmt)).scalars()
    ]

    stmt = (
        select(Enseignant)
        .where(
            Enseignant.supprime.is_(False),
            or_(
                Enseignant.nom.ilike(terme),
                Enseignant.prenoms.ilike(terme),
                Enseignant.matricule.ilike(terme),
            ),
        )
        .limit(limite)
    )
    resultats += [
        RechercheGlobaleResultat(
            type="enseignant",
            id=enseignant.id,
            libelle=enseignant.nom_complet,
            description=enseignant.matricule,
            lien=f"/enseignants/{enseignant.id}",
        )
        for enseignant in (await session.execute(stmt)).scalars()
    ]

    stmt = select(Classe).where(Classe.libelle.ilike(terme)).limit(limite)
    resultats += [
        RechercheGlobaleResultat(
            type="classe",
            id=classe.id,
            libelle=classe.libelle,
            description=classe.code,
            lien=f"/classes/{classe.id}",
        )
        for classe in (await session.execute(stmt)).scalars()
    ]

    stmt = (
        select(DiplomeDelivre)
        .where(
            or_(
                DiplomeDelivre.numero.ilike(terme),
                DiplomeDelivre.titulaire_nom.ilike(terme),
            )
        )
        .limit(limite)
    )
    resultats += [
        RechercheGlobaleResultat(
            type="diplome",
            id=diplome.id,
            libelle=f"{diplome.intitule} — {diplome.titulaire_nom}",
            description=diplome.numero,
            lien=f"/public/verification/{diplome.code_verification}",
        )
        for diplome in (await session.execute(stmt)).scalars()
    ]

    stmt = select(Projet).where(Projet.titre.ilike(terme)).limit(limite)
    resultats += [
        RechercheGlobaleResultat(
            type="projet",
            id=projet.id,
            libelle=projet.titre,
            description=projet.domaine,
            lien=f"/projets/{projet.id}",
        )
        for projet in (await session.execute(stmt)).scalars()
    ]

    return resultats[: limite * 2]


# ------------------------------------------------------------------
#  Requêtes enregistrées, règles et alertes
# ------------------------------------------------------------------

requetes = creer_routeur_crud(
    modele=RequeteEnregistree,
    schema_lecture=RequeteEnregistreeLecture,
    schema_creation=RequeteEnregistreeEcriture,
    schema_maj=RequeteEnregistreeEcriture,
    prefixe="/requetes-enregistrees",
    tag="Recherche",
    ressource="recherche_avancee",
    libelle_singulier="requête enregistrée",
    libelle_pluriel="requêtes enregistrées",
    champs_recherche=("code", "libelle", "requete_naturelle"),
)


@requetes.post(
    "/{identifiant}/executer",
    response_model=ResultatRecherche,
    summary="Exécuter une requête enregistrée",
)
async def executer_requete(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    page: Annotated[int, Query(ge=1)] = 1,
    taille: Annotated[int, Query(ge=1, le=200)] = 25,
) -> ResultatRecherche:
    contexte.exiger("recherche_avancee", Action.READ)
    requete = await obtenir_ou_404(session, RequeteEnregistree, identifiant, "Requête enregistrée")

    charge = requete.filtres or {}
    criteres = [
        Critere(
            champ=element["champ"],
            operateur=Operateur(element["operateur"]),
            valeur=element.get("valeur"),
        )
        for element in charge.get("criteres", [])
    ]
    conjonction = Conjonction(charge.get("conjonction", "AND"))

    resultat = await service_recherche.executer(
        session,
        requete.entite_cible,
        criteres,
        conjonction=conjonction,
        page=page,
        taille=taille,
    )

    requete.nombre_executions += 1
    requete.derniere_execution = datetime.now(UTC)
    await session.flush()

    return ResultatRecherche(**resultat)


router.include_router(requetes)

router.include_router(
    creer_routeur_crud(
        modele=RegleMetier,
        schema_lecture=RegleMetierLecture,
        schema_creation=RegleMetierEcriture,
        schema_maj=RegleMetierEcriture,
        prefixe="/regles-metier",
        tag="Gouvernance",
        ressource="parametres",
        libelle_singulier="règle métier",
        libelle_pluriel="règles métier",
        champs_recherche=("code", "libelle", "domaine"),
        tri_defaut="priorite",
        champs_filtrables=(
            DescripteurChamp("code", "Code", RegleMetier.code),
            DescripteurChamp("domaine", "Domaine", RegleMetier.domaine, "liste"),
            DescripteurChamp("entite_cible", "Entité", RegleMetier.entite_cible, "liste"),
            DescripteurChamp("active", "Active", RegleMetier.active, "booleen"),
        ),
    )
)

alertes = creer_routeur_crud(
    modele=Alerte,
    portee=Portee(etablissement="etablissement_id"),
    schema_lecture=AlerteLecture,
    schema_creation=None,
    schema_maj=None,
    prefixe="/alertes",
    tag="Gouvernance",
    ressource="analytics",
    libelle_singulier="alerte",
    libelle_pluriel="alertes",
    champs_recherche=("code", "titre"),
    contrainte_unicite=None,
    tri_defaut="created_at",
    champs_filtrables=(
        DescripteurChamp("code", "Code", Alerte.code),
        DescripteurChamp("niveau", "Niveau", Alerte.niveau, "liste"),
        DescripteurChamp("domaine", "Domaine", Alerte.domaine, "liste"),
        DescripteurChamp("traitee", "Traitée", Alerte.traitee, "booleen"),
        DescripteurChamp("etablissement_id", "Établissement", Alerte.etablissement_id, "uuid"),
    ),
)


@alertes.post(
    "/{identifiant}/traiter",
    response_model=AlerteLecture,
    summary="Marquer une alerte comme traitée",
)
async def traiter_alerte(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> Alerte:
    contexte.exiger("analytics", Action.UPDATE)
    alerte = await obtenir_ou_404(session, Alerte, identifiant, "Alerte")
    alerte.traitee = True
    alerte.traitee_le = datetime.now(UTC)
    alerte.traitee_par_id = contexte.id
    await session.flush()
    return alerte


router.include_router(alertes)


# ------------------------------------------------------------------
#  Indicateurs et rapports
# ------------------------------------------------------------------


@router.get(
    "/indicateurs",
    tags=["Gouvernance"],
    summary="Indicateurs précalculés",
)
async def indicateurs(
    session: SessionDep,
    contexte: ContexteDep,
    perimetre_type: Annotated[str, Query()] = "NATIONAL",
    perimetre_id: Annotated[uuid.UUID | None, Query()] = None,
    annee_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[dict]:
    contexte.exiger("analytics", Action.READ)
    stmt = select(IndicateurStatistique).where(
        IndicateurStatistique.perimetre_type == perimetre_type
    )
    if perimetre_id:
        stmt = stmt.where(IndicateurStatistique.perimetre_id == perimetre_id)
    if annee_id:
        stmt = stmt.where(IndicateurStatistique.annee_id == annee_id)

    return [
        {
            "code": indicateur.code,
            "libelle": indicateur.libelle,
            "valeur": indicateur.valeur,
            "unite": indicateur.unite,
            "variation": indicateur.variation_pourcentage,
            "perimetre": indicateur.perimetre_libelle,
        }
        for indicateur in (await session.execute(stmt)).scalars()
    ]


@router.post(
    "/rapports",
    status_code=status.HTTP_201_CREATED,
    tags=["Gouvernance"],
    summary="Générer un rapport",
    description=(
        "Types : annuel, etablissement, departement, examen, reussite, "
        "enseignants, infrastructure, inclusion."
    ),
)
async def generer_rapport(
    demande: DemandeRapport,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> dict:
    contexte.exiger("rapports", Action.CREATE)

    donnees: dict = {}
    titre = demande.titre or f"Rapport {demande.type_rapport}"

    if demande.type_rapport == "examen" and demande.session_id:
        session_examen = await obtenir_ou_404(session, SessionExamen, demande.session_id, "Session")
        titre = demande.titre or f"Rapport de session — {session_examen.libelle}"
        donnees = {
            "session": session_examen.libelle,
            "inscrits": session_examen.nombre_inscrits,
            "presents": session_examen.nombre_presents,
            "admis": session_examen.nombre_admis,
            "taux_reussite": session_examen.taux_reussite,
            "par_departement": await resultats_par_departement(session, demande.session_id),
        }
    elif demande.type_rapport == "inclusion":
        stmt = (
            select(Apprenant.type_handicap, func.count())
            .where(Apprenant.supprime.is_(False))
            .group_by(Apprenant.type_handicap)
        )
        repartition = {
            handicap.value: total for handicap, total in (await session.execute(stmt)).all()
        }
        stmt = (
            select(func.count())
            .select_from(Etablissement)
            .where(Etablissement.accessibilite.in_(["ACCESSIBLE", "ADAPTE"]))
        )
        accessibles = int((await session.execute(stmt)).scalar_one())
        titre = demande.titre or "Rapport national sur l'inclusion"
        donnees = {
            "repartition_handicap": repartition,
            "etablissements_accessibles": accessibles,
        }
    else:
        indicateurs_nationaux = await tableau_bord_national(session, demande.annee_id)
        donnees = {
            "indicateurs": [i.en_dict() for i in indicateurs_nationaux],
            "territoires": await effectifs_par_departement(session, demande.annee_id),
        }

    rapport = Rapport(
        reference=generer_reference("RAP"),
        titre=titre,
        type_rapport=demande.type_rapport,
        annee_id=demande.annee_id,
        etablissement_id=demande.etablissement_id,
        structure_id=demande.structure_id,
        parametres=demande.model_dump(mode="json"),
        donnees=donnees,
        format_export=demande.format_export,
        genere_par_id=contexte.id,
        genere_le=datetime.now(UTC),
    )
    session.add(rapport)
    await session.flush()

    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="rapports",
        entite_id=rapport.id,
        entite_libelle=titre,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return {"id": str(rapport.id), "reference": rapport.reference, "titre": titre}


@router.get(
    "/rapports/{identifiant}/pdf",
    tags=["Gouvernance"],
    summary="Télécharger un rapport en PDF",
    response_class=Response,
)
async def rapport_pdf(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> Response:
    contexte.exiger("rapports", Action.PRINT)
    rapport = await obtenir_ou_404(session, Rapport, identifiant, "Rapport")

    sections: list = []
    donnees = rapport.donnees or {}

    if "indicateurs" in donnees:
        sections.append(
            BlocTableau(
                entetes=["Indicateur", "Valeur", "Unité"],
                lignes=[
                    [i["libelle"], f"{i['valeur']:g}", i.get("unite") or ""]
                    for i in donnees["indicateurs"]
                ],
                alignements={1: "right"},
            )
        )
    if "territoires" in donnees:
        sections.append("Répartition territoriale")
        sections.append(
            BlocTableau(
                entetes=["Département", "Établissements", "Apprenants"],
                lignes=[
                    [t["departement"], str(t["etablissements"]), str(t["apprenants"])]
                    for t in donnees["territoires"]
                ],
                alignements={1: "right", 2: "right"},
            )
        )
    if "par_departement" in donnees:
        sections.append("Résultats par département")
        sections.append(
            BlocTableau(
                entetes=["Département", "Candidats", "Admis", "Taux", "Moyenne"],
                lignes=[
                    [
                        d["departement"],
                        str(d["candidats"]),
                        str(d["admis"]),
                        f"{d['taux_reussite']} %",
                        str(d["moyenne"] or "—"),
                    ]
                    for d in donnees["par_departement"]
                ],
                alignements={1: "right", 2: "right", 3: "right", 4: "right"},
            )
        )
    if "repartition_handicap" in donnees:
        sections.append(
            {
                "Établissements accessibles": str(donnees.get("etablissements_accessibles", 0)),
                **{k: str(v) for k, v in donnees["repartition_handicap"].items()},
            }
        )

    contenu = generer_document(
        EnTeteDocument(
            ministere="Ministère en charge de l'éducation",
            titre=rapport.titre,
            sous_titre=f"Rapport {rapport.type_rapport} — référence {rapport.reference}",
        ),
        sections or ["Aucune donnée à restituer."],
        paysage=True,
    )
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{rapport.reference}.pdf"'},
    )


@router.get(
    "/audit",
    tags=["Gouvernance"],
    summary="Journal d'audit",
    description="Trace des opérations sensibles, filtrable par entité et par utilisateur.",
)
async def journal_audit(
    session: SessionDep,
    contexte: ContexteDep,
    entite_type: Annotated[str | None, Query()] = None,
    entite_id: Annotated[uuid.UUID | None, Query()] = None,
    utilisateur_id: Annotated[uuid.UUID | None, Query()] = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[dict]:
    contexte.exiger("audit", Action.READ)
    stmt = select(JournalAudit).order_by(JournalAudit.created_at.desc()).limit(limite)
    if entite_type:
        stmt = stmt.where(JournalAudit.entite_type == entite_type)
    if entite_id:
        stmt = stmt.where(JournalAudit.entite_id == entite_id)
    if utilisateur_id:
        stmt = stmt.where(JournalAudit.utilisateur_id == utilisateur_id)

    return [
        {
            "id": str(entree.id),
            "date": entree.created_at.isoformat(),
            "utilisateur": entree.utilisateur_email,
            "action": entree.action,
            "entite_type": entree.entite_type,
            "entite_id": str(entree.entite_id) if entree.entite_id else None,
            "entite_libelle": entree.entite_libelle,
            "valeurs_avant": entree.valeurs_avant,
            "valeurs_apres": entree.valeurs_apres,
            "adresse_ip": entree.adresse_ip,
            "succes": entree.succes,
        }
        for entree in (await session.execute(stmt)).scalars()
    ]


@router.get(
    "/annees/{identifiant}/comparaison",
    tags=["Gouvernance"],
    summary="Comparaison pluriannuelle",
    description="Évolution des effectifs, des moyennes et des taux de réussite.",
)
async def comparaison_annuelle(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> dict:
    contexte.exiger("analytics", Action.READ)
    await obtenir_ou_404(session, AnneeAcademique, identifiant, "Année académique")

    stmt = (
        select(
            SessionExamen.annee,
            Examen.sigle,
            SessionExamen.taux_reussite,
            SessionExamen.moyenne_generale,
            SessionExamen.nombre_inscrits,
        )
        .join(Examen, Examen.id == SessionExamen.examen_id)
        .order_by(SessionExamen.annee)
    )
    evolution = [
        {
            "annee": annee,
            "examen": sigle,
            "taux_reussite": taux,
            "moyenne": moyenne,
            "inscrits": inscrits,
        }
        for annee, sigle, taux, moyenne, inscrits in (await session.execute(stmt)).all()
    ]

    return {"evolution": evolution}


@router.get(
    "/moteur-regles/simuler",
    tags=["Gouvernance"],
    summary="Simuler le moteur de règles",
    description="Applique les règles actives aux données courantes et renvoie les déclenchements.",
)
async def simuler_regles(
    session: SessionDep,
    contexte: ContexteDep,
    domaine: Annotated[str | None, Query()] = None,
) -> list[dict]:
    contexte.exiger("parametres", Action.READ)
    stmt = select(RegleMetier).where(RegleMetier.active.is_(True)).order_by(RegleMetier.priorite)
    if domaine:
        stmt = stmt.where(RegleMetier.domaine == domaine)

    declenchements = []
    for regle in (await session.execute(stmt)).scalars():
        conditions = regle.conditions or {}
        champ = conditions.get("champ")
        operateur = conditions.get("operateur")
        valeur = conditions.get("valeur")
        if not champ or not operateur:
            continue

        try:
            entite = service_recherche.obtenir_entite(regle.entite_cible)
        except Exception:
            declenchements.append(
                {
                    "regle": regle.code,
                    "libelle": regle.libelle,
                    "applicable": False,
                    "message": f"Entité « {regle.entite_cible} » non exposée à la recherche.",
                }
            )
            continue

        # Un champ calculé (taux de réussite, ratio élèves/enseignant…) n'est pas
        # une colonne déclarée : il est résolu par sous-requête, et reste donc
        # parfaitement interrogeable.
        if champ not in entite.constructeur.champs and not service_recherche.est_champ_calcule(
            champ, regle.entite_cible
        ):
            declenchements.append(
                {
                    "regle": regle.code,
                    "libelle": regle.libelle,
                    "applicable": False,
                    "message": f"Champ « {champ} » non interrogeable sur « {entite.libelle} ».",
                }
            )
            continue

        resultat = await service_recherche.executer(
            session,
            regle.entite_cible,
            [Critere(champ=champ, operateur=Operateur(operateur), valeur=valeur)],
            page=1,
            taille=5,
        )
        declenchements.append(
            {
                "regle": regle.code,
                "libelle": regle.libelle,
                "domaine": regle.domaine,
                "applicable": True,
                "condition": f"{champ} {operateur} {valeur}",
                "occurrences": resultat["total"],
                "consequences": regle.consequences,
                "exemples": resultat["lignes"][:3],
            }
        )

    return declenchements
