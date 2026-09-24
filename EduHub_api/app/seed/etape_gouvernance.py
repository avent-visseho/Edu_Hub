"""Étape 9 — Gouvernance : indicateurs, règles, alertes, requêtes et notifications."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select

from app.models.apprenant import Apprenant
from app.models.etablissement import Etablissement
from app.models.evaluation import Bulletin
from app.models.examen import DecisionExamen, ResultatExamen, SessionExamen
from app.models.personnel import Enseignant
from app.models.scolarite import Classe, Inscription
from app.models.systeme import (
    Alerte,
    Annonce,
    IndicateurStatistique,
    NiveauAlerte,
    Notification,
    ParametreSysteme,
    RegleMetier,
    RequeteEnregistree,
    TypeNotification,
)
from app.seed.contexte import ContexteSeed, logger
from app.utils.calculs import taux

#: Règles métier livrées avec la plateforme.
REGLES: tuple[dict, ...] = (
    {
        "code": "EXCELLENCE_SCOLAIRE",
        "libelle": "Détection des profils d'excellence",
        "domaine": "SCOLARITE",
        "entite_cible": "bulletins",
        "conditions": {"champ": "moyenne_generale", "operateur": "gte", "valeur": 18},
        "consequences": {"categorie": "Excellent", "notifier": True, "proposer_bourse": True},
        "priorite": 10,
    },
    {
        "code": "ALERTE_ASSIDUITE",
        "libelle": "Alerte d'assiduité",
        "domaine": "SCOLARITE",
        "entite_cible": "syntheses_assiduite",
        "conditions": {"champ": "taux_presence", "operateur": "lt", "valeur": 80},
        "consequences": {"alerte": "Assiduité", "niveau": "ATTENTION", "notifier_parent": True},
        "priorite": 20,
    },
    {
        "code": "RISQUE_ECHEC",
        "libelle": "Détection du risque d'échec",
        "domaine": "SCOLARITE",
        "entite_cible": "bulletins",
        "conditions": {"champ": "moyenne_generale", "operateur": "lt", "valeur": 8},
        "consequences": {"alerte": "Risque d'échec", "niveau": "CRITIQUE", "soutien": True},
        "priorite": 5,
    },
    {
        "code": "ETABLISSEMENT_SOUS_PERFORMANT",
        "libelle": "Établissement à accompagner",
        "domaine": "GOUVERNANCE",
        "entite_cible": "etablissements",
        "conditions": {"champ": "taux_reussite", "operateur": "lt", "valeur": 50},
        "consequences": {"alerte": "Faible réussite", "niveau": "CRITIQUE", "mission": True},
        "priorite": 5,
    },
    {
        "code": "SURCHARGE_SALLE",
        "libelle": "Surcharge des salles de classe",
        "domaine": "INFRASTRUCTURE",
        "entite_cible": "classes",
        "conditions": {"champ": "eleves_par_salle", "operateur": "gt", "valeur": 60},
        "consequences": {
            "alerte": "Surcharge",
            "niveau": "ATTENTION",
            "besoin_infrastructure": True,
        },
        "priorite": 15,
    },
    {
        "code": "DEFICIT_ENSEIGNANTS",
        "libelle": "Déficit d'enseignants",
        "domaine": "RESSOURCES_HUMAINES",
        "entite_cible": "etablissements",
        "conditions": {"champ": "eleves_par_enseignant", "operateur": "gt", "valeur": 55},
        "consequences": {"alerte": "Besoin d'enseignants", "niveau": "ATTENTION"},
        "priorite": 15,
    },
    {
        "code": "DOSSIER_INCOMPLET",
        "libelle": "Relance des dossiers incomplets",
        "domaine": "EXAMENS",
        "entite_cible": "candidats",
        "conditions": {"champ": "statut_dossier", "operateur": "eq", "valeur": "INCOMPLET"},
        "consequences": {"notifier": True, "delai_jours": 7},
        "priorite": 10,
    },
    {
        "code": "PRET_EN_RETARD",
        "libelle": "Prêts de bibliothèque en retard",
        "domaine": "BIBLIOTHEQUE",
        "entite_cible": "prets",
        "conditions": {"champ": "jours_retard", "operateur": "gt", "valeur": 7},
        "consequences": {"notifier": True, "penalite_par_jour": 50},
        "priorite": 30,
    },
)

#: Requêtes prêtes à l'emploi, reprenant les exemples de la spécification.
REQUETES: tuple[dict, ...] = (
    {
        "code": "ELEVES_CEG_18",
        "libelle": "Élèves des CEG ayant au moins 18 de moyenne",
        "entite_cible": "apprenants",
        "filtres": [
            {"champ": "type_etablissement", "operateur": "eq", "valeur": "CEG"},
            {"champ": "moyenne_generale", "operateur": "gte", "valeur": 18},
        ],
        "requete_naturelle": "Tous les élèves des CEG ayant plus de 18 de moyenne.",
    },
    {
        "code": "ETAB_FAIBLE_REUSSITE",
        "libelle": "Établissements dont le taux de réussite au BEPC est inférieur à 50 %",
        "entite_cible": "etablissements",
        "filtres": [
            {"champ": "examen", "operateur": "eq", "valeur": "BEPC"},
            {"champ": "taux_reussite", "operateur": "lt", "valeur": 50},
        ],
        "requete_naturelle": "Quels établissements ont moins de 50 % de réussite au BEPC ?",
    },
    {
        "code": "ETAB_SURCHARGES",
        "libelle": "Établissements de plus de 1 000 élèves avec moins de 20 salles",
        "entite_cible": "etablissements",
        "filtres": [
            {"champ": "effectif", "operateur": "gt", "valeur": 1000},
            {"champ": "nombre_salles", "operateur": "lt", "valeur": 20},
        ],
        "requete_naturelle": "Établissements du Littoral de plus de 1 000 élèves "
        "mais de moins de 20 salles.",
    },
    {
        "code": "PROFIL_CONTRASTE",
        "libelle": "Élèves faibles en mathématiques et forts en français",
        "entite_cible": "apprenants",
        "filtres": [
            {"champ": "moyenne_matiere:MATH", "operateur": "lt", "valeur": 8},
            {"champ": "moyenne_matiere:FRA", "operateur": "gt", "valeur": 15},
        ],
        "requete_naturelle": "Élèves ayant moins de 8 en mathématiques et plus de 15 en français.",
    },
    {
        "code": "ABSENTEISME",
        "libelle": "Élèves cumulant plus de 20 % d'absences",
        "entite_cible": "apprenants",
        "filtres": [{"champ": "taux_absence", "operateur": "gt", "valeur": 20}],
        "requete_naturelle": "Quels élèves ont plus de 20 % d'absences ?",
    },
    {
        "code": "CANDIDATS_LIMITE",
        "libelle": "Candidats au BEPC non admis entre 9 et 10 de moyenne",
        "entite_cible": "candidats",
        "filtres": [
            {"champ": "examen", "operateur": "eq", "valeur": "BEPC"},
            {"champ": "decision", "operateur": "eq", "valeur": "NON_ADMIS"},
            {"champ": "moyenne", "operateur": "between", "valeur": [9, 10]},
        ],
        "requete_naturelle": "Candidats BEPC non admis avec une moyenne comprise entre 9 et 10.",
    },
    {
        "code": "INCLUSION",
        "libelle": "Apprenants en situation de handicap scolarisés",
        "entite_cible": "apprenants",
        "filtres": [{"champ": "handicap", "operateur": "ne", "valeur": "AUCUN"}],
        "requete_naturelle": "Montre les apprenants en situation de handicap inscrits cette année.",
    },
)

#: Paramètres de configuration exposés à l'administration.
PARAMETRES: tuple[tuple[str, str, str, str, str], ...] = (
    ("moyenne_admission_defaut", "Moyenne d'admission par défaut", "10", "NOMBRE", "EXAMENS"),
    ("note_eliminatoire", "Note éliminatoire", "3", "NOMBRE", "EXAMENS"),
    ("bareme_defaut", "Barème par défaut des évaluations", "20", "NOMBRE", "EVALUATIONS"),
    ("seuil_alerte_absence", "Seuil d'alerte d'absentéisme (%)", "20", "NOMBRE", "SCOLARITE"),
    ("effectif_max_classe", "Effectif maximal par classe", "60", "NOMBRE", "SCOLARITE"),
    ("duree_pret_bibliotheque", "Durée de prêt (jours)", "14", "NOMBRE", "BIBLIOTHEQUE"),
    (
        "langues_actives",
        "Langues disponibles",
        "FR,FON,YORUBA,BARIBA,DENDI,ADJA",
        "LISTE",
        "ACCESSIBILITE",
    ),
    (
        "mode_simplifie_defaut",
        "Activer l'interface simplifiée par défaut",
        "false",
        "BOOLEEN",
        "ACCESSIBILITE",
    ),
    (
        "taille_max_piece_jointe",
        "Taille maximale d'une pièce jointe (Ko)",
        "5120",
        "NOMBRE",
        "DOCUMENTS",
    ),
    ("devise", "Devise du système", "XOF", "TEXTE", "FINANCES"),
)


async def generer(ctx: ContexteSeed) -> None:
    await _regles_et_parametres(ctx)
    await _indicateurs(ctx)
    await _alertes(ctx)
    await _communication(ctx)
    logger.info("Indicateurs, règles, alertes et notifications générés.")


# ------------------------------------------------------------------


async def _regles_et_parametres(ctx: ContexteSeed) -> None:
    regles = [
        {
            "id": ctx.nouvel_id(),
            "code": regle["code"],
            "libelle": regle["libelle"],
            "description": f"Règle « {regle['libelle']} » appliquée automatiquement.",
            "domaine": regle["domaine"],
            "entite_cible": regle["entite_cible"],
            "conditions": regle["conditions"],
            "consequences": regle["consequences"],
            "priorite": regle["priorite"],
            "active": True,
            "derniere_execution": datetime.now(UTC),
            "nombre_declenchements": ctx.entier(0, 2400),
        }
        for regle in REGLES
    ]
    ctx.cache("regle").update({r["code"]: r["id"] for r in regles})
    await ctx.inserer(RegleMetier, regles)

    proprietaire = ctx.recuperer("compte_demo", "super.admin@eduhub.bj")
    requetes = [
        {
            "id": ctx.nouvel_id(),
            "code": requete["code"],
            "libelle": requete["libelle"],
            "description": requete["requete_naturelle"],
            "entite_cible": requete["entite_cible"],
            "filtres": {"conjonction": "AND", "criteres": requete["filtres"]},
            "colonnes": None,
            "tri": None,
            "proprietaire_id": proprietaire,
            "partagee": True,
            "requete_naturelle": requete["requete_naturelle"],
            "nombre_executions": ctx.entier(0, 180),
        }
        for requete in REQUETES
    ]
    await ctx.inserer(RequeteEnregistree, requetes)

    parametres = [
        {
            "id": ctx.nouvel_id(),
            "cle": cle,
            "libelle": libelle,
            "valeur": valeur,
            "type_valeur": type_valeur,
            "categorie": categorie,
            "modifiable": True,
            "description": f"Paramètre « {libelle} » du système.",
        }
        for cle, libelle, valeur, type_valeur, categorie in PARAMETRES
    ]
    await ctx.inserer(ParametreSysteme, parametres)


async def _indicateurs(ctx: ContexteSeed) -> None:
    """Précalcule les indicateurs nationaux et par établissement."""
    session = ctx.session
    annee_id = ctx.recuperer("annee", "courante")
    horodatage = datetime.now(UTC)

    async def compter(modele, *conditions) -> int:
        stmt = select(func.count()).select_from(modele)
        for condition in conditions:
            stmt = stmt.where(condition)
        return int((await session.execute(stmt)).scalar_one())

    apprenants = await compter(Apprenant, Apprenant.supprime.is_(False))
    filles = await compter(Apprenant, Apprenant.supprime.is_(False), Apprenant.sexe == "FEMININ")
    enseignants = await compter(Enseignant, Enseignant.supprime.is_(False))
    etablissements = await compter(Etablissement, Etablissement.supprime.is_(False))
    classes = await compter(Classe)
    inscriptions = await compter(Inscription)

    moyenne_nationale = (
        await session.execute(select(func.avg(Bulletin.moyenne_generale)))
    ).scalar_one_or_none()

    admis = await compter(ResultatExamen, ResultatExamen.decision == DecisionExamen.ADMIS)
    resultats = await compter(ResultatExamen)

    national = [
        ("apprenants", "Apprenants", float(apprenants), "personnes"),
        ("enseignants", "Enseignants", float(enseignants), "personnes"),
        ("etablissements", "Établissements", float(etablissements), "structures"),
        ("classes", "Classes", float(classes), "classes"),
        ("inscriptions", "Inscriptions", float(inscriptions), "inscriptions"),
        ("taux_filles", "Part des filles", taux(filles, apprenants), "%"),
        ("taux_reussite", "Taux de réussite national", taux(admis, resultats or 1), "%"),
        (
            "moyenne_nationale",
            "Moyenne générale nationale",
            round(float(moyenne_nationale), 2) if moyenne_nationale is not None else 0.0,
            "/20",
        ),
        (
            "ratio_eleves_enseignant",
            "Élèves par enseignant",
            round(apprenants / enseignants, 1) if enseignants else 0.0,
            "élèves",
        ),
    ]

    lignes = [
        {
            "id": ctx.nouvel_id(),
            "code": code,
            "libelle": libelle,
            "categorie": "NATIONAL",
            "perimetre_type": "NATIONAL",
            "perimetre_id": None,
            "perimetre_libelle": "République du Bénin",
            "annee_id": annee_id,
            "valeur": valeur,
            "valeur_precedente": round(valeur * ctx.rng.uniform(0.9, 1.05), 2),
            "variation_pourcentage": round(ctx.rng.uniform(-6, 9), 2),
            "unite": unite,
            "calcule_le": horodatage,
        }
        for code, libelle, valeur, unite in national
    ]

    # Indicateurs par établissement, pour les tableaux de bord locaux.
    stmt = (
        select(
            Etablissement.id,
            Etablissement.nom,
            func.count(func.distinct(Inscription.id)),
            func.avg(Bulletin.moyenne_generale),
        )
        .outerjoin(Inscription, Inscription.etablissement_id == Etablissement.id)
        .outerjoin(Bulletin, Bulletin.etablissement_id == Etablissement.id)
        .group_by(Etablissement.id, Etablissement.nom)
    )
    for ident, nom, effectif, moyenne in (await session.execute(stmt)).all():
        lignes.append(
            {
                "id": ctx.nouvel_id(),
                "code": "effectif",
                "libelle": "Effectif inscrit",
                "categorie": "ETABLISSEMENT",
                "perimetre_type": "ETABLISSEMENT",
                "perimetre_id": ident,
                "perimetre_libelle": nom,
                "annee_id": annee_id,
                "valeur": float(effectif or 0),
                "unite": "élèves",
                "calcule_le": horodatage,
            }
        )
        lignes.append(
            {
                "id": ctx.nouvel_id(),
                "code": "moyenne_etablissement",
                "libelle": "Moyenne de l'établissement",
                "categorie": "ETABLISSEMENT",
                "perimetre_type": "ETABLISSEMENT",
                "perimetre_id": ident,
                "perimetre_libelle": nom,
                "annee_id": annee_id,
                "valeur": round(float(moyenne), 2) if moyenne is not None else 0.0,
                "unite": "/20",
                "calcule_le": horodatage,
            }
        )

    await ctx.inserer(IndicateurStatistique, lignes)


async def _alertes(ctx: ContexteSeed) -> None:
    """Alertes déduites des données produites par les étapes précédentes."""
    session = ctx.session
    alertes = []

    # Établissements dont la moyenne est faible.
    stmt = (
        select(Etablissement.id, Etablissement.nom, func.avg(Bulletin.moyenne_generale))
        .join(Bulletin, Bulletin.etablissement_id == Etablissement.id)
        .group_by(Etablissement.id, Etablissement.nom)
        .having(func.avg(Bulletin.moyenne_generale) < 10)
    )
    for ident, nom, moyenne in (await session.execute(stmt)).all():
        alertes.append(
            {
                "id": ctx.nouvel_id(),
                "code": "MOYENNE_FAIBLE",
                "titre": f"Moyenne préoccupante — {nom}",
                "message": (
                    f"La moyenne générale de l'établissement s'établit à "
                    f"{float(moyenne):.2f}/20, en deçà du seuil de 10."
                ),
                "niveau": NiveauAlerte.CRITIQUE,
                "domaine": "GOUVERNANCE",
                "regle_id": ctx.recuperer("regle", "ETABLISSEMENT_SOUS_PERFORMANT"),
                "entite_type": "etablissement",
                "entite_id": ident,
                "etablissement_id": ident,
                "valeur_mesuree": round(float(moyenne), 2),
                "seuil": 10.0,
                "traitee": False,
            }
        )

    # Sessions d'examen au taux de réussite insuffisant.
    stmt = select(SessionExamen.id, SessionExamen.libelle, SessionExamen.taux_reussite).where(
        SessionExamen.taux_reussite.isnot(None), SessionExamen.taux_reussite < 55
    )
    for ident, libelle, valeur in (await session.execute(stmt)).all():
        alertes.append(
            {
                "id": ctx.nouvel_id(),
                "code": "REUSSITE_INSUFFISANTE",
                "titre": f"Taux de réussite à surveiller — {libelle}",
                "message": f"Le taux de réussite de la session atteint {valeur:.1f} %.",
                "niveau": NiveauAlerte.ATTENTION,
                "domaine": "EXAMENS",
                "entite_type": "session_examen",
                "entite_id": ident,
                "valeur_mesuree": float(valeur),
                "seuil": 55.0,
                "traitee": False,
            }
        )

    # Classes en surcharge.
    stmt = select(Classe.id, Classe.libelle, Classe.effectif).where(Classe.effectif > 60)
    for ident, libelle, effectif in (await session.execute(stmt)).all():
        alertes.append(
            {
                "id": ctx.nouvel_id(),
                "code": "SURCHARGE_CLASSE",
                "titre": f"Classe surchargée — {libelle}",
                "message": f"La classe accueille {effectif} apprenants, au-delà du seuil de 60.",
                "niveau": NiveauAlerte.ATTENTION,
                "domaine": "INFRASTRUCTURE",
                "regle_id": ctx.recuperer("regle", "SURCHARGE_SALLE"),
                "entite_type": "classe",
                "entite_id": ident,
                "valeur_mesuree": float(effectif),
                "seuil": 60.0,
                "traitee": False,
            }
        )

    await ctx.inserer(Alerte, alertes)


async def _communication(ctx: ContexteSeed) -> None:
    """Annonces institutionnelles et notifications de démonstration."""
    annonces = [
        {
            "id": ctx.nouvel_id(),
            "titre": "Ouverture des inscriptions aux examens nationaux",
            "contenu": (
                "Les inscriptions au CEP, au BEPC et au baccalauréat sont ouvertes. "
                "Les candidats officiels sont inscrits par leur établissement ; les "
                "candidats libres créent leur compte directement sur la plateforme."
            ),
            "contenu_simplifie": "Les inscriptions aux examens sont ouvertes.",
            "structure_id": ctx.recuperer("structure", "MESFTP"),
            "public_cible": "Candidats, établissements, parents",
            "urgente": False,
            "date_publication": date.today() - timedelta(days=20),
            "date_expiration": date.today() + timedelta(days=45),
            "publiee": True,
            "nombre_vues": ctx.entier(500, 25000),
        },
        {
            "id": ctx.nouvel_id(),
            "titre": "Publication des résultats",
            "contenu": (
                "Les résultats des sessions normales sont publiés. Chaque candidat peut "
                "consulter son résultat, télécharger son relevé et vérifier l'authenticité "
                "de son diplôme par code ou par QR code."
            ),
            "contenu_simplifie": "Les résultats sont disponibles.",
            "structure_id": ctx.recuperer("structure", "DEC-MESFTP"),
            "public_cible": "Candidats et parents",
            "urgente": True,
            "date_publication": date.today() - timedelta(days=3),
            "publiee": True,
            "nombre_vues": ctx.entier(5000, 120000),
        },
        {
            "id": ctx.nouvel_id(),
            "titre": "Accessibilité : nouveaux services",
            "contenu": (
                "La plateforme propose désormais la lecture vocale des bulletins, "
                "l'interface simplifiée à pictogrammes et la navigation clavier complète. "
                "Ces réglages sont accessibles depuis le profil de chaque utilisateur."
            ),
            "contenu_simplifie": "De nouveaux outils facilitent l'usage pour tous.",
            "structure_id": ctx.recuperer("structure", "MEMP"),
            "public_cible": "Tous les usagers",
            "urgente": False,
            "date_publication": date.today() - timedelta(days=10),
            "publiee": True,
            "nombre_vues": ctx.entier(200, 9000),
        },
    ]
    await ctx.inserer(Annonce, annonces)

    destinataires = list(ctx.cache("compte_demo").values())
    notifications = []
    modeles = (
        (
            TypeNotification.RESULTAT,
            "Résultats publiés",
            "Les résultats de la session sont disponibles.",
        ),
        (
            TypeNotification.BULLETIN,
            "Bulletin disponible",
            "Votre bulletin du trimestre 1 est publié.",
        ),
        (
            TypeNotification.EXAMEN,
            "Convocation émise",
            "Votre convocation à l'examen est téléchargeable.",
        ),
        (TypeNotification.TRANSPORT, "Transport", "Le bus de la ligne 03 arrive dans 8 minutes."),
        (TypeNotification.BOURSE, "Bourse", "Votre candidature à une bourse a été retenue."),
    )
    for destinataire in destinataires:
        for type_notification, titre, message in ctx.echantillon(modeles, 3):
            notifications.append(
                {
                    "id": ctx.nouvel_id(),
                    "destinataire_id": destinataire,
                    "type_notification": type_notification,
                    "canal": "APPLICATION",
                    "titre": titre,
                    "message": message,
                    "message_simplifie": message,
                    "pictogramme": "🔔",
                    "priorite": ctx.entier(0, 3),
                    "lue": ctx.probabilite(0.4),
                }
            )

    await ctx.inserer(Notification, notifications)
