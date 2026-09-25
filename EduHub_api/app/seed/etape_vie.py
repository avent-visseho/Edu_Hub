from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.core.enums import Langue, StatutPaiement
from app.models.apprentissage import (
    CentreAlphabetisation,
    Cours,
    Lecon,
    ModuleCours,
    ParcoursAlphabetisation,
    ProgressionApprentissage,
    QuestionQuiz,
    Quiz,
    RessourcePedagogique,
    StatutPublication,
    TentativeQuiz,
    TypeRessource,
)
from app.models.orientation import (
    CampagneOrientation,
    DossierOrientation,
    Formation,
    StatutVoeu,
    VoeuOrientation,
)
from app.models.projet import (
    CandidatureOffre,
    Chercheur,
    CompetenceApprenant,
    Entreprise,
    JalonProjet,
    Laboratoire,
    MembreProjet,
    Offre,
    Projet,
    ProjetRecherche,
    Publication,
    RoleMembreProjet,
    Stage,
    StatutCandidature,
    StatutProjet,
    TypeContrat,
)
from app.models.vie_etudiante import (
    AbonnementTransport,
    AideSociale,
    ArretTransport,
    AttributionLogement,
    Bibliotheque,
    CampagneSante,
    CandidatureBourse,
    CentreSante,
    Chambre,
    Conducteur,
    Exemplaire,
    LigneTransport,
    Livre,
    Menu,
    Pret,
    ProgrammeBourse,
    RendezVousSante,
    Residence,
    Restaurant,
    StatutCandidatureBourse,
    StatutTrajet,
    StatutVehicule,
    Trajet,
    TypeAideSociale,
    TypeVehicule,
    Vehicule,
    VersementBourse,
)
from app.seed import donnees, scolaire
from app.seed.contexte import ContexteSeed, logger
from app.utils.codes import generer_code_barre, generer_reference

TITRES_LIVRES = (
    "Mathématiques pour la classe de terminale",
    "Grammaire et expression française",
    "Histoire du Bénin contemporain",
    "Sciences de la vie et de la Terre",
    "Physique-chimie appliquée",
    "Contes et légendes du Dahomey",
    "Initiation à l'informatique",
    "Anglais pour débutants",
    "Géographie de l'Afrique de l'Ouest",
    "Philosophie : les grands courants",
    "Économie générale et statistiques",
    "Agriculture durable en zone tropicale",
    "Santé communautaire et prévention",
    "Langues nationales : le fon en pratique",
    "Entrepreneuriat des jeunes",
)

AUTEURS = (
    "A. HOUNKPE",
    "M. DOSSOU",
    "F. GBAGUIDI",
    "P. ZINSOU",
    "L. AGBODJAN",
    "S. AMOUSSOU",
    "K. BIO",
    "R. QUENUM",
    "T. SOGLO",
    "N. ADJOVI",
)

PLATS = (
    "Riz au gras et poisson",
    "Igname pilée sauce arachide",
    "Pâte rouge et légumes",
    "Haricot et gari",
    "Atassi et sauce tomate",
    "Spaghetti sauce viande",
    "Akassa et poisson frit",
    "Couscous de maïs aux légumes",
)


async def generer(ctx: ContexteSeed) -> None:
    await _orientation(ctx)
    await _bourses(ctx)
    await _transport(ctx)
    await _logement_restauration(ctx)
    await _sante(ctx)
    await _bibliotheque(ctx)
    await _apprentissage(ctx)
    await _alphabetisation(ctx)
    await _projets_et_recherche(ctx)
    await _entreprises_stages_emploi(ctx)
    logger.info("Vie étudiante, projets et insertion professionnelle générés.")


# ------------------------------------------------------------------


def _universites(ctx: ContexteSeed) -> list[str]:
    codes = ctx.cache("etablissements_par_type").get("UNIV", [])
    codes += ctx.cache("etablissements_par_type").get("IUT", [])
    return codes or list(ctx.cache("etablissement_info"))[:3]


def _apprenants_echantillon(ctx: ContexteSeed, part: float) -> list[dict]:
    tous = [
        membre for liste in ctx.cache("apprenants_par_etablissement").values() for membre in liste
    ]
    return ctx.echantillon(tous, max(1, int(len(tous) * part)))


async def _orientation(ctx: ContexteSeed) -> None:
    """Formations universitaires, campagne d'orientation et vœux des bacheliers."""
    formations = []
    for code_etablissement in _universites(ctx):
        info = ctx.cache("etablissement_info")[code_etablissement]
        for code_filiere, libelle, code_diplome, duree in ctx.echantillon(scolaire.FILIERES, 7):
            code = f"FOR-{code_etablissement}-{code_filiere}"
            ident = ctx.nouvel_id()
            ctx.cache("formation")[code] = ident
            formations.append(
                {
                    "id": ident,
                    "code": code,
                    "intitule": f"{libelle} — {info['nom']}",
                    "etablissement_id": info["id"],
                    "filiere_id": ctx.recuperer("filiere", code_filiere),
                    "diplome_id": ctx.recuperer("diplome", code_diplome),
                    "type_formation_id": ctx.recuperer("type_formation", "INITIALE"),
                    "niveau_entree": "Baccalauréat",
                    "duree_annees": duree,
                    "credits_total": duree * 60,
                    "places_offertes": ctx.entier(40, 350),
                    "places_pourvues": 0,
                    "moyenne_minimale": round(ctx.rng.uniform(10, 14), 2),
                    "series_admises": ",".join(ctx.echantillon(scolaire.SERIES_GENERALES, 3)),
                    "conditions": "Être titulaire du baccalauréat et satisfaire aux prérequis.",
                    "debouches": f"Métiers du secteur « {libelle} ».",
                    "frais_annuels": float(ctx.entier(20_000, 350_000)),
                    "ouverte": True,
                }
            )
    await ctx.inserer(Formation, formations)

    if not formations:
        return

    annee = date.today().year
    id_campagne = ctx.nouvel_id()
    await ctx.inserer(
        CampagneOrientation,
        [
            {
                "id": id_campagne,
                "code": f"ORIENT-{annee}",
                "libelle": f"Campagne nationale d'orientation {annee}",
                "annee_id": ctx.recuperer("annee", "courante"),
                "date_ouverture": date(annee, 7, 25),
                "date_fermeture": date(annee, 8, 31),
                "date_resultats": date(annee, 9, 15),
                "nombre_voeux_max": 5,
                "ouverte": True,
            }
        ],
    )

    dossiers, voeux = [], []
    candidats_bac = [
        membre
        for code_classe in ctx.cache("classes_par_niveau").get("TLE", [])
        for membre in ctx.cache("classe_info")[code_classe]["apprenants"]
    ]

    for membre in ctx.echantillon(candidats_bac, min(len(candidats_bac), 800)):
        id_dossier = ctx.nouvel_id()
        moyenne = membre.get("moyenne_generale") or round(ctx.rng.uniform(9, 17), 2)
        choisies = ctx.echantillon(formations, ctx.entier(2, 5))
        affectee = choisies[0] if moyenne >= 10 and ctx.probabilite(0.72) else None
        if affectee is not None:
            # Le compteur de places doit refléter les affectations produites.
            affectee["places_pourvues"] += 1

        dossiers.append(
            {
                "id": id_dossier,
                "campagne_id": id_campagne,
                "apprenant_id": membre["id"],
                "moyenne_bac": moyenne,
                "profil_detecte": "Profil scientifique" if moyenne >= 13 else "Profil littéraire",
                "formation_affectee_id": affectee["id"] if affectee else None,
                "date_affectation": date(annee, 9, 15) if affectee else None,
                "statut": StatutVoeu.ACCEPTE if affectee else StatutVoeu.LISTE_ATTENTE,
            }
        )
        for rang, formation in enumerate(choisies, start=1):
            voeux.append(
                {
                    "id": ctx.nouvel_id(),
                    "dossier_id": id_dossier,
                    "formation_id": formation["id"],
                    "rang": rang,
                    "statut": StatutVoeu.ACCEPTE
                    if affectee and formation["id"] == affectee["id"]
                    else StatutVoeu.REFUSE
                    if affectee
                    else StatutVoeu.LISTE_ATTENTE,
                }
            )

    await ctx.inserer(DossierOrientation, dossiers)
    await ctx.inserer(VoeuOrientation, voeux)


async def _bourses(ctx: ContexteSeed) -> None:
    """Programmes de bourses, candidatures, versements et aides sociales."""
    annee = date.today().year
    programmes, candidatures, versements, aides = [], [], [], []

    for code, libelle, montant in donnees.TYPES_BOURSE:
        id_programme = ctx.nouvel_id()
        places = ctx.entier(40, 400)
        programmes.append(
            {
                "id": id_programme,
                "code": f"PROG-{code}-{annee}",
                "intitule": f"{libelle} — promotion {annee}",
                "type_bourse_id": ctx.recuperer("type_bourse", code),
                "structure_id": ctx.recuperer("structure", "MESRS"),
                "annee_id": ctx.recuperer("annee", "courante"),
                "description": f"Programme « {libelle} » ouvert aux apprenants éligibles.",
                "criteres_eligibilite": "Résultats scolaires, situation sociale et assiduité.",
                "montant_mensuel": montant,
                "duree_mois": 10,
                "places": places,
                "places_attribuees": 0,
                "moyenne_minimale": 12.0 if code in {"EXCELLENCE", "MERITE"} else 10.0,
                "date_ouverture": date(annee, 8, 1),
                "date_cloture": date(annee, 10, 15),
                "ouvert": True,
                "reserve_handicap": code == "HANDICAP",
            }
        )

        candidats = _apprenants_echantillon(ctx, 0.02)
        attribuees = 0
        for rang, membre in enumerate(candidats, start=1):
            moyenne = membre.get("moyenne_generale") or round(ctx.rng.uniform(8, 18), 2)
            retenu = attribuees < places and moyenne >= 12 and ctx.probabilite(0.5)
            if retenu:
                attribuees += 1
            id_candidature = ctx.nouvel_id()
            statut = (
                StatutCandidatureBourse.ATTRIBUEE
                if retenu
                else ctx.choix(
                    [
                        StatutCandidatureBourse.REJETEE,
                        StatutCandidatureBourse.EN_EVALUATION,
                        StatutCandidatureBourse.PRESELECTIONNEE,
                    ]
                )
            )
            candidatures.append(
                {
                    "id": id_candidature,
                    "numero": f"BRS-{code}-{annee}-{rang:06d}",
                    "programme_id": id_programme,
                    "apprenant_id": membre["id"],
                    "statut": statut,
                    "moyenne_reference": moyenne,
                    "score_evaluation": round(moyenne * 5, 2),
                    "revenu_familial_declare": float(ctx.entier(30_000, 450_000)),
                    "motivation": "Poursuivre mes études dans de bonnes conditions.",
                    "date_soumission": date(annee, 9, ctx.entier(1, 28)),
                    "date_decision": date(annee, 10, 20),
                    "montant_attribue": montant if retenu else 0.0,
                    "date_debut_versement": date(annee, 11, 1) if retenu else None,
                    "date_fin_versement": date(annee + 1, 8, 31) if retenu else None,
                }
            )

            if retenu:
                for mois in range(4):
                    versements.append(
                        {
                            "id": ctx.nouvel_id(),
                            "candidature_id": id_candidature,
                            "periode_libelle": f"Mensualité {mois + 1}",
                            "montant": montant,
                            "date_prevue": date(annee, 11, 5) + timedelta(days=30 * mois),
                            "date_versement": date(annee, 11, 8) + timedelta(days=30 * mois),
                            "statut": StatutPaiement.PAYE,
                            "reference": generer_reference("VRS"),
                        }
                    )

        programmes[-1]["places_attribuees"] = attribuees

    for rang, membre in enumerate(_apprenants_echantillon(ctx, 0.03), start=1):
        type_aide = ctx.choix(list(TypeAideSociale))
        aides.append(
            {
                "id": ctx.nouvel_id(),
                "numero": f"AIDE-{annee}-{rang:06d}",
                "apprenant_id": membre["id"],
                "type_aide": type_aide,
                "libelle": f"Aide « {type_aide.value.lower()} »",
                "motif": "Situation familiale difficile constatée par les services sociaux.",
                "montant": float(ctx.entier(10_000, 150_000)),
                "en_nature": ctx.probabilite(0.3),
                "date_demande": date(annee, ctx.entier(1, 11), ctx.entier(1, 28)),
                "date_attribution": date(annee, 12, 1),
                "statut": StatutCandidatureBourse.ATTRIBUEE,
            }
        )

    await ctx.inserer(ProgrammeBourse, programmes)
    await ctx.inserer(CandidatureBourse, candidatures)
    await ctx.inserer(VersementBourse, versements)
    await ctx.inserer(AideSociale, aides)


async def _transport(ctx: ContexteSeed) -> None:
    """Lignes, arrêts, véhicules, conducteurs, trajets suivis et abonnements."""
    lignes, arrets, vehicules, conducteurs, trajets, abonnements = [], [], [], [], [], []
    supports = _universites(ctx) + ctx.echantillon(
        ctx.cache("etablissements_par_type").get("LYCEE", []), 6
    )

    for numero, code_etablissement in enumerate(supports, start=1):
        info = ctx.cache("etablissement_info")[code_etablissement]
        commune = _libelle_commune(info["commune"])
        id_ligne = ctx.nouvel_id()
        tarif = float(ctx.entier(100, 350))

        lignes.append(
            {
                "id": id_ligne,
                "code": f"L{numero:02d}",
                "libelle": f"Ligne {numero:02d} — {commune} / {info['nom']}",
                "etablissement_id": info["id"],
                "commune_id": ctx.recuperer("commune", info["commune"]),
                "origine": f"Gare routière de {commune}",
                "destination": info["nom"],
                "distance_km": round(ctx.rng.uniform(3, 28), 1),
                "duree_minutes": ctx.entier(15, 70),
                "tarif": tarif,
                "tarif_abonnement": tarif * 18,
                "couleur": ctx.choix(["#1B4F8A", "#0F7B4F", "#B45309", "#7C3AED", "#BE123C"]),
                "active": True,
            }
        )

        arrets_ligne = []
        for rang in range(1, ctx.entier(5, 10)):
            id_arret = ctx.nouvel_id()
            arrets_ligne.append(id_arret)
            latitude, longitude = ctx.coordonnees(info.get("latitude", 6.4), 2.4, 0.08)
            arrets.append(
                {
                    "id": id_arret,
                    "ligne_id": id_ligne,
                    "code": f"L{numero:02d}-A{rang:02d}",
                    "nom": f"Arrêt {commune} {rang}",
                    "ordre": rang,
                    "latitude": latitude,
                    "longitude": longitude,
                    "heure_passage_aller": time(6, 0 + rang % 6 * 10 % 60),
                    "heure_passage_retour": time(17, 0 + rang % 5 * 10 % 60),
                    "abri": ctx.probabilite(0.4),
                    "accessible_handicap": ctx.probabilite(0.3),
                }
            )

        for index in range(ctx.entier(1, 3)):
            id_vehicule = ctx.nouvel_id()
            places = ctx.entier(28, 64)
            vehicules.append(
                {
                    "id": id_vehicule,
                    "immatriculation": f"AB-{ctx.entier(1000, 9999)}-RB{numero}{index}",
                    "code": f"B-{numero:02d}{index}",
                    "type_vehicule": ctx.rng.choices(
                        list(TypeVehicule), weights=[50, 25, 15, 5, 3, 2]
                    )[0],
                    "marque": ctx.choix(["Toyota", "Mercedes", "Hyundai", "Iveco"]),
                    "modele": ctx.choix(["Coaster", "Sprinter", "County", "Daily"]),
                    "annee": ctx.entier(2012, 2024),
                    "places": places,
                    "places_pmr": ctx.entier(0, 3),
                    "statut": ctx.rng.choices(list(StatutVehicule), weights=[85, 8, 4, 3])[0],
                    "etablissement_id": info["id"],
                    "derniere_visite_technique": ctx.date_entre(
                        date.today() - timedelta(days=330), date.today()
                    ),
                    "climatise": ctx.probabilite(0.35),
                }
            )

            id_conducteur = ctx.nouvel_id()
            sexe = ctx.sexe(0.1)
            nom, prenoms = ctx.identite(sexe)
            conducteurs.append(
                {
                    "id": id_conducteur,
                    "matricule": f"CND-{ctx.suivant('conducteur'):05d}",
                    "nom_complet": f"{prenoms} {nom}",
                    "telephone": ctx.telephone(),
                    "numero_permis": f"P{ctx.entier(100000, 999999)}",
                    "categorie_permis": ctx.choix(["C", "D", "D1"]),
                    "date_validite_permis": date.today() + timedelta(days=ctx.entier(60, 1400)),
                    "annees_experience": ctx.entier(2, 25),
                    "actif": True,
                }
            )

            # Trajet du jour, avec suivi simulé en temps réel.
            occupees = ctx.entier(5, places)
            trajets.append(
                {
                    "id": ctx.nouvel_id(),
                    "ligne_id": id_ligne,
                    "vehicule_id": id_vehicule,
                    "conducteur_id": id_conducteur,
                    "date_trajet": date.today(),
                    "sens": "ALLER",
                    "heure_depart_prevue": time(6, 30),
                    "heure_depart_reelle": time(6, 35),
                    "heure_arrivee_prevue": time(7, 30),
                    "statut": ctx.rng.choices(list(StatutTrajet), weights=[15, 55, 20, 3, 7])[0],
                    "places_occupees": occupees,
                    "prochain_arret_id": ctx.choix(arrets_ligne) if arrets_ligne else None,
                    "minutes_avant_prochain_arret": ctx.entier(1, 20),
                    "latitude_actuelle": ctx.coordonnees(6.4, 2.4, 0.2)[0],
                    "longitude_actuelle": ctx.coordonnees(6.4, 2.4, 0.2)[1],
                    "retard_minutes": ctx.entier(0, 18),
                }
            )

        # Abonnements des apprenants de l'établissement desservi.
        for membre in ctx.echantillon(
            ctx.cache("apprenants_par_etablissement").get(code_etablissement, []), 40
        ):
            abonnements.append(
                {
                    "id": ctx.nouvel_id(),
                    "apprenant_id": membre["id"],
                    "ligne_id": id_ligne,
                    "arret_montee_id": ctx.choix(arrets_ligne) if arrets_ligne else None,
                    "numero_carte": f"TR{ctx.suivant('carte_transport'):08d}",
                    "date_debut": date.today() - timedelta(days=ctx.entier(10, 120)),
                    "date_fin": date.today() + timedelta(days=ctx.entier(30, 240)),
                    "montant": tarif * 18,
                    "statut_paiement": StatutPaiement.PAYE,
                    "actif": True,
                }
            )

    await ctx.inserer(LigneTransport, lignes)
    await ctx.inserer(ArretTransport, arrets)
    await ctx.inserer(Vehicule, vehicules)
    await ctx.inserer(Conducteur, conducteurs)
    await ctx.inserer(Trajet, trajets)
    await ctx.inserer(AbonnementTransport, abonnements)


async def _logement_restauration(ctx: ContexteSeed) -> None:
    """Résidences universitaires, chambres, attributions, restaurants et menus."""
    residences, chambres, attributions, restaurants, menus = [], [], [], [], []

    for numero, code_etablissement in enumerate(_universites(ctx), start=1):
        info = ctx.cache("etablissement_info")[code_etablissement]
        id_residence = ctx.nouvel_id()
        capacite = ctx.entier(120, 900)
        tarif = float(ctx.entier(5000, 25000))

        residences.append(
            {
                "id": id_residence,
                "code": f"RES-{numero:03d}",
                "nom": f"Résidence universitaire {info['nom']}",
                "etablissement_id": info["id"],
                "commune_id": ctx.recuperer("commune", info["commune"]),
                "adresse": _libelle_commune(info["commune"]),
                "capacite": capacite,
                "places_occupees": 0,
                "tarif_mensuel": tarif,
                "mixte": ctx.probabilite(0.5),
                "accessible_handicap": ctx.probabilite(0.6),
            }
        )

        candidats = ctx.echantillon(
            ctx.cache("apprenants_par_etablissement").get(code_etablissement, []), 60
        )
        index_candidat = 0
        occupees = 0

        for rang in range(1, capacite // 3 + 1):
            id_chambre = ctx.nouvel_id()
            lits = ctx.entier(1, 4)
            chambres.append(
                {
                    "id": id_chambre,
                    "residence_id": id_residence,
                    "numero": f"{rang:03d}",
                    "batiment": chr(65 + rang % 4),
                    "etage": rang % 3,
                    "nombre_lits": lits,
                    "lits_occupes": 0,
                    "tarif_mensuel": tarif,
                    "disponible": True,
                    "accessible_handicap": rang % 10 == 0,
                }
            )

            for lit in range(1, lits + 1):
                if index_candidat >= len(candidats) or not ctx.probabilite(0.6):
                    continue
                membre = candidats[index_candidat]
                index_candidat += 1
                occupees += 1
                chambres[-1]["lits_occupes"] += 1
                attributions.append(
                    {
                        "id": ctx.nouvel_id(),
                        "apprenant_id": membre["id"],
                        "chambre_id": id_chambre,
                        "numero_lit": lit,
                        "date_debut": date(date.today().year, 10, 1),
                        "date_fin": date(date.today().year + 1, 7, 31),
                        "statut": StatutCandidatureBourse.ATTRIBUEE,
                        "caution": tarif,
                    }
                )
        residences[-1]["places_occupees"] = occupees

        id_restaurant = ctx.nouvel_id()
        restaurants.append(
            {
                "id": id_restaurant,
                "code": f"RU-{numero:03d}",
                "nom": f"Restaurant universitaire {info['nom']}",
                "etablissement_id": info["id"],
                "capacite": ctx.entier(200, 1200),
                "tarif_repas": float(ctx.entier(500, 1500)),
                "tarif_subventionne": float(ctx.entier(100, 400)),
                "horaire_ouverture": time(11, 0),
                "horaire_fermeture": time(14, 30),
                "actif": True,
            }
        )
        for jour in range(14):
            menus.append(
                {
                    "id": ctx.nouvel_id(),
                    "restaurant_id": id_restaurant,
                    "date_service": date.today() + timedelta(days=jour),
                    "service": "DEJEUNER",
                    "entree": ctx.choix(["Salade de crudités", "Bouillon", "Beignets"]),
                    "plat_principal": ctx.choix(PLATS),
                    "accompagnement": ctx.choix(["Légumes sautés", "Salade", "Piment doux"]),
                    "dessert": ctx.choix(["Banane", "Ananas", "Orange", "Yaourt"]),
                    "boisson": ctx.choix(["Eau", "Jus de bissap", "Jus de gingembre"]),
                    "calories": ctx.entier(600, 1100),
                    "vegetarien": ctx.probabilite(0.2),
                    "repas_servis": ctx.entier(120, 900),
                }
            )

    await ctx.inserer(Residence, residences)
    await ctx.inserer(Chambre, chambres)
    await ctx.inserer(AttributionLogement, attributions)
    await ctx.inserer(Restaurant, restaurants)
    await ctx.inserer(Menu, menus)


async def _sante(ctx: ContexteSeed) -> None:
    """Centres de santé scolaire, rendez-vous et campagnes de prévention."""
    centres, rendez_vous, campagnes = [], [], []

    for numero, code_etablissement in enumerate(
        ctx.echantillon(list(ctx.cache("etablissement_info")), 25), start=1
    ):
        info = ctx.cache("etablissement_info")[code_etablissement]
        id_centre = ctx.nouvel_id()
        centres.append(
            {
                "id": id_centre,
                "code": f"CS-{numero:03d}",
                "nom": f"Infirmerie scolaire — {info['nom']}",
                "etablissement_id": info["id"],
                "commune_id": ctx.recuperer("commune", info["commune"]),
                "services": "Consultations, premiers secours, prévention, vaccination",
                "telephone": ctx.telephone(),
                "nombre_agents": ctx.entier(1, 5),
                "actif": True,
            }
        )
        for membre in ctx.echantillon(
            ctx.cache("apprenants_par_etablissement").get(code_etablissement, []), 8
        ):
            rendez_vous.append(
                {
                    "id": ctx.nouvel_id(),
                    "centre_sante_id": id_centre,
                    "apprenant_id": membre["id"],
                    "motif": ctx.choix(
                        ["Visite médicale annuelle", "Consultation", "Vaccination", "Suivi"]
                    ),
                    "date_rdv": datetime.combine(
                        date.today() + timedelta(days=ctx.entier(-40, 40)), time(9, 30)
                    ),
                    "statut": ctx.choix(["PLANIFIE", "HONORE", "ANNULE"]),
                    "confidentiel": True,
                }
            )

    for rang, theme in enumerate(
        (
            "Vaccination",
            "Hygiène et lavage des mains",
            "Santé de la reproduction",
            "Lutte contre le paludisme",
            "Nutrition scolaire",
        ),
        start=1,
    ):
        cibles = ctx.entier(5000, 60000)
        campagnes.append(
            {
                "id": ctx.nouvel_id(),
                "code": f"CAMP-{date.today().year}-{rang:02d}",
                "intitule": f"Campagne nationale — {theme}",
                "theme": theme,
                "date_debut": date.today() - timedelta(days=ctx.entier(20, 200)),
                "date_fin": date.today() + timedelta(days=ctx.entier(10, 120)),
                "beneficiaires_cibles": cibles,
                "beneficiaires_atteints": int(cibles * ctx.rng.uniform(0.4, 0.95)),
            }
        )

    await ctx.inserer(CentreSante, centres)
    await ctx.inserer(RendezVousSante, rendez_vous)
    await ctx.inserer(CampagneSante, campagnes)


async def _bibliotheque(ctx: ContexteSeed) -> None:
    """Bibliothèques, catalogue, exemplaires et prêts en cours."""
    bibliotheques, livres, exemplaires, prets = [], [], [], []

    supports = ctx.echantillon(list(ctx.cache("etablissement_info")), 20)
    for numero, code_etablissement in enumerate(supports, start=1):
        info = ctx.cache("etablissement_info")[code_etablissement]
        bibliotheques.append(
            {
                "id": ctx.nouvel_id(),
                "code": f"BIB-{numero:03d}",
                "nom": f"Bibliothèque — {info['nom']}",
                "etablissement_id": info["id"],
                "nombre_places": ctx.entier(20, 200),
                "duree_pret_jours": 14,
                "prets_simultanes_max": 3,
                "actif": True,
            }
        )

    for rang in range(ctx.volumetrie.livres):
        titre = ctx.choix(TITRES_LIVRES)
        id_livre = ctx.nouvel_id()
        accessible = ctx.probabilite(0.18)
        livres.append(
            {
                "id": id_livre,
                "isbn": f"978-2-{ctx.entier(10000, 99999)}-{ctx.entier(10, 99)}-{rang % 10}",
                "titre": f"{titre} — tome {ctx.entier(1, 3)}",
                "auteur": ctx.choix(AUTEURS),
                "editeur": ctx.choix(["Éditions du Flamboyant", "CNPMS", "Ruisseaux d'Afrique"]),
                "annee_publication": ctx.entier(1998, 2025),
                "categorie": ctx.choix(
                    [
                        "Manuel scolaire",
                        "Littérature",
                        "Sciences",
                        "Sciences humaines",
                        "Documentaire",
                        "Jeunesse",
                    ]
                ),
                "langue": "Français",
                "nombre_pages": ctx.entier(80, 520),
                "resume": "Ouvrage de référence du fonds documentaire.",
                "format_accessible": accessible,
                "audio_disponible": accessible and ctx.probabilite(0.6),
                "braille_disponible": accessible and ctx.probabilite(0.35),
            }
        )

        for _ in range(ctx.entier(1, 4)):
            id_exemplaire = ctx.nouvel_id()
            bibliotheque = ctx.choix(bibliotheques)
            disponible = ctx.probabilite(0.72)
            exemplaires.append(
                {
                    "id": id_exemplaire,
                    "livre_id": id_livre,
                    "bibliotheque_id": bibliotheque["id"],
                    "code_barre": generer_code_barre("EX", ctx.rng),
                    "cote": f"{ctx.entier(100, 999)}.{ctx.entier(10, 99)}",
                    "etat": ctx.choix(["NEUF", "BON", "MOYEN", "USE"]),
                    "disponible": disponible,
                }
            )

            if not disponible:
                membre = ctx.choix(
                    [
                        m
                        for liste in ctx.cache("apprenants_par_etablissement").values()
                        for m in liste
                    ]
                )
                emprunt = date.today() - timedelta(days=ctx.entier(1, 40))
                retour_prevu = emprunt + timedelta(days=14)
                retard = max(0, (date.today() - retour_prevu).days)
                prets.append(
                    {
                        "id": ctx.nouvel_id(),
                        "exemplaire_id": id_exemplaire,
                        "apprenant_id": membre["id"],
                        "date_pret": emprunt,
                        "date_retour_prevue": retour_prevu,
                        "date_retour_effective": None,
                        "jours_retard": retard,
                        "penalite": float(retard * 50),
                        "prolonge": ctx.probabilite(0.15),
                        "rendu": False,
                    }
                )

    await ctx.inserer(Bibliotheque, bibliotheques)
    await ctx.inserer(Livre, livres)
    await ctx.inserer(Exemplaire, exemplaires)
    await ctx.inserer(Pret, prets)


def _libelle_commune(code_commune: str) -> str:
    code_departement, index = code_commune.split("-")
    return donnees.COMMUNES[code_departement][int(index) - 1]


async def _apprentissage(ctx: ContexteSeed) -> None:
    """Cours en ligne, modules, leçons, ressources, quiz et progressions."""
    cours, modules, lecons, ressources, quiz, questions = [], [], [], [], [], []
    progressions, tentatives = [], []

    enseignants = [
        enseignant
        for liste in ctx.cache("enseignants_par_etablissement").values()
        for enseignant in liste
    ]

    for numero in range(1, ctx.volumetrie.cours + 1):
        code_matiere, libelle_matiere, *_ = ctx.choix(scolaire.MATIERES)
        code_niveau = ctx.choix([n[0] for n in scolaire.NIVEAUX])
        enseignant = ctx.choix(enseignants) if enseignants else None
        id_cours = ctx.nouvel_id()
        accessible = ctx.probabilite(0.45)

        cours.append(
            {
                "id": id_cours,
                "code": f"COURS-{numero:05d}",
                "titre": f"{libelle_matiere} — {code_niveau}",
                "description": (
                    f"Cours complet de {libelle_matiere} destiné au niveau {code_niveau}, "
                    "conçu pour un usage en connectivité limitée."
                ),
                "matiere_id": ctx.recuperer("matiere", code_matiere),
                "niveau_id": ctx.recuperer("niveau", code_niveau),
                "enseignant_id": enseignant["id"] if enseignant else None,
                "langue": Langue.FR,
                "duree_heures": ctx.entier(6, 40),
                "statut": StatutPublication.PUBLIE,
                "disponible_hors_ligne": True,
                "transcription_disponible": accessible,
                "sous_titres_disponibles": accessible,
                "version_audio": accessible,
                "nombre_inscrits": 0,
                "note_moyenne": round(ctx.rng.uniform(3.2, 5.0), 2),
            }
        )

        lecons_du_cours = []
        for rang_module in range(1, ctx.entier(3, 6)):
            id_module = ctx.nouvel_id()
            modules.append(
                {
                    "id": id_module,
                    "cours_id": id_cours,
                    "titre": f"Module {rang_module} — {libelle_matiere}",
                    "description": "Objectifs, contenus et exercices du module.",
                    "ordre": rang_module,
                    "duree_minutes": ctx.entier(60, 240),
                }
            )

            for rang_lecon in range(1, ctx.entier(3, 6)):
                id_lecon = ctx.nouvel_id()
                lecons_du_cours.append(id_lecon)
                lecons.append(
                    {
                        "id": id_lecon,
                        "module_id": id_module,
                        "titre": f"Leçon {rang_module}.{rang_lecon}",
                        "contenu": "Contenu pédagogique structuré de la leçon.",
                        "contenu_simplifie": "L'essentiel de la leçon, en phrases courtes.",
                        "ordre": rang_lecon,
                        "duree_minutes": ctx.entier(15, 60),
                        "audio_url": f"cours/{numero}/lecon-{rang_module}-{rang_lecon}.mp3"
                        if accessible
                        else None,
                        "transcription": "Transcription intégrale disponible."
                        if accessible
                        else None,
                    }
                )

                ressources.append(
                    {
                        "id": ctx.nouvel_id(),
                        "code": f"RES-{ctx.suivant('ressource'):06d}",
                        "titre": f"Support de la leçon {rang_module}.{rang_lecon}",
                        "type_ressource": ctx.rng.choices(
                            list(TypeRessource),
                            weights=[30, 12, 10, 8, 8, 12, 6, 4, 6, 2, 2],
                        )[0],
                        "lecon_id": id_lecon,
                        "matiere_id": ctx.recuperer("matiere", code_matiere),
                        "niveau_id": ctx.recuperer("niveau", code_niveau),
                        "fichier_url": f"ressources/{code_matiere}/{ctx.nouvel_id().hex[:8]}.pdf",
                        "taille_ko": ctx.entier(80, 4800),
                        "langue": Langue.FR,
                        "statut": StatutPublication.PUBLIE,
                        "licence": "Creative Commons BY-NC",
                        "mots_cles": f"{code_matiere},{code_niveau}",
                        "nombre_vues": ctx.entier(0, 8000),
                        "nombre_telechargements": ctx.entier(0, 2500),
                        "poids_leger": True,
                    }
                )

        if lecons_du_cours:
            id_quiz = ctx.nouvel_id()
            quiz.append(
                {
                    "id": id_quiz,
                    "code": f"QUIZ-{numero:05d}",
                    "titre": f"Évaluation du cours — {libelle_matiere}",
                    "lecon_id": lecons_du_cours[-1],
                    "matiere_id": ctx.recuperer("matiere", code_matiere),
                    "niveau_id": ctx.recuperer("niveau", code_niveau),
                    "duree_minutes": ctx.entier(10, 30),
                    "note_passage": 10.0,
                    "tentatives_max": 3,
                    "aleatoire": True,
                }
            )
            for rang_question in range(1, ctx.entier(5, 11)):
                questions.append(
                    {
                        "id": ctx.nouvel_id(),
                        "quiz_id": id_quiz,
                        "enonce": f"Question {rang_question} portant sur {libelle_matiere}.",
                        "type_question": "CHOIX_UNIQUE",
                        "propositions": "A) Proposition 1|B) Proposition 2|C) Proposition 3",
                        "reponse_correcte": ctx.choix(["A", "B", "C"]),
                        "explication": "Justification de la réponse attendue.",
                        "points": 1.0,
                        "ordre": rang_question,
                    }
                )

        # Progressions d'apprenants inscrits au cours.
        inscrits = ctx.echantillon(_apprenants_echantillon(ctx, 0.004), 25)
        cours[-1]["nombre_inscrits"] = len(inscrits)
        for membre in inscrits:
            total = len(lecons_du_cours)
            faites = ctx.entier(0, total)
            progressions.append(
                {
                    "id": ctx.nouvel_id(),
                    "apprenant_id": membre["id"],
                    "cours_id": id_cours,
                    "lecons_terminees": faites,
                    "lecons_totales": total,
                    "pourcentage": round(faites * 100 / total, 2) if total else 0.0,
                    "temps_passe_minutes": faites * ctx.entier(12, 45),
                    "termine": total > 0 and faites == total,
                    "note_finale": round(ctx.rng.uniform(6, 19), 2) if faites == total else None,
                    "certificat_delivre": total > 0 and faites == total,
                }
            )

    await ctx.inserer(Cours, cours)
    await ctx.inserer(ModuleCours, modules)
    await ctx.inserer(Lecon, lecons)
    await ctx.inserer(RessourcePedagogique, ressources)
    await ctx.inserer(Quiz, quiz)
    await ctx.inserer(QuestionQuiz, questions)
    await ctx.inserer(ProgressionApprentissage, progressions)
    await ctx.inserer(TentativeQuiz, tentatives)


async def _alphabetisation(ctx: ContexteSeed) -> None:
    """Centres d'alphabétisation et parcours des apprenants adultes."""
    centres, parcours = [], []
    langues = [Langue.FON, Langue.YORUBA, Langue.BARIBA, Langue.DENDI, Langue.ADJA]

    for code_departement, *_ in donnees.DEPARTEMENTS:
        for index in range(ctx.entier(1, 3)):
            id_centre = ctx.nouvel_id()
            code_commune = ctx.choix(ctx.cache("communes_par_departement")[code_departement])
            langue = ctx.choix(langues)
            apprenants = ctx.entier(15, 90)

            centres.append(
                {
                    "id": id_centre,
                    "code": f"CAL-{code_departement}-{index + 1:02d}",
                    "nom": f"Centre d'alphabétisation de {_libelle_commune(code_commune)}",
                    "commune_id": ctx.recuperer("commune", code_commune),
                    "langue_enseignement": langue,
                    "responsable": f"{ctx.identite('FEMININ')[1]} {ctx.identite('FEMININ')[0]}",
                    "telephone": ctx.telephone(),
                    "nombre_formateurs": ctx.entier(1, 6),
                    "nombre_apprenants": apprenants,
                    "actif": True,
                }
            )

            for _ in range(min(apprenants, 12)):
                sexe = ctx.sexe(0.68)
                nom, prenoms = ctx.identite(sexe)
                progression = round(ctx.rng.uniform(0, 100), 1)
                parcours.append(
                    {
                        "id": ctx.nouvel_id(),
                        "centre_id": id_centre,
                        "nom_complet": f"{prenoms} {nom}",
                        "age": ctx.entier(16, 68),
                        "langue": langue,
                        "niveau_initial": "DEBUTANT",
                        "niveau_atteint": "INTERMEDIAIRE" if progression > 50 else "DEBUTANT",
                        "progression_pourcentage": progression,
                        "certifie": progression >= 90,
                    }
                )

    await ctx.inserer(CentreAlphabetisation, centres)
    await ctx.inserer(ParcoursAlphabetisation, parcours)


async def _projets_et_recherche(ctx: ContexteSeed) -> None:
    """Projets collaboratifs, laboratoires, chercheurs et publications."""
    projets, membres, jalons = [], [], []
    laboratoires, chercheurs, projets_recherche, publications = [], [], [], []

    enseignants = [
        enseignant
        for liste in ctx.cache("enseignants_par_etablissement").values()
        for enseignant in liste
    ]

    for numero in range(1, ctx.volumetrie.projets + 1):
        domaine = ctx.choix(scolaire.DOMAINES_PROJET)
        code_etablissement = ctx.choix(list(ctx.cache("etablissement_info")))
        info = ctx.cache("etablissement_info")[code_etablissement]
        id_projet = ctx.nouvel_id()
        statut = ctx.rng.choices(list(StatutProjet), weights=[8, 6, 10, 14, 34, 6, 18, 4])[0]

        projets.append(
            {
                "id": id_projet,
                "code": f"PRJ-{numero:05d}",
                "titre": f"{domaine} — initiative de {info['nom']}",
                "resume": f"Projet collaboratif autour de « {domaine} ».",
                "description": (
                    "Le projet associe apprenants, enseignants et partenaires autour "
                    "d'un objectif concret et mesurable, avec un impact local attendu."
                ),
                "domaine": domaine,
                "objectifs": "Concevoir, expérimenter et diffuser une solution adaptée.",
                "impact_attendu": "Amélioration mesurable des conditions d'apprentissage.",
                "etablissement_id": info["id"],
                "statut": statut,
                "date_debut": date.today() - timedelta(days=ctx.entier(30, 500)),
                "date_fin_prevue": date.today() + timedelta(days=ctx.entier(30, 400)),
                "budget_prevu": float(ctx.entier(150_000, 8_000_000)),
                "budget_obtenu": float(ctx.entier(0, 6_000_000)),
                "competences_recherchees": ctx.choix(
                    ["Programmation, design", "Agronomie, gestion", "Communication, terrain"]
                ),
                "places_disponibles": ctx.entier(0, 8),
                "avancement_pourcentage": round(ctx.rng.uniform(0, 100), 1),
                "ouvert_candidatures": ctx.probabilite(0.6),
            }
        )

        equipe = ctx.echantillon(
            ctx.cache("apprenants_par_etablissement").get(code_etablissement, []), 5
        )
        for rang, membre in enumerate(equipe):
            membres.append(
                {
                    "id": ctx.nouvel_id(),
                    "projet_id": id_projet,
                    "apprenant_id": membre["id"],
                    "utilisateur_id": membre.get("utilisateur_id"),
                    "nom_complet": f"{membre['prenoms']} {membre['nom']}",
                    "role": RoleMembreProjet.PORTEUR if rang == 0 else RoleMembreProjet.MEMBRE,
                    "competences": "Travail d'équipe, rigueur",
                    "date_adhesion": date.today() - timedelta(days=ctx.entier(10, 300)),
                    "actif": True,
                }
            )
        if enseignants:
            encadreur = ctx.choix(enseignants)
            membres.append(
                {
                    "id": ctx.nouvel_id(),
                    "projet_id": id_projet,
                    "enseignant_id": encadreur["id"],
                    "nom_complet": encadreur["nom_complet"],
                    "role": RoleMembreProjet.ENCADREUR,
                    "actif": True,
                }
            )

        for rang in range(1, ctx.entier(2, 5)):
            echeance = date.today() + timedelta(days=rang * ctx.entier(20, 60))
            jalons.append(
                {
                    "id": ctx.nouvel_id(),
                    "projet_id": id_projet,
                    "libelle": f"Jalon {rang}",
                    "description": "Livrable attendu à cette échéance.",
                    "echeance": echeance,
                    "atteint": echeance < date.today(),
                    "date_realisation": echeance if echeance < date.today() else None,
                }
            )

    for numero, code_etablissement in enumerate(_universites(ctx), start=1):
        info = ctx.cache("etablissement_info")[code_etablissement]
        for index in range(ctx.entier(1, 4)):
            id_labo = ctx.nouvel_id()
            domaine = ctx.choix(scolaire.DOMAINES_PROJET)
            effectif_labo = ctx.entier(3, 8)
            laboratoires.append(
                {
                    "id": id_labo,
                    "code": f"LAB-{numero:02d}{index:02d}",
                    "nom": f"Laboratoire de {domaine}",
                    "etablissement_id": info["id"],
                    "domaines": domaine,
                    "directeur_nom": f"Pr. {ctx.identite('MASCULIN')[0]}",
                    # Le compteur reflète les chercheurs réellement créés : un
                    # tirage indépendant ferait mentir l'affichage.
                    "nombre_chercheurs": effectif_labo,
                    "actif": True,
                }
            )

            equipe_recherche = []
            for _ in range(effectif_labo):
                id_chercheur = ctx.nouvel_id()
                sexe = ctx.sexe(0.3)
                nom, prenoms = ctx.identite(sexe)
                equipe_recherche.append(id_chercheur)
                chercheurs.append(
                    {
                        "id": id_chercheur,
                        "laboratoire_id": id_labo,
                        "nom_complet": f"{prenoms} {nom}",
                        "grade": ctx.choix(
                            ["Assistant", "Maître-assistant", "Maître de conférences", "Professeur"]
                        ),
                        "specialite": domaine,
                        "indice_h": ctx.entier(0, 28),
                        "nombre_publications": ctx.entier(0, 60),
                    }
                )

            id_projet_recherche = ctx.nouvel_id()
            projets_recherche.append(
                {
                    "id": id_projet_recherche,
                    "code": f"PRE-{numero:02d}{index:02d}",
                    "titre": f"Recherche appliquée en {domaine.lower()}",
                    "laboratoire_id": id_labo,
                    "responsable_id": equipe_recherche[0] if equipe_recherche else None,
                    "domaine": domaine,
                    "resume": "Programme de recherche pluriannuel à visée appliquée.",
                    "date_debut": date.today() - timedelta(days=ctx.entier(100, 900)),
                    "date_fin": date.today() + timedelta(days=ctx.entier(100, 900)),
                    "financement": float(ctx.entier(1_000_000, 90_000_000)),
                    "bailleur": ctx.choix(
                        [
                            "Fonds national de la recherche",
                            "Coopération internationale",
                            "Université",
                        ]
                    ),
                    "statut": StatutProjet.EN_COURS,
                }
            )

            for _ in range(ctx.entier(1, 5)):
                publications.append(
                    {
                        "id": ctx.nouvel_id(),
                        "titre": f"Étude sur {domaine.lower()} au Bénin",
                        "type_publication": ctx.choix(
                            ["ARTICLE", "THESE", "MEMOIRE", "COMMUNICATION", "OUVRAGE"]
                        ),
                        "auteur_principal_id": ctx.choix(equipe_recherche)
                        if equipe_recherche
                        else None,
                        "projet_recherche_id": id_projet_recherche,
                        "revue": ctx.choix(
                            ["Revue africaine des sciences", "Annales de l'UAC", "Cahiers du CBRSI"]
                        ),
                        "annee": ctx.entier(2015, date.today().year),
                        "doi": f"10.{ctx.entier(1000, 9999)}/eduhub.{ctx.entier(1000, 9999)}",
                        "resume": "Résumé scientifique de la publication.",
                        "mots_cles": domaine,
                        "acces_libre": ctx.probabilite(0.7),
                        "nombre_citations": ctx.entier(0, 120),
                    }
                )

    await ctx.inserer(Projet, projets)
    await ctx.inserer(MembreProjet, membres)
    await ctx.inserer(JalonProjet, jalons)
    await ctx.inserer(Laboratoire, laboratoires)
    await ctx.inserer(Chercheur, chercheurs)
    await ctx.inserer(ProjetRecherche, projets_recherche)
    await ctx.inserer(Publication, publications)


async def _entreprises_stages_emploi(ctx: ContexteSeed) -> None:
    """Entreprises partenaires, offres, candidatures, stages et compétences."""
    entreprises, offres, candidatures, stages, competences = [], [], [], [], []

    apprenants_ages = [
        membre
        for liste in ctx.cache("apprenants_par_etablissement").values()
        for membre in liste
        if membre["age"] >= 16
    ]

    for numero in range(1, ctx.volumetrie.entreprises + 1):
        secteur = ctx.choix(scolaire.SECTEURS_ENTREPRISE)
        code_departement = ctx.choix([c for c, _, _, _, _ in donnees.DEPARTEMENTS])
        code_commune = ctx.choix(ctx.cache("communes_par_departement")[code_departement])
        id_entreprise = ctx.nouvel_id()
        raison = (
            f"{ctx.choix(['Société', 'Groupe', 'Établissements', 'Compagnie'])} "
            f"{ctx.choix(scolaire.NOMS).title()}"
        )

        entreprises.append(
            {
                "id": id_entreprise,
                "code": f"ENT-{numero:04d}",
                "raison_sociale": raison,
                "sigle": raison.split()[-1][:6].upper(),
                "secteur_activite": secteur,
                "ifu": f"{ctx.entier(1000000000000, 9999999999999)}",
                "commune_id": ctx.recuperer("commune", code_commune),
                "adresse": _libelle_commune(code_commune),
                "telephone": ctx.telephone(),
                "email": f"contact@ent{numero:04d}.bj",
                "effectif": ctx.entier(5, 900),
                "contact_nom": f"{ctx.identite('FEMININ')[1]} {ctx.identite('FEMININ')[0]}",
                "partenaire_officiel": ctx.probabilite(0.4),
                "accueille_handicap": ctx.probabilite(0.3),
                "actif": True,
            }
        )

        for index in range(ctx.entier(1, 5)):
            id_offre = ctx.nouvel_id()
            type_contrat = ctx.rng.choices(list(TypeContrat), weights=[45, 22, 14, 10, 4, 3, 2])[0]
            places = ctx.entier(1, 6)
            offres.append(
                {
                    "id": id_offre,
                    "reference": f"OFF-{numero:04d}-{index + 1:02d}",
                    "intitule": f"{'Stage' if type_contrat is TypeContrat.STAGE else 'Poste'} "
                    f"en {secteur.lower()}",
                    "entreprise_id": id_entreprise,
                    "type_contrat": type_contrat,
                    "description": f"Mission au sein du service {secteur.lower()}.",
                    "missions": "Participer aux activités du service et produire un rapport.",
                    "competences_requises": "Autonomie, rigueur, esprit d'équipe",
                    "niveau_requis": ctx.choix(["BEPC", "Baccalauréat", "Licence", "Master"]),
                    "domaine": secteur,
                    "lieu": _libelle_commune(code_commune),
                    "commune_id": ctx.recuperer("commune", code_commune),
                    "duree_mois": ctx.entier(1, 24),
                    "gratification": float(ctx.entier(0, 250_000)),
                    "places": places,
                    "places_pourvues": 0,
                    "date_publication": date.today() - timedelta(days=ctx.entier(1, 180)),
                    "date_limite": date.today() + timedelta(days=ctx.entier(5, 90)),
                    "accessible_handicap": ctx.probabilite(0.25),
                    "ouverte": ctx.probabilite(0.75),
                }
            )

            for membre in ctx.echantillon(apprenants_ages, ctx.entier(1, 8)):
                statut = ctx.rng.choices(
                    list(StatutCandidature), weights=[8, 30, 22, 14, 12, 12, 2]
                )[0]
                candidatures.append(
                    {
                        "id": ctx.nouvel_id(),
                        "offre_id": id_offre,
                        "apprenant_id": membre["id"],
                        "statut": statut,
                        "lettre_motivation": "Je souhaite mettre en pratique mes acquis.",
                        "date_candidature": date.today() - timedelta(days=ctx.entier(1, 90)),
                        "date_reponse": date.today() - timedelta(days=ctx.entier(0, 30))
                        if statut in {StatutCandidature.ACCEPTEE, StatutCandidature.REFUSEE}
                        else None,
                    }
                )

                if statut is StatutCandidature.ACCEPTEE and type_contrat is TypeContrat.STAGE:
                    debut = date.today() - timedelta(days=ctx.entier(30, 180))
                    note_finale = round(ctx.rng.uniform(10, 19), 2)
                    stages.append(
                        {
                            "id": ctx.nouvel_id(),
                            "reference": f"STG-{ctx.suivant('stage'):06d}",
                            "apprenant_id": membre["id"],
                            "entreprise_id": id_entreprise,
                            "offre_id": id_offre,
                            "sujet": f"Contribution aux activités de {secteur.lower()}",
                            "tuteur_entreprise": f"{ctx.identite('MASCULIN')[1]} "
                            f"{ctx.identite('MASCULIN')[0]}",
                            "date_debut": debut,
                            "date_fin": debut + timedelta(days=ctx.entier(30, 180)),
                            "gratification": float(ctx.entier(0, 120_000)),
                            "convention_signee": True,
                            "note_entreprise": round(ctx.rng.uniform(10, 20), 2),
                            "note_rapport": round(ctx.rng.uniform(8, 20), 2),
                            "note_soutenance": round(ctx.rng.uniform(8, 20), 2),
                            "note_finale": note_finale,
                            "appreciation": "Stage satisfaisant, objectifs atteints.",
                            "valide": note_finale >= 10,
                        }
                    )

    for membre in _apprenants_echantillon(ctx, 0.05):
        for libelle in ctx.echantillon(
            [
                "Bureautique",
                "Programmation",
                "Communication écrite",
                "Travail d'équipe",
                "Analyse de données",
                "Langues étrangères",
                "Gestion de projet",
                "Comptabilité",
                "Dessin technique",
                "Agriculture durable",
            ],
            ctx.entier(1, 4),
        ):
            competences.append(
                {
                    "id": ctx.nouvel_id(),
                    "apprenant_id": membre["id"],
                    "libelle": libelle,
                    "categorie": "Compétence transversale",
                    "niveau": ctx.choix(["DEBUTANT", "INTERMEDIAIRE", "AVANCE"]),
                    "source": ctx.choix(["Scolarité", "Projet", "Stage", "Formation en ligne"]),
                    "date_acquisition": ctx.date_entre(
                        date.today() - timedelta(days=900), date.today()
                    ),
                }
            )

    await ctx.inserer(Entreprise, entreprises)
    await ctx.inserer(Offre, offres)
    await ctx.inserer(CandidatureOffre, candidatures)
    await ctx.inserer(Stage, stages)
    await ctx.inserer(CompetenceApprenant, competences)
