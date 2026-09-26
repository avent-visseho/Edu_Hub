"""Apprenants, parents, enseignants et personnels."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.enums import Action, RoleCode
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.engines.audit import journaliser
from app.engines.portee import Portee
from app.engines.search import DescripteurChamp
from app.models.apprenant import Apprenant, ApprenantParent, Parent
from app.models.diplome import DiplomeDelivre
from app.models.etablissement import Etablissement
from app.models.evaluation import Bulletin
from app.models.examen import Candidat, Examen, ResultatExamen, SessionExamen
from app.models.identity import Role, Utilisateur, UtilisateurRole
from app.models.pedagogie import SyntheseAssiduite
from app.models.personnel import Enseignant, EnseignantMatiere, Personnel
from app.models.projet import CompetenceApprenant, MembreProjet, Projet, Stage
from app.models.scolarite import AnneeAcademique, Classe, Inscription, Periode, Serie
from app.models.vie_etudiante import AbonnementTransport, CandidatureBourse, LigneTransport
from app.schemas.base import MessageReponse
from app.schemas.personne import (
    ApprenantCreation,
    ApprenantLecture,
    ApprenantMiseAJour,
    DossierApprenant,
    EnseignantCreation,
    EnseignantLecture,
    EnseignantMiseAJour,
    LienParenteEcriture,
    LigneBulletinResume,
    LigneExamenResume,
    LigneParcours,
    ParentEcriture,
    ParentLecture,
    PersonnelEcriture,
    PersonnelLecture,
)
from app.utils.codes import generer_identifiant_educatif, generer_matricule, generer_mot_de_passe

router = APIRouter()


CHAMPS_APPRENANT = (
    DescripteurChamp(
        "identifiant_educatif", "Identifiant éducatif", Apprenant.identifiant_educatif
    ),
    DescripteurChamp("nom", "Nom", Apprenant.nom),
    DescripteurChamp("prenoms", "Prénoms", Apprenant.prenoms),
    DescripteurChamp("sexe", "Sexe", Apprenant.sexe, "liste", ("MASCULIN", "FEMININ")),
    DescripteurChamp("date_naissance", "Date de naissance", Apprenant.date_naissance, "date"),
    DescripteurChamp("commune_id", "Commune", Apprenant.commune_id, "uuid"),
    DescripteurChamp(
        "etablissement_actuel_id", "Établissement", Apprenant.etablissement_actuel_id, "uuid"
    ),
    DescripteurChamp("statut", "Statut", Apprenant.statut, "liste"),
    DescripteurChamp("type_handicap", "Besoin spécifique", Apprenant.type_handicap, "liste"),
    DescripteurChamp("tiers_temps", "Tiers temps", Apprenant.tiers_temps, "booleen"),
    DescripteurChamp("orphelin", "Orphelin", Apprenant.orphelin, "booleen"),
    DescripteurChamp(
        "situation_vulnerable", "Situation vulnérable", Apprenant.situation_vulnerable, "booleen"
    ),
)


# ------------------------------------------------------------------
#  Apprenants
# ------------------------------------------------------------------

apprenants = creer_routeur_crud(
    modele=Apprenant,
    portee=Portee(est_apprenant=True),
    schema_lecture=ApprenantLecture,
    schema_creation=None,
    schema_maj=ApprenantMiseAJour,
    prefixe="/apprenants",
    tag="Apprenants",
    ressource="apprenants",
    libelle_singulier="apprenant",
    libelle_pluriel="apprenants",
    champs_recherche=("nom", "prenoms", "identifiant_educatif", "matricule"),
    champs_filtrables=CHAMPS_APPRENANT,
    tri_defaut="nom",
    contrainte_unicite=None,
)


@apprenants.post(
    "",
    response_model=ApprenantLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Inscrire un nouvel apprenant",
    description="Attribue automatiquement l'identifiant éducatif national.",
)
async def creer_apprenant(
    donnees: ApprenantCreation,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> Apprenant:
    contexte.exiger("apprenants", Action.CREATE)

    annee = date.today().year
    sequence = (
        int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(Apprenant)
                    .where(Apprenant.identifiant_educatif.like(f"EDU-{annee}-%"))
                )
            ).scalar_one()
        )
        + 1
    )
    identifiant = generer_identifiant_educatif(sequence, annee)

    valeurs = donnees.model_dump(exclude={"creer_compte"}, exclude_unset=True)
    apprenant = Apprenant(identifiant_educatif=identifiant, **valeurs)

    if donnees.creer_compte:
        email = donnees.email or f"{identifiant.lower()}@apprenant.bj"
        existant = (
            await session.execute(select(Utilisateur).where(Utilisateur.email == email.lower()))
        ).scalar_one_or_none()
        if existant is not None:
            raise ConflictError("Un compte utilise déjà cette adresse électronique.")

        mot_de_passe = generer_mot_de_passe()
        utilisateur = Utilisateur(
            email=email.lower(),
            mot_de_passe=hash_password(mot_de_passe),
            nom=donnees.nom,
            prenoms=donnees.prenoms,
            sexe=donnees.sexe,
            date_naissance=donnees.date_naissance,
            langue=donnees.langue_principale,
            type_handicap=donnees.type_handicap,
            doit_changer_mot_de_passe=True,
        )
        session.add(utilisateur)
        await session.flush()

        role = (
            await session.execute(select(Role).where(Role.code == RoleCode.STUDENT.value))
        ).scalar_one_or_none()
        if role is not None:
            session.add(
                UtilisateurRole(
                    utilisateur_id=utilisateur.id,
                    role_id=role.id,
                    etablissement_id=donnees.etablissement_actuel_id,
                )
            )
        apprenant.utilisateur_id = utilisateur.id

    session.add(apprenant)
    await session.flush()
    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="apprenants",
        entite_id=apprenant.id,
        entite_libelle=apprenant.nom_complet,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return apprenant


@apprenants.get(
    "/identifiant/{identifiant_educatif}",
    response_model=ApprenantLecture,
    summary="Rechercher un apprenant par son identifiant éducatif",
)
async def par_identifiant(
    identifiant_educatif: str, session: SessionDep, contexte: ContexteDep
) -> Apprenant:
    contexte.exiger("apprenants", Action.READ)
    apprenant = (
        await session.execute(
            select(Apprenant).where(Apprenant.identifiant_educatif == identifiant_educatif.upper())
        )
    ).scalar_one_or_none()
    if apprenant is None:
        raise NotFoundError("Aucun apprenant ne porte cet identifiant éducatif.")
    return apprenant


@apprenants.get(
    "/{identifiant}/dossier",
    response_model=DossierApprenant,
    summary="Dossier scolaire complet",
    description=(
        "Parcours, bulletins, examens, diplômes, assiduité, bourses, projets, "
        "stages, compétences et transport — la vue à 360° d'un apprenant."
    ),
)
async def dossier(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> DossierApprenant:
    contexte.exiger("apprenants", Action.READ)
    apprenant = await obtenir_ou_404(session, Apprenant, identifiant, "Apprenant")

    dossier = DossierApprenant(apprenant=ApprenantLecture.model_validate(apprenant))

    # --- Parents ---
    stmt = (
        select(ApprenantParent, Parent)
        .join(Parent, Parent.id == ApprenantParent.parent_id)
        .where(ApprenantParent.apprenant_id == identifiant)
    )
    dossier.parents = [
        {
            "id": str(parent.id),
            "nom_complet": parent.nom_complet,
            "lien": lien.lien.value,
            "contact_principal": lien.contact_principal,
            "telephone": parent.telephone,
            "profession": parent.profession,
        }
        for lien, parent in (await session.execute(stmt)).all()
    ]

    # --- Parcours scolaire ---
    stmt = (
        select(Inscription)
        .where(Inscription.apprenant_id == identifiant)
        .options(
            selectinload(Inscription.annee),
            selectinload(Inscription.etablissement),
            selectinload(Inscription.classe),
        )
        .order_by(Inscription.created_at)
    )
    dossier.parcours = [
        LigneParcours(
            annee=inscription.annee.code if inscription.annee else "—",
            etablissement=inscription.etablissement.nom if inscription.etablissement else None,
            classe=inscription.classe.libelle if inscription.classe else None,
            statut=inscription.statut.value,
            moyenne_annuelle=inscription.moyenne_annuelle,
            rang=inscription.rang_annuel,
            decision=inscription.decision.value,
        )
        for inscription in (await session.execute(stmt)).scalars()
    ]

    # --- Bulletins ---
    stmt = (
        select(Bulletin, Periode, Classe)
        .join(Periode, Periode.id == Bulletin.periode_id)
        .join(Classe, Classe.id == Bulletin.classe_id)
        .where(Bulletin.apprenant_id == identifiant)
        .order_by(Periode.numero)
    )
    dossier.bulletins = [
        LigneBulletinResume(
            id=bulletin.id,
            numero=bulletin.numero,
            periode=periode.libelle,
            classe=classe.libelle,
            moyenne_generale=bulletin.moyenne_generale,
            rang=bulletin.rang,
            effectif_classe=bulletin.effectif_classe,
            mention=bulletin.mention,
            decision=bulletin.decision.value if bulletin.decision else None,
            publie=bulletin.publie,
        )
        for bulletin, periode, classe in (await session.execute(stmt)).all()
    ]

    # --- Examens et résultats ---
    stmt = (
        select(Candidat, SessionExamen, Examen, ResultatExamen, Serie)
        .join(SessionExamen, SessionExamen.id == Candidat.session_id)
        .join(Examen, Examen.id == SessionExamen.examen_id)
        .outerjoin(ResultatExamen, ResultatExamen.candidat_id == Candidat.id)
        .outerjoin(Serie, Serie.id == Candidat.serie_id)
        .where(Candidat.apprenant_id == identifiant)
    )
    dossier.examens = [
        LigneExamenResume(
            numero_candidat=candidat.numero_candidat,
            examen=examen.nom,
            session=session_examen.libelle,
            serie=serie.code if serie else None,
            statut_dossier=candidat.statut_dossier.value,
            moyenne=resultat.moyenne if resultat else None,
            mention=resultat.mention if resultat else None,
            decision=resultat.decision.value if resultat else None,
        )
        for candidat, session_examen, examen, resultat, serie in (await session.execute(stmt)).all()
    ]

    # --- Diplômes ---
    stmt = select(DiplomeDelivre).where(DiplomeDelivre.apprenant_id == identifiant)
    dossier.diplomes = [
        {
            "id": str(diplome.id),
            "numero": diplome.numero,
            "intitule": diplome.intitule,
            "annee": diplome.annee,
            "mention": diplome.mention,
            "moyenne": diplome.moyenne,
            "code_verification": diplome.code_verification,
            "date_delivrance": diplome.date_delivrance.isoformat(),
        }
        for diplome in (await session.execute(stmt)).scalars()
    ]

    # --- Assiduité ---
    stmt = select(
        func.sum(SyntheseAssiduite.seances_totales),
        func.sum(SyntheseAssiduite.presences),
        func.sum(SyntheseAssiduite.absences_justifiees),
        func.sum(SyntheseAssiduite.absences_injustifiees),
        func.sum(SyntheseAssiduite.retards),
    ).where(SyntheseAssiduite.apprenant_id == identifiant)
    total, presences, justifiees, injustifiees, retards = (await session.execute(stmt)).one()
    if total:
        dossier.assiduite = {
            "seances": int(total),
            "presences": int(presences or 0),
            "absences_justifiees": int(justifiees or 0),
            "absences_injustifiees": int(injustifiees or 0),
            "retards": int(retards or 0),
            "taux_presence": round((presences or 0) * 100 / total, 2),
        }

    # --- Bourses, projets, stages, compétences, transport ---
    stmt = select(CandidatureBourse).where(CandidatureBourse.apprenant_id == identifiant)
    dossier.bourses = [
        {
            "numero": candidature.numero,
            "statut": candidature.statut.value,
            "montant_attribue": candidature.montant_attribue,
        }
        for candidature in (await session.execute(stmt)).scalars()
    ]

    stmt = (
        select(Projet, MembreProjet)
        .join(MembreProjet, MembreProjet.projet_id == Projet.id)
        .where(MembreProjet.apprenant_id == identifiant)
    )
    dossier.projets = [
        {
            "id": str(projet.id),
            "titre": projet.titre,
            "domaine": projet.domaine,
            "role": membre.role.value,
            "statut": projet.statut.value,
        }
        for projet, membre in (await session.execute(stmt)).all()
    ]

    stmt = select(Stage).where(Stage.apprenant_id == identifiant)
    dossier.stages = [
        {
            "reference": stage.reference,
            "sujet": stage.sujet,
            "date_debut": stage.date_debut.isoformat(),
            "date_fin": stage.date_fin.isoformat(),
            "note_finale": stage.note_finale,
            "valide": stage.valide,
        }
        for stage in (await session.execute(stmt)).scalars()
    ]

    stmt = select(CompetenceApprenant).where(CompetenceApprenant.apprenant_id == identifiant)
    dossier.competences = [
        {"libelle": competence.libelle, "niveau": competence.niveau, "source": competence.source}
        for competence in (await session.execute(stmt)).scalars()
    ]

    stmt = (
        select(AbonnementTransport, LigneTransport)
        .join(LigneTransport, LigneTransport.id == AbonnementTransport.ligne_id)
        .where(AbonnementTransport.apprenant_id == identifiant)
    )
    dossier.transport = [
        {
            "ligne": ligne.libelle,
            "numero_carte": abonnement.numero_carte,
            "date_fin": abonnement.date_fin.isoformat(),
            "actif": abonnement.actif,
        }
        for abonnement, ligne in (await session.execute(stmt)).all()
    ]

    return dossier


@apprenants.post(
    "/{identifiant}/parents",
    response_model=MessageReponse,
    summary="Rattacher un parent à un apprenant",
)
async def rattacher_parent(
    identifiant: uuid.UUID,
    donnees: LienParenteEcriture,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("apprenants", Action.UPDATE)
    await obtenir_ou_404(session, Apprenant, identifiant, "Apprenant")
    await obtenir_ou_404(session, Parent, donnees.parent_id, "Parent")

    existant = (
        await session.execute(
            select(ApprenantParent).where(
                ApprenantParent.apprenant_id == identifiant,
                ApprenantParent.parent_id == donnees.parent_id,
            )
        )
    ).scalar_one_or_none()
    if existant is not None:
        raise ConflictError("Ce parent est déjà rattaché à l'apprenant.")

    session.add(ApprenantParent(apprenant_id=identifiant, **donnees.model_dump()))
    return MessageReponse(message="Parent rattaché à l'apprenant.")


router.include_router(apprenants)


# ------------------------------------------------------------------
#  Parents
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Parent,
        schema_lecture=ParentLecture,
        schema_creation=ParentEcriture,
        schema_maj=ParentEcriture,
        prefixe="/parents",
        tag="Apprenants",
        ressource="parents",
        libelle_singulier="parent",
        libelle_pluriel="parents",
        champs_recherche=("nom", "prenoms", "telephone"),
        contrainte_unicite=None,
        tri_defaut="nom",
        champs_filtrables=(
            DescripteurChamp("nom", "Nom", Parent.nom),
            DescripteurChamp("prenoms", "Prénoms", Parent.prenoms),
            DescripteurChamp("profession", "Profession", Parent.profession),
            DescripteurChamp("commune_id", "Commune", Parent.commune_id, "uuid"),
        ),
    )
)


# ------------------------------------------------------------------
#  Enseignants
# ------------------------------------------------------------------

enseignants = creer_routeur_crud(
    modele=Enseignant,
    schema_lecture=EnseignantLecture,
    schema_creation=None,
    schema_maj=EnseignantMiseAJour,
    prefixe="/enseignants",
    tag="Enseignants",
    ressource="enseignants",
    libelle_singulier="enseignant",
    libelle_pluriel="enseignants",
    champs_recherche=("nom", "prenoms", "matricule", "specialite"),
    tri_defaut="nom",
    contrainte_unicite="matricule",
    champs_filtrables=(
        DescripteurChamp("matricule", "Matricule", Enseignant.matricule),
        DescripteurChamp("nom", "Nom", Enseignant.nom),
        DescripteurChamp("prenoms", "Prénoms", Enseignant.prenoms),
        DescripteurChamp("sexe", "Sexe", Enseignant.sexe, "liste"),
        DescripteurChamp("grade", "Grade", Enseignant.grade),
        DescripteurChamp("statut_agent", "Statut", Enseignant.statut_agent, "liste"),
        DescripteurChamp("situation", "Situation", Enseignant.situation, "liste"),
        DescripteurChamp(
            "etablissement_principal_id",
            "Établissement",
            Enseignant.etablissement_principal_id,
            "uuid",
        ),
        DescripteurChamp("peut_corriger", "Peut corriger", Enseignant.peut_corriger, "booleen"),
        DescripteurChamp(
            "peut_surveiller", "Peut surveiller", Enseignant.peut_surveiller, "booleen"
        ),
    ),
)


@enseignants.post(
    "",
    response_model=EnseignantLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Recruter un enseignant",
)
async def creer_enseignant(
    donnees: EnseignantCreation,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> Enseignant:
    contexte.exiger("enseignants", Action.CREATE)

    matricule = donnees.matricule
    if not matricule:
        total = int(
            (await session.execute(select(func.count()).select_from(Enseignant))).scalar_one()
        )
        matricule = generer_matricule("ENS", total + 1)

    valeurs = donnees.model_dump(
        exclude={"matieres", "creer_compte", "matricule"}, exclude_unset=True
    )
    enseignant = Enseignant(matricule=matricule, **valeurs)

    if donnees.creer_compte:
        email = donnees.email or f"{matricule.lower()}@enseignant.bj"
        utilisateur = Utilisateur(
            email=email.lower(),
            mot_de_passe=hash_password(generer_mot_de_passe()),
            nom=donnees.nom,
            prenoms=donnees.prenoms,
            sexe=donnees.sexe,
            doit_changer_mot_de_passe=True,
        )
        session.add(utilisateur)
        await session.flush()
        role = (
            await session.execute(select(Role).where(Role.code == RoleCode.TEACHER.value))
        ).scalar_one_or_none()
        if role is not None:
            session.add(
                UtilisateurRole(
                    utilisateur_id=utilisateur.id,
                    role_id=role.id,
                    etablissement_id=donnees.etablissement_principal_id,
                )
            )
        enseignant.utilisateur_id = utilisateur.id

    session.add(enseignant)
    await session.flush()

    for rang, matiere_id in enumerate(donnees.matieres):
        session.add(
            EnseignantMatiere(
                enseignant_id=enseignant.id, matiere_id=matiere_id, principale=rang == 0
            )
        )

    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="enseignants",
        entite_id=enseignant.id,
        entite_libelle=enseignant.nom_complet,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return enseignant


@enseignants.get(
    "/{identifiant}/service",
    summary="Service d'un enseignant",
    description="Établissement, matières enseignées, classes et volume horaire.",
)
async def service_enseignant(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> dict:
    contexte.exiger("enseignants", Action.READ)
    enseignant = await obtenir_ou_404(session, Enseignant, identifiant, "Enseignant")

    stmt = (
        select(EnseignantMatiere)
        .where(EnseignantMatiere.enseignant_id == identifiant)
        .options(selectinload(EnseignantMatiere.matiere))
    )
    matieres = [
        {
            "id": str(lien.matiere.id),
            "code": lien.matiere.code,
            "libelle": lien.matiere.libelle,
            "principale": lien.principale,
        }
        for lien in (await session.execute(stmt)).scalars()
    ]

    stmt = (
        select(Classe)
        .where(Classe.professeur_principal_id == identifiant)
        .options(selectinload(Classe.etablissement))
    )
    classes = [
        {
            "id": str(classe.id),
            "libelle": classe.libelle,
            "effectif": classe.effectif,
            "etablissement": classe.etablissement.nom if classe.etablissement else None,
        }
        for classe in (await session.execute(stmt)).scalars()
    ]

    etablissement = (
        await session.get(Etablissement, enseignant.etablissement_principal_id)
        if enseignant.etablissement_principal_id
        else None
    )

    return {
        "enseignant": {
            "id": str(enseignant.id),
            "matricule": enseignant.matricule,
            "nom_complet": enseignant.nom_complet,
            "grade": enseignant.grade,
            "anciennete_annees": enseignant.anciennete_annees,
        },
        "etablissement": etablissement.nom if etablissement else None,
        "heures_hebdomadaires": enseignant.heures_hebdomadaires,
        "matieres": matieres,
        "classes_principales": classes,
        "aptitudes": {
            "surveillance": enseignant.peut_surveiller,
            "correction": enseignant.peut_corriger,
            "presidence_jury": enseignant.peut_presider_jury,
        },
    }


router.include_router(enseignants)


# ------------------------------------------------------------------
#  Personnels
# ------------------------------------------------------------------

router.include_router(
    creer_routeur_crud(
        modele=Personnel,
        schema_lecture=PersonnelLecture,
        schema_creation=PersonnelEcriture,
        schema_maj=PersonnelEcriture,
        prefixe="/personnels",
        tag="Enseignants",
        ressource="personnels",
        libelle_singulier="agent",
        libelle_pluriel="agents",
        champs_recherche=("nom", "prenoms", "matricule", "fonction"),
        tri_defaut="nom",
        contrainte_unicite="matricule",
        champs_filtrables=(
            DescripteurChamp("matricule", "Matricule", Personnel.matricule),
            DescripteurChamp("nom", "Nom", Personnel.nom),
            DescripteurChamp("categorie", "Catégorie", Personnel.categorie, "liste"),
            DescripteurChamp("fonction", "Fonction", Personnel.fonction),
            DescripteurChamp(
                "etablissement_id", "Établissement", Personnel.etablissement_id, "uuid"
            ),
        ),
    )
)


@router.get(
    "/annees-academiques/courante",
    tags=["Scolarité"],
    summary="Année académique en cours",
)
async def annee_courante(session: SessionDep, contexte: ContexteDep) -> dict:
    contexte.exiger("referentiels", Action.READ)
    annee = (
        await session.execute(
            select(AnneeAcademique)
            .where(AnneeAcademique.courante.is_(True))
            .options(selectinload(AnneeAcademique.periodes))
        )
    ).scalar_one_or_none()
    if annee is None:
        raise NotFoundError("Aucune année académique n'est marquée comme courante.")
    return {
        "id": str(annee.id),
        "code": annee.code,
        "libelle": annee.libelle,
        "date_debut": annee.date_debut.isoformat(),
        "date_fin": annee.date_fin.isoformat(),
        "periodes": [
            {
                "id": str(periode.id),
                "code": periode.code,
                "libelle": periode.libelle,
                "numero": periode.numero,
                "saisie_ouverte": periode.saisie_ouverte,
                "notes_publiees": periode.notes_publiees,
            }
            for periode in sorted(annee.periodes, key=lambda p: p.numero)
        ],
    }
