"""Étape 4 — Enseignants, personnel, apprenants et parents."""

from __future__ import annotations

from datetime import date, timedelta

from app.core.enums import RoleCode, TypeHandicap
from app.core.security import hash_password
from app.models.apprenant import (
    Apprenant,
    ApprenantParent,
    LienParente,
    Parent,
    StatutApprenant,
)
from app.models.identity import Utilisateur, UtilisateurRole
from app.models.personnel import (
    CategoriePersonnel,
    Enseignant,
    EnseignantMatiere,
    EvenementCarriere,
    Personnel,
    SituationAgent,
    StatutAgent,
    TypeEvenementCarriere,
)
from app.seed import scolaire
from app.seed.contexte import ContexteSeed, logger
from app.seed.etape_identite import (
    MOT_DE_PASSE_DEMO,
    construire_affectation,
    construire_utilisateur,
)
from app.utils.codes import generer_identifiant_educatif, generer_matricule

GRADES = (
    "Instituteur adjoint",
    "Instituteur",
    "Professeur adjoint",
    "Professeur certifié",
    "Professeur agrégé",
    "Maître-assistant",
    "Maître de conférences",
)

DIPLOMES_ENSEIGNANT = (
    "BEPC",
    "Baccalauréat",
    "Licence",
    "Master",
    "Doctorat",
    "Certificat d'aptitude pédagogique",
)

PROFESSIONS_PARENT = (
    "Agriculteur",
    "Commerçante",
    "Enseignant",
    "Artisan",
    "Couturière",
    "Chauffeur",
    "Infirmière",
    "Fonctionnaire",
    "Maçon",
    "Mécanicien",
    "Coiffeuse",
    "Pêcheur",
    "Menuisier",
    "Vendeuse",
    "Technicien",
    "Comptable",
    "Éleveur",
    "Restauratrice",
)

NIVEAUX_ALPHABETISATION = (
    "Aucune scolarisation",
    "Primaire",
    "Secondaire",
    "Supérieur",
    "Alphabétisé en langue nationale",
)

#: Répartition des besoins spécifiques dans la population apprenante.
POIDS_HANDICAP = {
    TypeHandicap.AUCUN: 940,
    TypeHandicap.VISUEL: 18,
    TypeHandicap.AUDITIF: 14,
    TypeHandicap.MOTEUR: 13,
    TypeHandicap.COGNITIF: 9,
    TypeHandicap.LANGAGE: 5,
    TypeHandicap.MULTIPLE: 1,
}

AMENAGEMENTS = {
    TypeHandicap.VISUEL: "Sujets en grands caractères ou en braille, tiers temps, secrétaire.",
    TypeHandicap.AUDITIF: (
        "Consignes écrites, interprète en langue des signes, placement au premier rang."
    ),
    TypeHandicap.MOTEUR: "Salle accessible de plain-pied, mobilier adapté, secrétaire.",
    TypeHandicap.COGNITIF: "Énoncés simplifiés, tiers temps, salle au calme.",
    TypeHandicap.LANGAGE: "Épreuves écrites privilégiées, tiers temps.",
    TypeHandicap.MULTIPLE: "Dispositif d'accompagnement individualisé.",
}


async def generer(ctx: ContexteSeed) -> None:
    await _enseignants(ctx)
    await _personnel(ctx)
    await _apprenants_et_parents(ctx)
    logger.info(
        "%d enseignants et %d apprenants générés.",
        len(ctx.cache("enseignant")),
        len(ctx.cache("apprenant")),
    )


# ------------------------------------------------------------------


async def _enseignants(ctx: ContexteSeed) -> None:
    empreinte = hash_password(MOT_DE_PASSE_DEMO)
    codes_etablissements = list(ctx.cache("etablissement_info"))

    enseignants, liens_matieres, carrieres = [], [], []
    utilisateurs, affectations = [], []

    codes_matieres = [code for code, _, _, _, _, _ in scolaire.MATIERES]

    for index in range(1, ctx.volumetrie.enseignants + 1):
        sexe = ctx.sexe(0.34)
        nom, prenoms = ctx.identite(sexe)
        matricule = generer_matricule("ENS", index)
        ident = ctx.nouvel_id()
        code_etablissement = ctx.choix(codes_etablissements)
        etablissement = ctx.cache("etablissement_info")[code_etablissement]

        date_naissance = ctx.date_entre(date(1965, 1, 1), date(1999, 12, 31))
        prise_service = ctx.date_entre(
            max(date(1990, 1, 1), date(date_naissance.year + 23, 1, 1)), date.today()
        )
        statut_agent = ctx.rng.choices(list(StatutAgent), weights=[30, 34, 16, 9, 6, 3, 2])[0]

        email = f"{prenoms.split()[0].lower()}.{nom.lower()}.{index}@enseignant.bj"
        compte = construire_utilisateur(
            ctx,
            email=email,
            nom=nom,
            prenoms=prenoms,
            sexe=sexe,
            empreinte=empreinte,
            date_naissance=date_naissance,
            telephone=ctx.telephone(),
        )
        utilisateurs.append(compte)
        affectations.append(
            construire_affectation(
                ctx,
                compte["id"],
                RoleCode.TEACHER,
                etablissement_id=etablissement["id"],
            )
        )

        specialites = ctx.echantillon(codes_matieres, ctx.entier(1, 2))
        ctx.enregistrer("enseignant", matricule, ident)
        ctx.cache("enseignants_par_etablissement").setdefault(code_etablissement, []).append(
            {
                "id": ident,
                "matricule": matricule,
                "nom_complet": f"{prenoms} {nom}",
                "matieres": specialites,
                "telephone": compte["telephone"],
            }
        )
        for code_matiere in specialites:
            ctx.cache("enseignants_par_matiere").setdefault(code_matiere, []).append(ident)

        enseignants.append(
            {
                "id": ident,
                "matricule": matricule,
                "utilisateur_id": compte["id"],
                "nom": nom,
                "prenoms": prenoms,
                "sexe": sexe,
                "date_naissance": date_naissance,
                "telephone": compte["telephone"],
                "email": email,
                "diplome_le_plus_eleve": ctx.choix(DIPLOMES_ENSEIGNANT),
                "specialite": scolaire.MATIERES[codes_matieres.index(specialites[0])][1],
                "grade": ctx.choix(GRADES),
                "echelon": ctx.entier(1, 12),
                "statut_agent": statut_agent,
                "situation": ctx.rng.choices(list(SituationAgent), weights=[86, 3, 3, 4, 3, 0, 1])[
                    0
                ],
                "date_recrutement": prise_service - timedelta(days=ctx.entier(30, 400)),
                "date_prise_service": prise_service,
                "etablissement_principal_id": etablissement["id"],
                "heures_hebdomadaires": ctx.entier(12, 24),
                "peut_surveiller": ctx.probabilite(0.9),
                "peut_corriger": ctx.probabilite(0.8),
                "peut_presider_jury": ctx.probabilite(0.12),
                "type_handicap": TypeHandicap.AUCUN,
                "supprime": False,
            }
        )

        for rang, code_matiere in enumerate(specialites):
            liens_matieres.append(
                {
                    "id": ctx.nouvel_id(),
                    "enseignant_id": ident,
                    "matiere_id": ctx.recuperer("matiere", code_matiere),
                    "principale": rang == 0,
                }
            )

        carrieres.append(
            {
                "id": ctx.nouvel_id(),
                "enseignant_id": ident,
                "type_evenement": TypeEvenementCarriere.PRISE_SERVICE,
                "libelle": f"Prise de service à {etablissement['nom']}",
                "date_evenement": prise_service,
                "reference_acte": f"Décision n°{ctx.entier(100, 9999)}/DDEPS",
            }
        )
        if ctx.probabilite(0.3):
            carrieres.append(
                {
                    "id": ctx.nouvel_id(),
                    "enseignant_id": ident,
                    "type_evenement": TypeEvenementCarriere.FORMATION,
                    "libelle": "Formation continue en pédagogie active",
                    "date_evenement": ctx.date_entre(prise_service, date.today()),
                    "note_evaluation": round(ctx.rng.uniform(11, 19), 2),
                }
            )

    await ctx.inserer(Utilisateur, utilisateurs)
    await ctx.inserer(UtilisateurRole, affectations)
    await ctx.inserer(Enseignant, enseignants)
    await ctx.inserer(EnseignantMatiere, liens_matieres)
    await ctx.inserer(EvenementCarriere, carrieres)


async def _personnel(ctx: ContexteSeed) -> None:
    """Personnel administratif et technique des établissements."""
    fonctions = {
        CategoriePersonnel.DIRECTION: ("Censeur", "Surveillant général", "Proviseur adjoint"),
        CategoriePersonnel.ADMINISTRATIF: ("Secrétaire", "Économe", "Agent comptable"),
        CategoriePersonnel.SURVEILLANCE: ("Surveillant", "Éducateur"),
        CategoriePersonnel.TECHNIQUE: ("Technicien de laboratoire", "Agent de maintenance"),
        CategoriePersonnel.SANTE: ("Infirmier scolaire",),
        CategoriePersonnel.BIBLIOTHEQUE: ("Documentaliste",),
        CategoriePersonnel.SECURITE: ("Agent de sécurité",),
        CategoriePersonnel.ENTRETIEN: ("Agent d'entretien",),
    }

    lignes = []
    index = 0
    for code_etablissement, info in ctx.cache("etablissement_info").items():
        for categorie, intitules in fonctions.items():
            if not ctx.probabilite(0.45):
                continue
            index += 1
            sexe = ctx.sexe()
            nom, prenoms = ctx.identite(sexe)
            lignes.append(
                {
                    "id": ctx.nouvel_id(),
                    "matricule": generer_matricule("PER", index),
                    "etablissement_id": info["id"],
                    "nom": nom,
                    "prenoms": prenoms,
                    "sexe": sexe,
                    "categorie": categorie,
                    "fonction": ctx.choix(intitules),
                    "statut_agent": ctx.choix(list(StatutAgent)),
                    "situation": SituationAgent.EN_SERVICE,
                    "telephone": ctx.telephone(),
                    "date_prise_service": ctx.date_entre(date(2010, 1, 1), date.today()),
                    "peut_saisir_notes": categorie
                    in {CategoriePersonnel.DIRECTION, CategoriePersonnel.ADMINISTRATIF},
                    "supprime": False,
                }
            )
        ctx.cache("code_etablissement_index")[code_etablissement] = index

    await ctx.inserer(Personnel, lignes)


async def _apprenants_et_parents(ctx: ContexteSeed) -> None:
    """Apprenants, leurs comptes, leurs parents et les liens de parenté."""
    empreinte = hash_password(MOT_DE_PASSE_DEMO)
    annee_courante = date.today().year

    codes_scolaires = [
        code
        for code, info in ctx.cache("etablissement_info").items()
        if info["type"] not in {"CAL", "UNIV", "IUT"}
    ] or list(ctx.cache("etablissement_info"))

    apprenants, parents, liens = [], [], []
    utilisateurs, affectations = [], []

    types_handicap = list(POIDS_HANDICAP)
    poids_handicap = list(POIDS_HANDICAP.values())

    for index in range(1, ctx.volumetrie.apprenants + 1):
        sexe = ctx.sexe(0.485)
        nom, prenoms = ctx.identite(sexe)
        code_etablissement = ctx.choix(codes_scolaires)
        info = ctx.cache("etablissement_info")[code_etablissement]

        handicap = ctx.rng.choices(types_handicap, weights=poids_handicap)[0]
        age = ctx.entier(6, 20)
        date_naissance = date(annee_courante - age, ctx.entier(1, 12), ctx.entier(1, 28))
        identifiant = generer_identifiant_educatif(index, annee_courante)
        ident = ctx.nouvel_id()

        # Un apprenant sur trois dispose d'un compte personnel.
        utilisateur_id = None
        if ctx.probabilite(0.34):
            compte = construire_utilisateur(
                ctx,
                email=f"{identifiant.lower()}@apprenant.bj",
                nom=nom,
                prenoms=prenoms,
                sexe=sexe,
                empreinte=empreinte,
                date_naissance=date_naissance,
                type_handicap=handicap.value,
                mode_simplifie=handicap is not TypeHandicap.AUCUN and ctx.probabilite(0.4),
                lecture_vocale=handicap is TypeHandicap.VISUEL,
                grande_police=handicap is TypeHandicap.VISUEL,
                contraste_eleve=handicap is TypeHandicap.VISUEL and ctx.probabilite(0.7),
            )
            utilisateurs.append(compte)
            affectations.append(
                construire_affectation(
                    ctx, compte["id"], RoleCode.STUDENT, etablissement_id=info["id"]
                )
            )
            utilisateur_id = compte["id"]

        ctx.enregistrer("apprenant", identifiant, ident)
        ctx.cache("apprenants_par_etablissement").setdefault(code_etablissement, []).append(
            {
                "id": ident,
                "identifiant": identifiant,
                "nom": nom,
                "prenoms": prenoms,
                "sexe": sexe,
                "date_naissance": date_naissance,
                "age": age,
                "handicap": handicap,
                "utilisateur_id": utilisateur_id,
            }
        )

        apprenants.append(
            {
                "id": ident,
                "identifiant_educatif": identifiant,
                "matricule": f"MAT{index:07d}",
                "utilisateur_id": utilisateur_id,
                "nom": nom,
                "prenoms": prenoms,
                "sexe": sexe,
                "date_naissance": date_naissance,
                "lieu_naissance": _libelle_commune(info["commune"]),
                "nationalite": "Béninoise",
                "numero_acte_naissance": f"{ctx.entier(1, 9999):04d}/{date_naissance.year}",
                "commune_id": ctx.recuperer("commune", info["commune"]),
                "adresse": f"{_libelle_commune(info['commune'])}, {info['departement']}",
                "telephone": ctx.telephone() if age >= 15 and ctx.probabilite(0.4) else None,
                "etablissement_actuel_id": info["id"],
                "statut": StatutApprenant.ACTIF,
                "langue_principale": "FR",
                "type_handicap": handicap.value,
                "besoins_specifiques": None
                if handicap is TypeHandicap.AUCUN
                else f"Besoin spécifique : {handicap.value.lower()}.",
                "amenagements_examen": AMENAGEMENTS.get(handicap),
                "tiers_temps": handicap is not TypeHandicap.AUCUN and ctx.probabilite(0.75),
                "orphelin": ctx.probabilite(0.04),
                "situation_vulnerable": ctx.probabilite(0.12),
                "supprime": False,
            }
        )

        # Fratries : un apprenant sur quatre rejoint une famille déjà créée dans
        # sa commune, plutôt que de recevoir des parents à lui. Sans cela, le
        # pays comptait autant de familles que d'élèves — aucun frère, aucune
        # sœur — et l'espace d'un parent n'aurait jamais montré qu'un enfant.
        familles = ctx.cache("familles_par_commune").setdefault(info["commune"], [])
        if familles and ctx.probabilite(0.25):
            for id_parent, rang in ctx.choix(familles):
                liens.append(
                    {
                        "id": ctx.nouvel_id(),
                        "apprenant_id": ident,
                        "parent_id": id_parent,
                        "lien": LienParente.PERE if rang == 0 else LienParente.MERE,
                        "contact_principal": rang == 0,
                        "autorise_sortie": True,
                    }
                )
            continue

        # Parents : un ou deux par apprenant.
        contacts = []
        for rang in range(ctx.entier(1, 2)):
            sexe_parent = "MASCULIN" if rang == 0 else "FEMININ"
            nom_parent = nom if ctx.probabilite(0.85) else ctx.identite(sexe_parent)[0]
            prenoms_parent = ctx.identite(sexe_parent)[1]
            id_parent = ctx.nouvel_id()

            compte_parent_id = None
            if rang == 0 and ctx.probabilite(0.22):
                compte_parent = construire_utilisateur(
                    ctx,
                    email=f"parent.{identifiant.lower()}@eduhub.bj",
                    nom=nom_parent,
                    prenoms=prenoms_parent,
                    sexe=sexe_parent,
                    empreinte=empreinte,
                    telephone=ctx.telephone(),
                )
                utilisateurs.append(compte_parent)
                affectations.append(
                    construire_affectation(ctx, compte_parent["id"], RoleCode.PARENT)
                )
                compte_parent_id = compte_parent["id"]

            parents.append(
                {
                    "id": id_parent,
                    "utilisateur_id": compte_parent_id,
                    "nom": nom_parent,
                    "prenoms": prenoms_parent,
                    "sexe": sexe_parent,
                    "profession": ctx.choix(PROFESSIONS_PARENT),
                    "telephone": ctx.telephone(),
                    "adresse": f"{_libelle_commune(info['commune'])}, {info['departement']}",
                    "commune_id": ctx.recuperer("commune", info["commune"]),
                    "niveau_alphabetisation": ctx.choix(NIVEAUX_ALPHABETISATION),
                    "supprime": False,
                }
            )
            contacts.append((id_parent, rang))

        for id_parent, rang in contacts:
            liens.append(
                {
                    "id": ctx.nouvel_id(),
                    "apprenant_id": ident,
                    "parent_id": id_parent,
                    "lien": LienParente.PERE if rang == 0 else LienParente.MERE,
                    "contact_principal": rang == 0,
                    "autorise_sortie": True,
                }
            )

        # La famille devient disponible pour les cadets de la même commune.
        familles.append(contacts)

    await ctx.inserer(Utilisateur, utilisateurs)
    await ctx.inserer(UtilisateurRole, affectations)
    await ctx.inserer(Apprenant, apprenants)
    await ctx.inserer(Parent, parents)
    await ctx.inserer(ApprenantParent, liens)


def _libelle_commune(code_commune: str) -> str:
    from app.seed.donnees import COMMUNES

    code_departement, index = code_commune.split("-")
    return COMMUNES[code_departement][int(index) - 1]
