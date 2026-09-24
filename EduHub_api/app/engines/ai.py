"""Moteur d'assistance — recherche en langage naturel et aide à la décision.

L'assistant n'appelle aucun service externe : il traduit une phrase française
en filtres structurés à l'aide d'un analyseur lexical, puis laisse le moteur de
recherche exécuter la requête. C'est une couche supplémentaire, jamais une
dépendance du cœur métier.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.engines.search import Critere, Operateur


def normaliser(texte: str) -> str:
    """Minuscule, sans accent ni ponctuation superflue."""
    sans_accent = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texte.lower())
        if unicodedata.category(caractere) != "Mn"
    )
    return re.sub(r"\s+", " ", sans_accent).strip()


#: Entités reconnues et mots-clés qui les désignent.
ENTITES: dict[str, tuple[str, ...]] = {
    "apprenants": ("eleve", "eleves", "etudiant", "etudiants", "apprenant", "apprenants"),
    "enseignants": ("enseignant", "enseignants", "professeur", "professeurs", "instituteur"),
    "etablissements": ("etablissement", "etablissements", "ecole", "ecoles", "lycee", "college"),
    "candidats": ("candidat", "candidats"),
    "resultats": ("resultat", "resultats", "admis", "laureat", "laureats"),
    "classes": ("classe", "classes"),
    "projets": ("projet", "projets"),
}

#: Types d'établissement détectables dans une phrase.
TYPES_ETABLISSEMENT: dict[str, str] = {
    "ceg": "CEG",
    "epp": "EPP",
    "lycee": "LYCEE",
    "lycees": "LYCEE",
    "universite": "UNIVERSITE",
    "universites": "UNIVERSITE",
    "cfp": "CFP",
    "cep": "EPP",
}

#: Départements du Bénin et leurs variantes orthographiques.
DEPARTEMENTS: dict[str, str] = {
    "alibori": "ALIBORI",
    "atacora": "ATACORA",
    "atlantique": "ATLANTIQUE",
    "borgou": "BORGOU",
    "collines": "COLLINES",
    "couffo": "COUFFO",
    "donga": "DONGA",
    "littoral": "LITTORAL",
    "mono": "MONO",
    "oueme": "OUEME",
    "plateau": "PLATEAU",
    "zou": "ZOU",
}

#: Villes fréquemment citées et leur département de rattachement.
VILLES: dict[str, str] = {
    "cotonou": "LITTORAL",
    "porto-novo": "OUEME",
    "porto novo": "OUEME",
    "parakou": "BORGOU",
    "abomey-calavi": "ATLANTIQUE",
    "abomey calavi": "ATLANTIQUE",
    "bohicon": "ZOU",
    "natitingou": "ATACORA",
    "lokossa": "MONO",
    "djougou": "DONGA",
    "kandi": "ALIBORI",
    "dassa": "COLLINES",
    "aplahoue": "COUFFO",
    "pobe": "PLATEAU",
}

#: Examens reconnus.
EXAMENS: tuple[str, ...] = ("cep", "bepc", "bac", "baccalaureat")

#: Matières reconnues et leur code.
MATIERES: dict[str, str] = {
    "mathematiques": "MATH",
    "maths": "MATH",
    "math": "MATH",
    "francais": "FRA",
    "anglais": "ANG",
    "svt": "SVT",
    "physique": "PC",
    "physique-chimie": "PC",
    "histoire": "HG",
    "geographie": "HG",
    "philosophie": "PHILO",
    "informatique": "INFO",
}

_COMPARATEURS: tuple[tuple[str, Operateur], ...] = (
    ("au moins", Operateur.SUPERIEUR_EGAL),
    ("superieure ou egale", Operateur.SUPERIEUR_EGAL),
    ("superieur ou egal", Operateur.SUPERIEUR_EGAL),
    ("au moins egal", Operateur.SUPERIEUR_EGAL),
    ("plus grand ou egal", Operateur.SUPERIEUR_EGAL),
    ("pas moins de", Operateur.SUPERIEUR_EGAL),
    ("au plus", Operateur.INFERIEUR_EGAL),
    ("inferieur ou egal", Operateur.INFERIEUR_EGAL),
    ("inferieure ou egale", Operateur.INFERIEUR_EGAL),
    ("moins de", Operateur.INFERIEUR),
    ("inferieur a", Operateur.INFERIEUR),
    ("inferieure a", Operateur.INFERIEUR),
    ("plus de", Operateur.SUPERIEUR),
    ("superieur a", Operateur.SUPERIEUR),
    ("superieure a", Operateur.SUPERIEUR),
    ("depasse", Operateur.SUPERIEUR),
    ("au dessus de", Operateur.SUPERIEUR),
    ("en dessous de", Operateur.INFERIEUR),
    (">=", Operateur.SUPERIEUR_EGAL),
    ("<=", Operateur.INFERIEUR_EGAL),
    (">", Operateur.SUPERIEUR),
    ("<", Operateur.INFERIEUR),
)


@dataclass(slots=True)
class Interpretation:
    """Traduction structurée d'une question en langage naturel."""

    question: str
    entite: str
    criteres: list[Critere] = field(default_factory=list)
    explications: list[str] = field(default_factory=list)
    confiance: float = 0.0

    def en_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "entite": self.entite,
            "confiance": round(self.confiance, 2),
            "explications": self.explications,
            "filtres": [
                {"champ": c.champ, "operateur": c.operateur.value, "valeur": c.valeur}
                for c in self.criteres
            ],
        }


def _detecter_entite(texte: str) -> tuple[str, float]:
    """Retient l'entité dont le mot-clé apparaît le plus tôt — le sujet de la phrase."""
    meilleure: tuple[int, str] | None = None
    for entite, mots in ENTITES.items():
        for mot in mots:
            correspondance = re.search(rf"\b{re.escape(mot)}\b", texte)
            if correspondance is None:
                continue
            candidat = (correspondance.start(), entite)
            if meilleure is None or candidat[0] < meilleure[0]:
                meilleure = candidat
    if meilleure is None:
        return "apprenants", 0.1
    return meilleure[1], 0.3


def _operateur_avant(texte: str, position: int) -> Operateur:
    """Déduit l'opérateur de comparaison précédant un nombre.

    C'est l'expression la plus proche du nombre qui l'emporte : dans « moins de
    8 en mathématiques et plus de 15 en français », le second nombre reçoit bien
    l'opérateur « supérieur ».
    """
    contexte = texte[max(0, position - 40) : position]
    meilleur: tuple[int, Operateur] | None = None
    for expression, operateur in _COMPARATEURS:
        index = contexte.rfind(expression)
        if index == -1:
            continue
        if meilleur is None or index > meilleur[0]:
            meilleur = (index, operateur)
    return meilleur[1] if meilleur else Operateur.SUPERIEUR_EGAL


def _intervalles(texte: str) -> list[tuple[int, int, float, float]]:
    """Repère les expressions « entre X et Y » et renvoie leurs bornes."""
    resultats: list[tuple[int, int, float, float]] = []
    motif = r"entre\s+(\d+(?:[.,]\d+)?)\s+et\s+(\d+(?:[.,]\d+)?)"
    for correspondance in re.finditer(motif, texte):
        basse = float(correspondance.group(1).replace(",", "."))
        haute = float(correspondance.group(2).replace(",", "."))
        resultats.append((correspondance.start(), correspondance.end(), basse, haute))
    return resultats


#: Sujets numériques reconnus, du plus spécifique au plus général.
SUJETS_NUMERIQUES: tuple[tuple[str, str], ...] = (
    ("moyenne", "moyenne"),
    ("reussite", "taux_reussite"),
    ("echec", "taux_echec"),
    ("absence", "taux_absence"),
    ("salle", "nombre_salles"),
    ("classe", "nombre_classes"),
    ("enseignant", "nombre_enseignants"),
    ("eleve", "effectif"),
    ("etudiant", "effectif"),
    ("apprenant", "effectif"),
    ("effectif", "effectif"),
    ("candidat", "nombre_candidats"),
    ("place", "nombre_places"),
)


@dataclass(slots=True)
class ValeurNumerique:
    """Nombre extrait de la phrase, avec son opérateur et le sujet qu'il qualifie."""

    valeur: float
    operateur: Operateur
    sujet: str | None
    contexte: str
    borne_haute: float | None = None

    @property
    def valeur_critere(self) -> float | list[float]:
        """Valeur transmise au critère : une borne unique ou un intervalle."""
        if self.operateur is Operateur.ENTRE and self.borne_haute is not None:
            return [self.valeur, self.borne_haute]
        return self.valeur

    def formater(self) -> str:
        if self.operateur is Operateur.ENTRE and self.borne_haute is not None:
            return f"entre {self.valeur:g} et {self.borne_haute:g}"
        return f"{self.operateur.value} {self.valeur:g}"


def _sujet_le_plus_proche(texte: str, debut: int, fin: int) -> tuple[str | None, str]:
    """Trouve le mot-clé le plus proche du nombre, en privilégiant ce qui le suit.

    Dans « plus de 1 000 élèves mais moins de 20 salles », chaque nombre est
    rattaché au bon sujet ; dans « moins de 8 en mathématiques et plus de 15 en
    français », chaque note est rattachée à sa matière.
    """
    candidats: list[tuple[str, str]] = [
        *SUJETS_NUMERIQUES,
        *((mot, f"moyenne_matiere:{code}") for mot, code in MATIERES.items()),
    ]

    meilleur: tuple[int, str] | None = None
    for mot, sujet in candidats:
        for correspondance in re.finditer(rf"\b{re.escape(mot)}", texte):
            position = correspondance.start()
            if position >= fin:
                # Un sujet placé après le nombre le qualifie presque toujours.
                distance = (position - fin) * 2
            else:
                distance = (debut - correspondance.end()) * 3
            if distance < 0:
                continue
            if meilleur is None or distance < meilleur[0]:
                meilleur = (distance, sujet)

    # Le sujet doit rester dans la même proposition : environ 90 caractères
    # après le nombre, 60 avant, compte tenu des pondérations appliquées.
    contexte = texte[max(0, debut - 70) : min(len(texte), fin + 40)]
    if meilleur is None or meilleur[0] > 180:
        return None, contexte
    return meilleur[1], contexte


def _nombres_avec_contexte(texte: str) -> list[ValeurNumerique]:
    """Extrait les valeurs numériques, leur opérateur et le sujet qu'elles qualifient."""
    # Les séparateurs de milliers sont retirés au préalable : « 1 000 » → « 1000 ».
    texte = re.sub(r"(?<=\d) (?=\d{3}\b)", "", texte)

    resultats: list[ValeurNumerique] = []
    intervalles = _intervalles(texte)
    for depart, arrivee, basse, haute in intervalles:
        sujet, contexte = _sujet_le_plus_proche(texte, depart, arrivee)
        resultats.append(
            ValeurNumerique(basse, Operateur.ENTRE, sujet, contexte, borne_haute=haute)
        )

    for correspondance in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:/\s*20|%)?", texte):
        debut, fin = correspondance.start(), correspondance.end()
        if any(depart <= debut < arrivee for depart, arrivee, _, _ in intervalles):
            continue  # Borne déjà consommée par un intervalle.
        brut = correspondance.group(1).replace(",", ".")
        try:
            valeur = float(brut)
        except ValueError:
            continue
        sujet, contexte = _sujet_le_plus_proche(texte, debut, fin)
        resultats.append(ValeurNumerique(valeur, _operateur_avant(texte, debut), sujet, contexte))
    return resultats


def interpreter(question: str) -> Interpretation:
    """Traduit une question française en critères de recherche structurés.

    Exemple :
        « Montre-moi les élèves des CEG de Porto-Novo qui ont au moins 17 de
        moyenne en mathématiques. »
    devient :
        entite = apprenants
        type_etablissement = CEG, departement = OUEME, moyenne_matiere >= 17
    """
    texte = normaliser(question)
    entite, confiance = _detecter_entite(texte)
    interpretation = Interpretation(question=question, entite=entite, confiance=confiance)

    # --- Type d'établissement ---
    for mot, code in TYPES_ETABLISSEMENT.items():
        if re.search(rf"\b{re.escape(mot)}\b", texte):
            interpretation.criteres.append(Critere("type_etablissement", Operateur.EGAL, code))
            interpretation.explications.append(f"Type d'établissement détecté : {code}")
            interpretation.confiance += 0.2
            break

    # --- Territoire ---
    departement_trouve = None
    for mot, code in DEPARTEMENTS.items():
        if re.search(rf"\b{re.escape(mot)}\b", texte):
            departement_trouve = code
            break
    if departement_trouve is None:
        for ville, code in VILLES.items():
            if ville in texte:
                departement_trouve = code
                interpretation.criteres.append(Critere("commune", Operateur.CONTIENT, ville))
                interpretation.explications.append(f"Commune détectée : {ville}")
                break
    if departement_trouve:
        interpretation.criteres.append(Critere("departement", Operateur.EGAL, departement_trouve))
        interpretation.explications.append(f"Département détecté : {departement_trouve}")
        interpretation.confiance += 0.2

    # --- Examen ---
    for examen in EXAMENS:
        if re.search(rf"\b{re.escape(examen)}\b", texte):
            code = "BAC" if examen.startswith("bac") else examen.upper()
            interpretation.criteres.append(Critere("examen", Operateur.EGAL, code))
            interpretation.explications.append(f"Examen détecté : {code}")
            interpretation.confiance += 0.15
            break

    # --- Décision d'examen ---
    if re.search(r"\bnon[ -]?admis", texte) or re.search(r"\b(ajourne|recale)", texte):
        interpretation.criteres.append(Critere("decision", Operateur.EGAL, "NON_ADMIS"))
        interpretation.explications.append("Décision détectée : non admis")
        interpretation.confiance += 0.15
    elif re.search(r"\b(admis|laureat|recu)s?\b", texte):
        interpretation.criteres.append(Critere("decision", Operateur.EGAL, "ADMIS"))
        interpretation.explications.append("Décision détectée : admis")
        interpretation.confiance += 0.15

    # --- Sexe ---
    if re.search(r"\b(fille|filles)\b", texte):
        interpretation.criteres.append(Critere("sexe", Operateur.EGAL, "FEMININ"))
        interpretation.explications.append("Filtre sur le sexe : féminin")
    elif re.search(r"\b(garcon|garcons)\b", texte):
        interpretation.criteres.append(Critere("sexe", Operateur.EGAL, "MASCULIN"))
        interpretation.explications.append("Filtre sur le sexe : masculin")

    # --- Handicap et inclusion ---
    if re.search(r"\b(handicap|malvoyant|aveugle|sourd|inclusi)", texte):
        interpretation.criteres.append(Critere("handicap", Operateur.DIFFERENT, "AUCUN"))
        interpretation.explications.append("Filtre sur les besoins spécifiques")

    # --- Valeurs numériques contextualisées ---
    for nombre in _nombres_avec_contexte(texte):
        operateur, valeur, sujet = nombre.operateur, nombre.valeur, nombre.sujet

        if sujet and sujet.startswith("moyenne_matiere:") and valeur <= 20:
            matiere = sujet.split(":", 1)[1]
            interpretation.criteres.append(Critere(sujet, operateur, nombre.valeur_critere))
            interpretation.explications.append(f"Moyenne en {matiere} {nombre.formater()}")
            interpretation.confiance += 0.2
        elif sujet == "moyenne" and valeur <= 20:
            matiere = next((code for mot, code in MATIERES.items() if mot in nombre.contexte), None)
            champ = f"moyenne_matiere:{matiere}" if matiere else "moyenne_generale"
            interpretation.criteres.append(Critere(champ, operateur, nombre.valeur_critere))
            interpretation.explications.append(
                f"{'Moyenne en ' + matiere if matiere else 'Moyenne générale'} {nombre.formater()}"
            )
            interpretation.confiance += 0.25
        elif sujet in {"taux_reussite", "taux_echec", "taux_absence"}:
            interpretation.criteres.append(Critere(sujet, operateur, nombre.valeur_critere))
            interpretation.explications.append(
                f"{sujet.replace('_', ' ').capitalize()} {nombre.formater()} %"
            )
            interpretation.confiance += 0.2
        elif sujet is not None:
            interpretation.criteres.append(Critere(sujet, operateur, nombre.valeur_critere))
            interpretation.explications.append(
                f"{sujet.replace('_', ' ').capitalize()} {nombre.formater()}"
            )
            interpretation.confiance += 0.15
        elif 1990 <= valeur <= 2100:
            interpretation.criteres.append(Critere("annee", Operateur.EGAL, int(valeur)))
            interpretation.explications.append(f"Année détectée : {int(valeur)}")

    if not interpretation.criteres:
        interpretation.explications.append(
            "Aucun filtre n'a pu être déduit : la recherche portera sur l'ensemble des données."
        )

    interpretation.confiance = min(interpretation.confiance, 1.0)
    return interpretation


def suggestions() -> list[str]:
    """Exemples de questions proposés à l'utilisateur."""
    return [
        "Montre-moi les élèves des CEG de Porto-Novo ayant au moins 17 de moyenne "
        "en mathématiques.",
        "Quels établissements ont un taux de réussite inférieur à 50 % au BEPC ?",
        "Quels établissements du Littoral ont plus de 1 000 élèves mais moins de 20 salles ?",
        "Affiche les élèves de l'Atlantique ayant une moyenne générale supérieure ou égale à 18.",
        "Liste les filles admises au BAC avec plus de 16 de moyenne.",
        "Quels élèves ont plus de 20 % d'absences ?",
        "Montre les apprenants en situation de handicap inscrits cette année.",
    ]
