"""Administration : comptes, rôles, documents, notifications et messagerie."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.crud import creer_routeur_crud, obtenir_ou_404
from app.api.deps import ContexteDep, MetadonneesDep, SessionDep
from app.core.enums import Action, RoleCode
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.security import hash_password
from app.engines import document as moteur_document
from app.engines import notification as moteur_notification
from app.engines.audit import journaliser
from app.engines.identity import ContexteUtilisateur
from app.engines.search import DescripteurChamp
from app.models.identity import Role, Utilisateur, UtilisateurRole
from app.models.systeme import (
    Annonce,
    CanalNotification,
    Message,
    Notification,
    ParametreSysteme,
    TransitionWorkflow,
    TypeNotification,
)
from app.schemas.base import MessageReponse
from app.schemas.identity import (
    AffectationEcriture,
    ReinitialisationMotDePasse,
    RoleLecture,
    UtilisateurCreation,
    UtilisateurDetail,
    UtilisateurLecture,
    UtilisateurMiseAJour,
)
from app.utils.codes import generer_mot_de_passe

router = APIRouter()


# ------------------------------------------------------------------
#  Utilisateurs et rôles
# ------------------------------------------------------------------

utilisateurs = creer_routeur_crud(
    modele=Utilisateur,
    schema_lecture=UtilisateurLecture,
    schema_creation=None,
    schema_maj=UtilisateurMiseAJour,
    prefixe="/utilisateurs",
    tag="Administration",
    ressource="utilisateurs",
    libelle_singulier="utilisateur",
    libelle_pluriel="utilisateurs",
    champs_recherche=("email", "nom", "prenoms", "telephone"),
    tri_defaut="nom",
    contrainte_unicite="email",
    champs_filtrables=(
        DescripteurChamp("email", "Adresse électronique", Utilisateur.email),
        DescripteurChamp("nom", "Nom", Utilisateur.nom),
        DescripteurChamp("prenoms", "Prénoms", Utilisateur.prenoms),
        DescripteurChamp("actif", "Actif", Utilisateur.actif, "booleen"),
        DescripteurChamp("verifie", "Vérifié", Utilisateur.verifie, "booleen"),
        DescripteurChamp("langue", "Langue", Utilisateur.langue, "liste"),
        DescripteurChamp("type_handicap", "Besoin spécifique", Utilisateur.type_handicap, "liste"),
        DescripteurChamp(
            "derniere_connexion", "Dernière connexion", Utilisateur.derniere_connexion, "date"
        ),
    ),
)


@utilisateurs.post(
    "",
    response_model=UtilisateurDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur",
    description=(
        "Crée un compte et lui attribue ses rôles. Sans mot de passe fourni, un mot "
        "de passe provisoire est généré et devra être changé à la première connexion."
    ),
)
async def creer_utilisateur(
    donnees: UtilisateurCreation,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> UtilisateurDetail:
    contexte.exiger("utilisateurs", Action.CREATE)

    email = donnees.email.lower()
    existant = (
        await session.execute(select(Utilisateur).where(Utilisateur.email == email))
    ).scalar_one_or_none()
    if existant is not None:
        raise ConflictError("Cette adresse électronique est déjà utilisée.")

    provisoire = donnees.mot_de_passe is None
    mot_de_passe = donnees.mot_de_passe or generer_mot_de_passe()

    utilisateur = Utilisateur(
        **donnees.model_dump(exclude={"mot_de_passe", "affectations", "email"}),
        email=email,
        mot_de_passe=hash_password(mot_de_passe),
        doit_changer_mot_de_passe=provisoire,
    )
    session.add(utilisateur)
    await session.flush()

    roles = {role.code: role for role in (await session.execute(select(Role))).scalars()}
    for affectation in donnees.affectations:
        role = roles.get(affectation.role_code)
        if role is None:
            raise NotFoundError(
                f"Rôle « {affectation.role_code} » inconnu.",
                details={"roles_disponibles": sorted(roles)},
            )
        # Seul un super administrateur peut conférer le rôle suprême.
        if role.code == RoleCode.SUPER_ADMIN.value and not contexte.est_omnipotent:
            raise PermissionDeniedError("Seul un super administrateur peut attribuer ce rôle.")
        session.add(
            UtilisateurRole(
                utilisateur_id=utilisateur.id,
                role_id=role.id,
                structure_id=affectation.structure_id,
                etablissement_id=affectation.etablissement_id,
                debut=affectation.debut,
                fin=affectation.fin,
            )
        )

    await session.flush()
    await journaliser(
        session,
        action=Action.CREATE,
        entite_type="utilisateurs",
        entite_id=utilisateur.id,
        entite_libelle=utilisateur.email,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )

    detail = UtilisateurDetail.model_validate(utilisateur)
    detail.roles = [affectation.role_code for affectation in donnees.affectations]
    return detail


@utilisateurs.get(
    "/{identifiant}/detail",
    response_model=UtilisateurDetail,
    summary="Compte, rôles et permissions effectives",
)
async def detail_utilisateur(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> UtilisateurDetail:
    contexte.exiger("utilisateurs", Action.READ)
    stmt = (
        select(Utilisateur)
        .where(Utilisateur.id == identifiant)
        .options(
            selectinload(Utilisateur.affectations)
            .selectinload(UtilisateurRole.role)
            .selectinload(Role.permissions)
        )
    )
    utilisateur = (await session.execute(stmt)).scalar_one_or_none()
    if utilisateur is None:
        raise NotFoundError("Utilisateur introuvable.")

    vue = ContexteUtilisateur(utilisateur)
    detail = UtilisateurDetail.model_validate(utilisateur)
    detail.roles = sorted(vue.roles)
    detail.permissions = sorted(vue.permissions)
    detail.niveau_scope = vue.niveau_max
    return detail


@utilisateurs.post(
    "/{identifiant}/roles",
    response_model=MessageReponse,
    summary="Attribuer un rôle",
)
async def attribuer_role(
    identifiant: uuid.UUID,
    donnees: AffectationEcriture,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("roles", Action.ASSIGN)
    await obtenir_ou_404(session, Utilisateur, identifiant, "Utilisateur")

    role = (
        await session.execute(select(Role).where(Role.code == donnees.role_code))
    ).scalar_one_or_none()
    if role is None:
        raise NotFoundError(f"Rôle « {donnees.role_code} » inconnu.")
    if role.code == RoleCode.SUPER_ADMIN.value and not contexte.est_omnipotent:
        raise PermissionDeniedError("Seul un super administrateur peut attribuer ce rôle.")

    existante = (
        await session.execute(
            select(UtilisateurRole).where(
                UtilisateurRole.utilisateur_id == identifiant,
                UtilisateurRole.role_id == role.id,
                UtilisateurRole.structure_id == donnees.structure_id,
                UtilisateurRole.etablissement_id == donnees.etablissement_id,
            )
        )
    ).scalar_one_or_none()
    if existante is not None:
        raise ConflictError("Ce rôle est déjà attribué sur cette portée.")

    session.add(
        UtilisateurRole(
            utilisateur_id=identifiant,
            role_id=role.id,
            structure_id=donnees.structure_id,
            etablissement_id=donnees.etablissement_id,
            debut=donnees.debut,
            fin=donnees.fin,
        )
    )
    await session.flush()
    return MessageReponse(message=f"Rôle « {role.libelle} » attribué.")


@utilisateurs.delete(
    "/{identifiant}/roles/{affectation_id}",
    response_model=MessageReponse,
    summary="Retirer un rôle",
)
async def retirer_role(
    identifiant: uuid.UUID,
    affectation_id: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
) -> MessageReponse:
    contexte.exiger("roles", Action.ASSIGN)
    affectation = await obtenir_ou_404(session, UtilisateurRole, affectation_id, "Affectation")
    if affectation.utilisateur_id != identifiant:
        raise NotFoundError("Cette affectation ne concerne pas l'utilisateur indiqué.")
    await session.delete(affectation)
    return MessageReponse(message="Rôle retiré.")


@utilisateurs.post(
    "/{identifiant}/reinitialiser-mot-de-passe",
    summary="Réinitialiser un mot de passe",
    description="Renvoie le mot de passe provisoire à communiquer à l'utilisateur.",
)
async def reinitialiser(
    identifiant: uuid.UUID,
    donnees: ReinitialisationMotDePasse,
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> dict:
    contexte.exiger("utilisateurs", Action.UPDATE)
    utilisateur = await obtenir_ou_404(session, Utilisateur, identifiant, "Utilisateur")

    mot_de_passe = donnees.nouveau_mot_de_passe or generer_mot_de_passe()
    utilisateur.mot_de_passe = hash_password(mot_de_passe)
    utilisateur.doit_changer_mot_de_passe = donnees.forcer_changement
    utilisateur.tentatives_echouees = 0
    utilisateur.verrouille_jusqu_a = None
    await session.flush()

    await journaliser(
        session,
        action="REINITIALISATION_MOT_DE_PASSE",
        entite_type="utilisateurs",
        entite_id=utilisateur.id,
        entite_libelle=utilisateur.email,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        adresse_ip=metadonnees["adresse_ip"],
    )
    return {
        "message": "Mot de passe réinitialisé.",
        "mot_de_passe_provisoire": mot_de_passe,
        "changement_requis": donnees.forcer_changement,
    }


router.include_router(utilisateurs)

router.include_router(
    creer_routeur_crud(
        modele=Role,
        schema_lecture=RoleLecture,
        schema_creation=None,
        schema_maj=None,
        prefixe="/roles",
        tag="Administration",
        ressource="roles",
        libelle_singulier="rôle",
        libelle_pluriel="rôles",
        champs_recherche=("code", "libelle"),
        tri_defaut="ordre",
        precharger=lambda stmt: stmt.options(selectinload(Role.permissions)),
    )
)


# ------------------------------------------------------------------
#  Documents
# ------------------------------------------------------------------

documents = APIRouter(prefix="/documents", tags=["Documents"])


@documents.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Déposer un document",
    description="Le moteur de documents gère le versionnement et la validation.",
)
async def deposer_document(
    session: SessionDep,
    contexte: ContexteDep,
    fichier: Annotated[UploadFile, File(description="Fichier à déposer")],
    entite_type: Annotated[str, Form()],
    nom: Annotated[str, Form()],
    entite_id: Annotated[uuid.UUID | None, Form()] = None,
    type_document_id: Annotated[uuid.UUID | None, Form()] = None,
    confidentiel: Annotated[bool, Form()] = False,
) -> dict:
    contexte.exiger("documents", Action.CREATE)
    contenu = await fichier.read()

    document = await moteur_document.deposer(
        session,
        entite_type=entite_type,
        entite_id=entite_id,
        nom=nom,
        nom_fichier=fichier.filename or nom,
        contenu=contenu,
        type_mime=fichier.content_type,
        type_document_id=type_document_id,
        proprietaire_id=contexte.id,
        auteur_id=contexte.id,
        confidentiel=confidentiel,
    )
    return {
        "id": str(document.id),
        "reference": document.reference,
        "nom": document.nom,
        "version": document.version,
        "taille_octets": document.taille_octets,
        "statut": document.statut.value,
        "code_verification": document.code_verification,
    }


@documents.get(
    "/entite/{entite_type}/{entite_id}",
    summary="Documents rattachés à une entité",
)
async def documents_entite(
    entite_type: str,
    entite_id: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    toutes_versions: Annotated[bool, Query()] = False,
) -> list[dict]:
    contexte.exiger("documents", Action.READ)
    liste = await moteur_document.lister_par_entite(
        session, entite_type, entite_id, derniere_version_seulement=not toutes_versions
    )
    return [
        {
            "id": str(document.id),
            "reference": document.reference,
            "nom": document.nom,
            "nom_fichier": document.nom_fichier,
            "type_mime": document.type_mime,
            "taille_octets": document.taille_octets,
            "version": document.version,
            "statut": document.statut.value,
            "confidentiel": document.confidentiel,
            "depose_le": document.created_at.isoformat(),
        }
        for document in liste
    ]


@documents.get(
    "/{identifiant}/telecharger",
    summary="Télécharger un document",
    response_class=Response,
)
async def telecharger_document(
    identifiant: uuid.UUID, session: SessionDep, contexte: ContexteDep
) -> Response:
    contexte.exiger("documents", Action.READ)
    document, contenu = await moteur_document.telecharger(session, identifiant)
    return Response(
        content=contenu,
        media_type=document.type_mime or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document.nom_fichier}"'},
    )


@documents.post(
    "/{identifiant}/validation",
    response_model=MessageReponse,
    summary="Valider ou rejeter un document",
)
async def valider_document(
    identifiant: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
    valide: Annotated[bool, Query()],
    commentaire: Annotated[str | None, Query(max_length=1000)] = None,
) -> MessageReponse:
    contexte.exiger("documents", Action.VALIDATE)
    document = await moteur_document.valider(
        session, identifiant, valide=valide, commentaire=commentaire
    )
    return MessageReponse(
        message=f"Document marqué « {document.statut.value} ».",
    )


router.include_router(documents)


# ------------------------------------------------------------------
#  Notifications, messagerie et annonces
# ------------------------------------------------------------------

communication = APIRouter(prefix="/communication", tags=["Communication"])


@communication.get(
    "/notifications",
    summary="Mes notifications",
)
async def mes_notifications(
    session: SessionDep,
    contexte: ContexteDep,
    non_lues_seulement: Annotated[bool, Query()] = False,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    stmt = (
        select(Notification)
        .where(Notification.destinataire_id == contexte.id)
        .order_by(Notification.priorite.desc(), Notification.created_at.desc())
        .limit(limite)
    )
    if non_lues_seulement:
        stmt = stmt.where(Notification.lue.is_(False))

    notifications = list((await session.execute(stmt)).scalars())
    non_lues = await moteur_notification.compter_non_lues(session, contexte.id)

    return {
        "non_lues": non_lues,
        "notifications": [
            {
                "id": str(notification.id),
                "type": notification.type_notification.value,
                "titre": notification.titre,
                "message": notification.message,
                "message_simplifie": notification.message_simplifie,
                "pictogramme": notification.pictogramme,
                "priorite": notification.priorite,
                "lien": notification.lien,
                "lue": notification.lue,
                "date": notification.created_at.isoformat(),
            }
            for notification in notifications
        ],
    }


@communication.post(
    "/notifications/marquer-lues",
    response_model=MessageReponse,
    summary="Marquer des notifications comme lues",
)
async def marquer_lues(
    session: SessionDep,
    contexte: ContexteDep,
    identifiants: list[uuid.UUID] | None = None,
) -> MessageReponse:
    total = await moteur_notification.marquer_lues(session, contexte.id, identifiants)
    return MessageReponse(message="Notifications mises à jour.", details={"traitees": total})


@communication.post(
    "/notifications",
    response_model=MessageReponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adresser une notification",
)
async def envoyer_notification(
    session: SessionDep,
    contexte: ContexteDep,
    destinataire_id: Annotated[uuid.UUID, Query()],
    titre: Annotated[str, Query(min_length=1, max_length=255)],
    message: Annotated[str, Query(min_length=1)],
    type_notification: Annotated[TypeNotification, Query()] = TypeNotification.INFORMATION,
    canal: Annotated[CanalNotification, Query()] = CanalNotification.APPLICATION,
) -> MessageReponse:
    contexte.exiger("notifications", Action.CREATE)
    await moteur_notification.notifier(
        session,
        destinataire_id=destinataire_id,
        type_notification=type_notification,
        titre=titre,
        message=message,
        canal=canal,
    )
    return MessageReponse(message="Notification envoyée.")


@communication.get(
    "/messages",
    summary="Ma messagerie",
)
async def messagerie(
    session: SessionDep,
    contexte: ContexteDep,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict]:
    stmt = (
        select(Message)
        .where(
            or_(
                Message.destinataire_id == contexte.id,
                Message.expediteur_id == contexte.id,
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limite)
    )
    return [
        {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "objet": message.objet,
            "corps": message.corps,
            "recu": message.destinataire_id == contexte.id,
            "lu": message.lu,
            "date": message.created_at.isoformat(),
        }
        for message in (await session.execute(stmt)).scalars()
    ]


@communication.post(
    "/messages",
    response_model=MessageReponse,
    status_code=status.HTTP_201_CREATED,
    summary="Envoyer un message",
)
async def envoyer_message(
    session: SessionDep,
    contexte: ContexteDep,
    destinataire_id: Annotated[uuid.UUID, Query()],
    corps: Annotated[str, Query(min_length=1)],
    objet: Annotated[str | None, Query(max_length=255)] = None,
    conversation_id: Annotated[uuid.UUID | None, Query()] = None,
) -> MessageReponse:
    await obtenir_ou_404(session, Utilisateur, destinataire_id, "Destinataire")
    message = Message(
        conversation_id=conversation_id or uuid.uuid4(),
        expediteur_id=contexte.id,
        destinataire_id=destinataire_id,
        objet=objet,
        corps=corps,
    )
    session.add(message)
    await session.flush()
    return MessageReponse(
        message="Message envoyé.", details={"conversation_id": str(message.conversation_id)}
    )


@communication.get(
    "/annonces",
    summary="Annonces publiées",
)
async def annonces(
    session: SessionDep,
    contexte: ContexteDep,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict]:
    from datetime import date

    stmt = (
        select(Annonce)
        .where(
            Annonce.publiee.is_(True),
            or_(Annonce.date_expiration.is_(None), Annonce.date_expiration >= date.today()),
        )
        .order_by(Annonce.urgente.desc(), Annonce.date_publication.desc())
        .limit(limite)
    )
    return [
        {
            "id": str(annonce.id),
            "titre": annonce.titre,
            "contenu": annonce.contenu,
            "contenu_simplifie": annonce.contenu_simplifie,
            "urgente": annonce.urgente,
            "date_publication": annonce.date_publication.isoformat(),
            "nombre_vues": annonce.nombre_vues,
        }
        for annonce in (await session.execute(stmt)).scalars()
    ]


router.include_router(communication)


# ------------------------------------------------------------------
#  Paramètres et historique des workflows
# ------------------------------------------------------------------


@router.get(
    "/parametres",
    tags=["Administration"],
    summary="Paramètres du système",
)
async def parametres(
    session: SessionDep,
    contexte: ContexteDep,
    categorie: Annotated[str | None, Query()] = None,
) -> list[dict]:
    contexte.exiger("parametres", Action.READ)
    stmt = select(ParametreSysteme).order_by(ParametreSysteme.categorie, ParametreSysteme.cle)
    if categorie:
        stmt = stmt.where(ParametreSysteme.categorie == categorie)
    return [
        {
            "cle": parametre.cle,
            "libelle": parametre.libelle,
            "valeur": parametre.valeur,
            "type": parametre.type_valeur,
            "categorie": parametre.categorie,
            "modifiable": parametre.modifiable,
            "description": parametre.description,
        }
        for parametre in (await session.execute(stmt)).scalars()
    ]


@router.patch(
    "/parametres/{cle}",
    tags=["Administration"],
    response_model=MessageReponse,
    summary="Modifier un paramètre",
)
async def modifier_parametre(
    cle: str,
    valeur: Annotated[str, Query(min_length=1)],
    session: SessionDep,
    contexte: ContexteDep,
    metadonnees: MetadonneesDep,
) -> MessageReponse:
    contexte.exiger("parametres", Action.UPDATE)
    parametre = (
        await session.execute(select(ParametreSysteme).where(ParametreSysteme.cle == cle))
    ).scalar_one_or_none()
    if parametre is None:
        raise NotFoundError(f"Paramètre « {cle} » inconnu.")
    if not parametre.modifiable:
        raise PermissionDeniedError("Ce paramètre n'est pas modifiable.")

    ancienne = parametre.valeur
    parametre.valeur = valeur
    await session.flush()

    await journaliser(
        session,
        action=Action.UPDATE,
        entite_type="parametres",
        entite_id=parametre.id,
        entite_libelle=cle,
        utilisateur_id=contexte.id,
        utilisateur_email=contexte.email,
        valeurs_avant={"valeur": ancienne},
        valeurs_apres={"valeur": valeur},
        adresse_ip=metadonnees["adresse_ip"],
    )
    return MessageReponse(message=f"Paramètre « {cle} » mis à jour.")


@router.get(
    "/workflows/{entite_type}/{entite_id}/historique",
    tags=["Administration"],
    summary="Historique des transitions d'une entité",
)
async def historique_workflow(
    entite_type: str,
    entite_id: uuid.UUID,
    session: SessionDep,
    contexte: ContexteDep,
) -> list[dict]:
    contexte.exiger("audit", Action.READ)
    stmt = (
        select(TransitionWorkflow)
        .where(
            TransitionWorkflow.entite_type == entite_type,
            TransitionWorkflow.entite_id == entite_id,
        )
        .order_by(TransitionWorkflow.created_at)
    )
    return [
        {
            "date": transition.created_at.isoformat(),
            "workflow": transition.workflow,
            "action": transition.action,
            "statut_avant": transition.statut_avant,
            "statut_apres": transition.statut_apres,
            "acteur": transition.acteur_nom,
            "commentaire": transition.commentaire,
        }
        for transition in (await session.execute(stmt)).scalars()
    ]


@router.get(
    "/statistiques/comptes",
    tags=["Administration"],
    summary="Répartition des comptes par rôle",
)
async def statistiques_comptes(session: SessionDep, contexte: ContexteDep) -> dict:
    contexte.exiger("utilisateurs", Action.READ)

    stmt = (
        select(Role.code, Role.libelle, func.count(UtilisateurRole.id))
        .outerjoin(UtilisateurRole, UtilisateurRole.role_id == Role.id)
        .group_by(Role.code, Role.libelle)
        .order_by(func.count(UtilisateurRole.id).desc())
    )
    par_role = [
        {"code": code, "libelle": libelle, "comptes": total}
        for code, libelle, total in (await session.execute(stmt)).all()
    ]

    total = int(
        (
            await session.execute(
                select(func.count()).select_from(Utilisateur).where(Utilisateur.supprime.is_(False))
            )
        ).scalar_one()
    )
    actifs = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Utilisateur)
                .where(Utilisateur.supprime.is_(False), Utilisateur.actif.is_(True))
            )
        ).scalar_one()
    )
    connectes = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Utilisateur)
                .where(Utilisateur.derniere_connexion.isnot(None))
            )
        ).scalar_one()
    )

    return {
        "total": total,
        "actifs": actifs,
        "inactifs": total - actifs,
        "deja_connectes": connectes,
        "par_role": par_role,
        "calcule_le": datetime.now(UTC).isoformat(),
    }
