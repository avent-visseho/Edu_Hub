"""Tests de l'interprétation des questions en français."""

from __future__ import annotations

from app.engines.ai import interpreter


def filtres(question: str) -> dict[str, tuple[str, object]]:
    interpretation = interpreter(question)
    return {c.champ: (c.operateur.value, c.valeur) for c in interpretation.criteres}


def test_detecte_le_type_d_etablissement_et_la_matiere():
    resultat = filtres(
        "Montre-moi les élèves des CEG de Porto-Novo qui ont au moins 17 de moyenne "
        "en mathématiques."
    )
    assert resultat["type_etablissement"] == ("eq", "CEG")
    assert resultat["departement"] == ("eq", "OUEME")
    assert resultat["moyenne_matiere:MATH"] == ("gte", 17.0)


def test_rattache_chaque_nombre_a_son_sujet():
    resultat = filtres("Quels établissements ont plus de 1 000 élèves mais moins de 20 salles ?")
    assert resultat["effectif"] == ("gt", 1000.0)
    assert resultat["nombre_salles"] == ("lt", 20.0)


def test_retient_l_operateur_le_plus_proche_du_nombre():
    resultat = filtres("Élèves ayant moins de 8 en mathématiques et plus de 15 en français")
    assert resultat["moyenne_matiere:MATH"] == ("lt", 8.0)
    assert resultat["moyenne_matiere:FRA"] == ("gt", 15.0)


def test_reconnait_un_intervalle():
    resultat = filtres("Candidats BEPC non admis avec une moyenne comprise entre 9 et 10")
    assert resultat["moyenne_generale"] == ("between", [9.0, 10.0])
    assert resultat["examen"] == ("eq", "BEPC")


def test_reconnait_le_taux_d_absence():
    resultat = filtres("Élèves avec plus de 20 % d'absences")
    assert resultat["taux_absence"] == ("gt", 20.0)


def test_identifie_l_entite_sujet_de_la_phrase():
    assert interpreter(
        "Quels établissements ont un taux de réussite inférieur à 50 % ?"
    ).entite == ("etablissements")
    assert interpreter("Liste les élèves de troisième").entite == "apprenants"


def test_sans_filtre_deductible_la_confiance_reste_faible():
    interpretation = interpreter("Bonjour")
    assert interpretation.criteres == []
    assert interpretation.confiance <= 0.5
