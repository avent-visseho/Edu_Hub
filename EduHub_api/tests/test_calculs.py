"""Tests des calculs académiques — la partie la plus sensible du système."""

from __future__ import annotations

import pytest

from app.utils.calculs import (
    ElementNote,
    calculer_rangs,
    determiner_mention,
    ecart_type,
    moyenne_ponderee,
    ramener_sur_20,
    taux,
    totaux_ponderes,
)


def test_moyenne_ponderee_applique_les_coefficients():
    # 18×4 + 16×3 + 17×2 = 154, sur 9 coefficients.
    elements = [ElementNote(18, 4), ElementNote(16, 3), ElementNote(17, 2)]
    assert moyenne_ponderee(elements) == pytest.approx(17.11, abs=0.01)


def test_moyenne_ponderee_ignore_les_notes_absentes():
    elements = [ElementNote(12, 2), ElementNote(None, 3)]  # type: ignore[arg-type]
    assert moyenne_ponderee(elements) == 12.0


def test_moyenne_ponderee_sans_element_vaut_none():
    assert moyenne_ponderee([]) is None


def test_totaux_ponderes():
    points, coefficients = totaux_ponderes([ElementNote(15, 2), ElementNote(10, 3)])
    assert (points, coefficients) == (60.0, 5.0)


def test_ramener_sur_20_convertit_le_bareme():
    assert ramener_sur_20(30, 40) == 15.0
    assert ramener_sur_20(12, 20) == 12.0


def test_ramener_sur_20_tolere_un_bareme_nul():
    assert ramener_sur_20(12, 0) == 12.0


def test_calculer_rangs_partage_le_rang_des_ex_aequo():
    rangs = calculer_rangs({"a": 15, "b": 18, "c": 15, "d": 9})
    assert rangs["b"] == 1
    assert rangs["a"] == rangs["c"] == 2
    assert rangs["d"] == 4


def test_calculer_rangs_classe_les_valeurs_manquantes_en_dernier():
    rangs = calculer_rangs({"a": 12, "b": None})
    assert rangs["a"] == 1
    assert rangs["b"] == 2


def test_determiner_mention_sur_le_bareme_par_defaut():
    assert determiner_mention(18.5) == "Excellent"
    assert determiner_mention(16.0) == "Très bien"
    assert determiner_mention(10.0) == "Passable"
    assert determiner_mention(9.9) is None


def test_determiner_mention_avec_un_bareme_propre_a_l_examen():
    bareme = [(10.0, 14.0, "Admis"), (14.0, 20.0, "Admis avec félicitations")]
    assert determiner_mention(15.0, bareme) == "Admis avec félicitations"


def test_ecart_type():
    assert ecart_type([10, 10, 10]) == 0.0
    assert ecart_type([8, 12]) == 2.0
    assert ecart_type([15]) is None


def test_taux_est_robuste_au_denominateur_nul():
    assert taux(5, 0) == 0.0
    assert taux(1, 4) == 25.0
