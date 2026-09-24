"""Étape 2 — Rôles, permissions, structures institutionnelles et comptes."""

from __future__ import annotations

from app.core.enums import Action, NiveauScope, RoleCode
from app.core.security import hash_password
from app.models.identity import Permission, Role, Utilisateur, UtilisateurRole, role_permission
from app.models.organisation import CategorieStructure, Structure
from app.seed import donnees
from app.seed.contexte import ContexteSeed, logger

#: Mot de passe commun à tous les comptes de démonstration.
MOT_DE_PASSE_DEMO = "EduHub2026!"

#: Ressources protégées de la plateforme.
RESSOURCES: tuple[tuple[str, str], ...] = (
    ("utilisateurs", "Utilisateurs et comptes"),
    ("roles", "Rôles et permissions"),
    ("structures", "Structures institutionnelles"),
    ("referentiels", "Référentiels et nomenclatures"),
    ("etablissements", "Établissements"),
    ("infrastructures", "Bâtiments, salles et équipements"),
    ("apprenants", "Apprenants"),
    ("parents", "Parents et tuteurs"),
    ("enseignants", "Enseignants"),
    ("personnels", "Personnel non enseignant"),
    ("classes", "Classes"),
    ("inscriptions", "Inscriptions et transferts"),
    ("emploi_du_temps", "Emploi du temps"),
    ("presences", "Présences et assiduité"),
    ("evaluations", "Évaluations"),
    ("notes", "Notes"),
    ("bulletins", "Bulletins"),
    ("conseils", "Conseils de classe"),
    ("examens", "Examens et concours"),
    ("sessions", "Sessions d'examen"),
    ("candidats", "Candidats"),
    ("centres", "Centres de composition"),
    ("surveillance", "Surveillants et chefs de centre"),
    ("correcteurs", "Correcteurs"),
    ("copies", "Copies"),
    ("jurys", "Jurys et délibérations"),
    ("resultats", "Résultats d'examen"),
    ("contentieux", "Contentieux"),
    ("budget", "Budget et comptabilité"),
    ("archives", "Banque d'épreuves et archives"),
    ("diplomes", "Diplômes et attestations"),
    ("orientation", "Orientation et affectation"),
    ("bourses", "Bourses et aides sociales"),
    ("transport", "Transport"),
    ("logement", "Logement"),
    ("restauration", "Restauration"),
    ("sante", "Santé scolaire"),
    ("bibliotheque", "Bibliothèque"),
    ("apprentissage", "Cours et ressources pédagogiques"),
    ("projets", "Projets collaboratifs"),
    ("recherche", "Recherche et publications"),
    ("stages", "Stages"),
    ("emploi", "Offres et candidatures"),
    ("entreprises", "Entreprises partenaires"),
    ("documents", "Documents"),
    ("notifications", "Notifications et messages"),
    ("analytics", "Statistiques et tableaux de bord"),
    ("recherche_avancee", "Recherche avancée et requêtes"),
    ("rapports", "Rapports"),
    ("audit", "Journal d'audit"),
    ("parametres", "Paramètres du système"),
)

_LECTURE = (Action.READ,)
_GESTION = (Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE)
_VALIDATION = (Action.VALIDATE, Action.APPROVE, Action.REJECT)
_DIFFUSION = (Action.PUBLISH, Action.EXPORT, Action.PRINT)

#: Droits accordés à chaque rôle : ressource → actions.
MATRICE: dict[RoleCode, dict[str, tuple[Action, ...]]] = {
    RoleCode.MINISTRY_ADMIN: {
        "utilisateurs": _GESTION,
        "roles": _LECTURE,
        "structures": _GESTION,
        "referentiels": _GESTION,
        "etablissements": _GESTION + _VALIDATION,
        "apprenants": _LECTURE + _DIFFUSION,
        "enseignants": _GESTION,
        "examens": _GESTION + _VALIDATION + _DIFFUSION,
        "sessions": _GESTION + _VALIDATION,
        "resultats": _LECTURE + _DIFFUSION,
        "budget": _GESTION + _VALIDATION,
        "analytics": _LECTURE + _DIFFUSION,
        "recherche_avancee": _LECTURE + _DIFFUSION,
        "rapports": _GESTION + _DIFFUSION,
        "audit": _LECTURE,
        "parametres": _GESTION,
        "orientation": _GESTION,
        "bourses": _GESTION + _VALIDATION,
    },
    RoleCode.DIRECTOR_ADMIN: {
        "utilisateurs": _GESTION,
        "structures": _LECTURE,
        "referentiels": _GESTION,
        "etablissements": _LECTURE + (Action.UPDATE,),
        "examens": _GESTION + _VALIDATION + _DIFFUSION,
        "sessions": _GESTION + _VALIDATION + _DIFFUSION,
        "candidats": _GESTION + _VALIDATION,
        "centres": _GESTION + (Action.ASSIGN,),
        "surveillance": _GESTION + (Action.ASSIGN,),
        "correcteurs": _GESTION + (Action.ASSIGN,),
        "copies": _GESTION,
        "jurys": _GESTION + _VALIDATION,
        "resultats": _GESTION + _VALIDATION + _DIFFUSION,
        "contentieux": _GESTION + _VALIDATION,
        "budget": _GESTION,
        "archives": _GESTION + (Action.ARCHIVE,),
        "diplomes": _GESTION + _DIFFUSION,
        "documents": _GESTION + _VALIDATION,
        "analytics": _LECTURE + _DIFFUSION,
        "rapports": _GESTION + _DIFFUSION,
    },
    RoleCode.DEPARTMENT_ADMIN: {
        "utilisateurs": _GESTION,
        "etablissements": _LECTURE + (Action.UPDATE,),
        "apprenants": _LECTURE,
        "enseignants": _LECTURE + (Action.UPDATE,),
        "candidats": _GESTION + _VALIDATION,
        "centres": _GESTION,
        "surveillance": _GESTION,
        "copies": _LECTURE + (Action.UPDATE,),
        "resultats": _LECTURE + _DIFFUSION,
        "documents": _LECTURE + _VALIDATION,
        "analytics": _LECTURE,
        "rapports": _LECTURE + _DIFFUSION,
    },
    RoleCode.EXAM_ADMIN: {
        "examens": _GESTION,
        "sessions": _GESTION,
        "candidats": _GESTION + _VALIDATION,
        "centres": _GESTION + (Action.ASSIGN,),
        "surveillance": _GESTION + (Action.ASSIGN,),
        "correcteurs": _GESTION + (Action.ASSIGN,),
        "copies": _GESTION,
        "jurys": _GESTION,
        "resultats": _GESTION + _DIFFUSION,
        "contentieux": _GESTION,
        "archives": _GESTION,
        "documents": _LECTURE + _VALIDATION,
    },
    RoleCode.SCHOOL_ADMIN: {
        "utilisateurs": (Action.CREATE, Action.READ, Action.UPDATE),
        "etablissements": _LECTURE + (Action.UPDATE,),
        "infrastructures": _GESTION,
        "apprenants": _GESTION,
        "parents": _GESTION,
        "enseignants": _LECTURE + (Action.CREATE, Action.UPDATE),
        "personnels": _GESTION,
        "classes": _GESTION,
        "inscriptions": _GESTION + _VALIDATION,
        "emploi_du_temps": _GESTION,
        "presences": _LECTURE,
        "evaluations": _LECTURE + _VALIDATION,
        "notes": _LECTURE + _VALIDATION,
        "bulletins": _GESTION + _DIFFUSION,
        "conseils": _GESTION,
        "candidats": (Action.CREATE, Action.READ, Action.UPDATE),
        "surveillance": (Action.CREATE, Action.READ),
        "correcteurs": (Action.CREATE, Action.READ),
        "resultats": _LECTURE + _DIFFUSION,
        "documents": _GESTION,
        "analytics": _LECTURE,
        "rapports": _LECTURE + _DIFFUSION,
        "bibliotheque": _GESTION,
        "transport": _LECTURE,
    },
    RoleCode.SCHOOL_STAFF: {
        "apprenants": _LECTURE + (Action.UPDATE,),
        "parents": _LECTURE,
        "classes": _LECTURE,
        "inscriptions": (Action.CREATE, Action.READ, Action.UPDATE),
        "presences": _GESTION,
        "notes": _LECTURE,
        "bulletins": _LECTURE + (Action.PRINT,),
        "documents": (Action.CREATE, Action.READ),
    },
    RoleCode.TEACHER: {
        "classes": _LECTURE,
        "apprenants": _LECTURE,
        "emploi_du_temps": _LECTURE,
        "presences": _GESTION,
        "evaluations": _GESTION,
        "notes": _GESTION,
        "bulletins": _LECTURE,
        "conseils": _LECTURE,
        "apprentissage": _GESTION,
        "projets": _GESTION,
        "bibliotheque": _LECTURE,
        "documents": (Action.CREATE, Action.READ),
        "analytics": _LECTURE,
    },
    RoleCode.STUDENT: {
        "apprenants": _LECTURE,
        "classes": _LECTURE,
        "emploi_du_temps": _LECTURE,
        "presences": _LECTURE,
        "notes": _LECTURE,
        "bulletins": _LECTURE + (Action.PRINT,),
        "resultats": _LECTURE + (Action.PRINT,),
        "diplomes": _LECTURE + (Action.PRINT,),
        "orientation": (Action.CREATE, Action.READ, Action.UPDATE),
        "bourses": (Action.CREATE, Action.READ, Action.UPDATE),
        "transport": _LECTURE + (Action.CREATE,),
        "logement": _LECTURE + (Action.CREATE,),
        "bibliotheque": _LECTURE,
        "apprentissage": _LECTURE,
        "projets": (Action.CREATE, Action.READ, Action.UPDATE),
        "stages": (Action.CREATE, Action.READ),
        "emploi": (Action.CREATE, Action.READ),
        "documents": (Action.CREATE, Action.READ),
        "notifications": _LECTURE,
    },
    RoleCode.PARENT: {
        "apprenants": _LECTURE,
        "presences": _LECTURE,
        "notes": _LECTURE,
        "bulletins": _LECTURE + (Action.PRINT,),
        "resultats": _LECTURE,
        "inscriptions": _LECTURE,
        "notifications": _LECTURE,
        "documents": _LECTURE,
        "transport": _LECTURE,
    },
    RoleCode.CANDIDATE: {
        "candidats": (Action.CREATE, Action.READ, Action.UPDATE),
        "documents": (Action.CREATE, Action.READ),
        "resultats": _LECTURE + (Action.PRINT,),
        "centres": _LECTURE,
        "diplomes": _LECTURE + (Action.PRINT,),
        "contentieux": (Action.CREATE, Action.READ),
        "notifications": _LECTURE,
    },
    RoleCode.CORRECTOR: {
        "copies": _LECTURE + (Action.UPDATE,),
        "correcteurs": _LECTURE,
        "archives": _LECTURE,
        "notifications": _LECTURE,
    },
    RoleCode.INVIGILATOR: {
        "surveillance": _LECTURE,
        "candidats": _LECTURE,
        "centres": _LECTURE,
        "notifications": _LECTURE,
    },
    RoleCode.JURY_MEMBER: {
        "jurys": _LECTURE + (Action.UPDATE,),
        "resultats": _LECTURE + _VALIDATION,
        "notifications": _LECTURE,
    },
    RoleCode.RESEARCHER: {
        "recherche": _GESTION,
        "projets": _GESTION,
        "apprentissage": _LECTURE,
        "analytics": _LECTURE,
        "bibliotheque": _LECTURE,
    },
    RoleCode.COMPANY: {
        "entreprises": _LECTURE + (Action.UPDATE,),
        "emploi": _GESTION,
        "stages": _GESTION,
        "projets": _LECTURE + (Action.CREATE,),
    },
    RoleCode.PARTNER: {
        "projets": _LECTURE + (Action.CREATE,),
        "bourses": _LECTURE + (Action.CREATE,),
        "analytics": _LECTURE,
    },
    RoleCode.TRANSPORT_MANAGER: {"transport": _GESTION, "notifications": (Action.CREATE,)},
    RoleCode.LIBRARIAN: {"bibliotheque": _GESTION, "apprentissage": _LECTURE},
    RoleCode.HEALTH_WORKER: {"sante": _GESTION, "apprenants": _LECTURE},
    RoleCode.FINANCE_MANAGER: {
        "budget": _GESTION + _VALIDATION,
        "bourses": _LECTURE + _VALIDATION,
        "rapports": _LECTURE + _DIFFUSION,
    },
}

#: Portée institutionnelle de chaque rôle.
PORTEES: dict[RoleCode, NiveauScope] = {
    RoleCode.SUPER_ADMIN: NiveauScope.NATIONAL,
    RoleCode.MINISTRY_ADMIN: NiveauScope.MINISTERE,
    RoleCode.DIRECTOR_ADMIN: NiveauScope.DIRECTION,
    RoleCode.EXAM_ADMIN: NiveauScope.DIRECTION,
    RoleCode.DEPARTMENT_ADMIN: NiveauScope.DEPARTEMENT,
    RoleCode.SCHOOL_ADMIN: NiveauScope.ETABLISSEMENT,
    RoleCode.SCHOOL_STAFF: NiveauScope.ETABLISSEMENT,
    RoleCode.TEACHER: NiveauScope.ETABLISSEMENT,
    RoleCode.LIBRARIAN: NiveauScope.ETABLISSEMENT,
    RoleCode.HEALTH_WORKER: NiveauScope.ETABLISSEMENT,
    RoleCode.TRANSPORT_MANAGER: NiveauScope.DEPARTEMENT,
    RoleCode.FINANCE_MANAGER: NiveauScope.DIRECTION,
}

LIBELLES_ROLES: dict[RoleCode, str] = {
    RoleCode.SUPER_ADMIN: "Super administrateur",
    RoleCode.MINISTRY_ADMIN: "Administrateur ministériel",
    RoleCode.DIRECTOR_ADMIN: "Administrateur de direction",
    RoleCode.DEPARTMENT_ADMIN: "Administrateur départemental",
    RoleCode.EXAM_ADMIN: "Administrateur des examens",
    RoleCode.SCHOOL_ADMIN: "Administrateur d'établissement",
    RoleCode.SCHOOL_STAFF: "Personnel administratif",
    RoleCode.TEACHER: "Enseignant",
    RoleCode.STUDENT: "Apprenant",
    RoleCode.PARENT: "Parent ou tuteur",
    RoleCode.CANDIDATE: "Candidat",
    RoleCode.CORRECTOR: "Correcteur",
    RoleCode.INVIGILATOR: "Surveillant",
    RoleCode.JURY_MEMBER: "Membre de jury",
    RoleCode.RESEARCHER: "Chercheur",
    RoleCode.COMPANY: "Entreprise partenaire",
    RoleCode.PARTNER: "Partenaire",
    RoleCode.TRANSPORT_MANAGER: "Gestionnaire de transport",
    RoleCode.LIBRARIAN: "Bibliothécaire",
    RoleCode.HEALTH_WORKER: "Agent de santé scolaire",
    RoleCode.FINANCE_MANAGER: "Gestionnaire financier",
}


async def generer(ctx: ContexteSeed) -> None:
    await _permissions(ctx)
    await _roles(ctx)
    await _structures(ctx)
    logger.info("Rôles, permissions et structures institutionnelles générés.")


async def _permissions(ctx: ContexteSeed) -> None:
    lignes = []
    for rang, (ressource, libelle) in enumerate(RESSOURCES):
        for action in Action:
            code = f"{ressource}:{action.value}"
            ident = ctx.enregistrer("permission", code, ctx.nouvel_id())
            lignes.append(
                {
                    "id": ident,
                    "code": code,
                    "libelle": f"{libelle} — {action.value}",
                    "ressource": ressource,
                    "action": action,
                    "actif": True,
                    "ordre": rang,
                }
            )
    await ctx.inserer(Permission, lignes)


async def _roles(ctx: ContexteSeed) -> None:
    roles, liens = [], []
    for rang, code_role in enumerate(RoleCode):
        ident = ctx.enregistrer("role", code_role.value, ctx.nouvel_id())
        roles.append(
            {
                "id": ident,
                "code": code_role.value,
                "libelle": LIBELLES_ROLES[code_role],
                "description": f"Rôle « {LIBELLES_ROLES[code_role]} » de la plateforme EduHub.",
                "niveau_scope": PORTEES.get(code_role, NiveauScope.PERSONNEL),
                "systeme": True,
                "actif": True,
                "ordre": rang,
            }
        )

        if code_role is RoleCode.SUPER_ADMIN:
            # Le super administrateur reçoit l'intégralité des permissions.
            attributions = {ressource: tuple(Action) for ressource, _ in RESSOURCES}
        else:
            attributions = MATRICE.get(code_role, {})

        for ressource, actions in attributions.items():
            for action in dict.fromkeys(actions):
                permission_id = ctx.recuperer("permission", f"{ressource}:{action.value}")
                if permission_id:
                    liens.append({"role_id": ident, "permission_id": permission_id})

    await ctx.inserer(Role, roles)
    await ctx.inserer(role_permission, liens)


async def _structures(ctx: ContexteSeed) -> None:
    """Chaîne ministère → direction → direction départementale."""
    structures = []

    for rang, (code, sigle, libelle) in enumerate(donnees.MINISTERES):
        ident = ctx.enregistrer("structure", code, ctx.nouvel_id())
        structures.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "sigle": sigle,
                "categorie": CategorieStructure.MINISTERE,
                "niveau_scope": NiveauScope.MINISTERE,
                "parent_id": None,
                "email": f"contact@{code.lower()}.gouv.bj",
                "telephone": ctx.telephone(),
                "adresse": "Cotonou, Bénin",
                "missions": f"Pilotage national — {libelle}.",
                "actif": True,
                "supprime": False,
                "ordre": rang,
            }
        )

    for rang, (code, sigle, libelle, code_ministere, categorie) in enumerate(donnees.DIRECTIONS):
        ident = ctx.enregistrer("structure", code, ctx.nouvel_id())
        structures.append(
            {
                "id": ident,
                "code": code,
                "libelle": libelle,
                "sigle": sigle,
                "categorie": CategorieStructure(categorie),
                "niveau_scope": NiveauScope.DIRECTION,
                "parent_id": ctx.recuperer("structure", code_ministere),
                "email": f"contact@{code.lower().replace('/', '-')}.gouv.bj",
                "telephone": ctx.telephone(),
                "adresse": "Porto-Novo, Bénin",
                "missions": f"Organisation des examens et concours — {libelle}.",
                "actif": True,
                "supprime": False,
                "ordre": rang,
            }
        )

    # Une direction départementale par département, rattachée au MESFTP.
    parent_ddeps = ctx.recuperer("structure", "MESFTP")
    for rang, (code_departement, libelle, _, _, _) in enumerate(donnees.DEPARTEMENTS):
        code = f"DDEPS-{code_departement}"
        ident = ctx.enregistrer("structure", code, ctx.nouvel_id())
        ctx.cache("ddeps_par_departement")[code_departement] = ident
        structures.append(
            {
                "id": ident,
                "code": code,
                "libelle": f"Direction départementale des enseignements — {libelle}",
                "sigle": f"DDEPS/{code_departement}",
                "categorie": CategorieStructure.DIRECTION_DEPARTEMENTALE,
                "niveau_scope": NiveauScope.DEPARTEMENT,
                "parent_id": parent_ddeps,
                "departement_id": ctx.recuperer("departement", code_departement),
                "email": f"ddeps.{code_departement.lower()}@education.bj",
                "telephone": ctx.telephone(),
                "actif": True,
                "supprime": False,
                "ordre": rang,
            }
        )

    await ctx.inserer(Structure, structures)


def construire_utilisateur(
    ctx: ContexteSeed,
    *,
    email: str,
    nom: str,
    prenoms: str,
    sexe: str | None = None,
    mot_de_passe: str = MOT_DE_PASSE_DEMO,
    empreinte: str | None = None,
    **extra,
) -> dict:
    """Prépare la ligne d'insertion d'un compte utilisateur."""
    ligne = {
        "id": ctx.nouvel_id(),
        "email": email.lower(),
        "mot_de_passe": empreinte or hash_password(mot_de_passe),
        "nom": nom,
        "prenoms": prenoms,
        "sexe": sexe,
        "actif": True,
        "verifie": True,
        "doit_changer_mot_de_passe": False,
        "tentatives_echouees": 0,
        "nationalite": "Béninoise",
        "langue": "FR",
        "type_handicap": "AUCUN",
        "mode_simplifie": False,
        "contraste_eleve": False,
        "grande_police": False,
        "lecture_vocale": False,
        "supprime": False,
    }
    ligne.update(extra)
    return ligne


def construire_affectation(
    ctx: ContexteSeed,
    utilisateur_id,
    code_role: RoleCode | str,
    *,
    structure_id=None,
    etablissement_id=None,
) -> dict:
    """Prépare la ligne d'affectation d'un rôle à un utilisateur."""
    code = code_role.value if isinstance(code_role, RoleCode) else code_role
    return {
        "id": ctx.nouvel_id(),
        "utilisateur_id": utilisateur_id,
        "role_id": ctx.recuperer("role", code),
        "structure_id": structure_id,
        "etablissement_id": etablissement_id,
        "actif": True,
    }


async def generer_comptes_administration(ctx: ContexteSeed) -> None:
    """Comptes de démonstration de la chaîne administrative."""
    empreinte = hash_password(MOT_DE_PASSE_DEMO)
    utilisateurs, affectations = [], []

    def ajouter(email, nom, prenoms, role, sexe="MASCULIN", **portee):
        ligne = construire_utilisateur(
            ctx, email=email, nom=nom, prenoms=prenoms, sexe=sexe, empreinte=empreinte
        )
        utilisateurs.append(ligne)
        affectations.append(construire_affectation(ctx, ligne["id"], role, **portee))
        ctx.enregistrer("compte_demo", email, ligne["id"])
        return ligne["id"]

    ajouter("super.admin@eduhub.bj", "VISSEHO", "Avent", RoleCode.SUPER_ADMIN)
    ajouter(
        "demo@education.local",
        "DEMONSTRATION",
        "Compte",
        RoleCode.SUPER_ADMIN,
        sexe="FEMININ",
    )

    for code, sigle, _ in donnees.MINISTERES:
        structure_id = ctx.recuperer("structure", code)
        nom, prenoms = ctx.identite("MASCULIN")
        ajouter(
            f"admin.{code.lower()}@eduhub.bj",
            nom,
            prenoms,
            RoleCode.MINISTRY_ADMIN,
            structure_id=structure_id,
        )
        ctx.cache("sigle_ministere")[code] = sigle

    for code, _, _, _, _ in donnees.DIRECTIONS:
        structure_id = ctx.recuperer("structure", code)
        nom, prenoms = ctx.identite("FEMININ")
        alias = code.lower().replace("-", ".")
        ajouter(
            f"admin.{alias}@eduhub.bj",
            nom,
            prenoms,
            RoleCode.DIRECTOR_ADMIN,
            sexe="FEMININ",
            structure_id=structure_id,
        )
        nom, prenoms = ctx.identite("MASCULIN")
        ajouter(
            f"examens.{alias}@eduhub.bj",
            nom,
            prenoms,
            RoleCode.EXAM_ADMIN,
            structure_id=structure_id,
        )

    # Alias attendus par la documentation.
    ctx.cache("alias_comptes")["admin.dec@eduhub.bj"] = "admin.dec.memp@eduhub.bj"

    for code_departement, libelle, _, _, _ in donnees.DEPARTEMENTS:
        structure_id = ctx.cache("ddeps_par_departement")[code_departement]
        sexe = ctx.sexe()
        nom, prenoms = ctx.identite(sexe)
        alias = libelle.lower().replace(" ", "-").replace("é", "e").replace("è", "e")
        ajouter(
            f"admin.ddeps.{alias}@eduhub.bj",
            nom,
            prenoms,
            RoleCode.DEPARTMENT_ADMIN,
            sexe=sexe,
            structure_id=structure_id,
        )

    await ctx.inserer(Utilisateur, utilisateurs)
    await ctx.inserer(UtilisateurRole, affectations)
