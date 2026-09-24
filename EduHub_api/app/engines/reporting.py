"""Moteur de restitution — génération de PDF et de QR codes."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLEU = colors.HexColor("#1B4F8A")
VERT = colors.HexColor("#0F7B4F")
GRIS = colors.HexColor("#F1F4F8")
GRIS_TEXTE = colors.HexColor("#4A5568")


@dataclass(slots=True)
class EnTeteDocument:
    """En-tête administratif commun à tous les documents officiels."""

    republique: str = "République du Bénin"
    ministere: str = ""
    direction: str = ""
    etablissement: str = ""
    titre: str = ""
    sous_titre: str = ""


@dataclass(slots=True)
class BlocTableau:
    """Tableau à insérer dans un document."""

    entetes: list[str]
    lignes: list[list[str]]
    largeurs: list[float] | None = None
    alignements: dict[int, str] = field(default_factory=dict)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titre": ParagraphStyle(
            "TitreEduHub",
            parent=base["Title"],
            fontSize=16,
            textColor=BLEU,
            spaceAfter=4,
        ),
        "sous_titre": ParagraphStyle(
            "SousTitreEduHub",
            parent=base["Normal"],
            fontSize=11,
            alignment=1,
            textColor=GRIS_TEXTE,
            spaceAfter=10,
        ),
        "entete": ParagraphStyle(
            "EnteteEduHub",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=GRIS_TEXTE,
        ),
        "normal": ParagraphStyle("NormalEduHub", parent=base["Normal"], fontSize=10, leading=14),
        "petit": ParagraphStyle(
            "PetitEduHub", parent=base["Normal"], fontSize=8, textColor=GRIS_TEXTE
        ),
    }


def generer_qr_code(donnees: str, taille_px: int = 180) -> bytes:
    """Produit un QR code PNG encodant un code de vérification ou une URL."""
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(donnees)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").resize((taille_px, taille_px))
    tampon = io.BytesIO()
    image.save(tampon, format="PNG")
    return tampon.getvalue()


def _bloc_entete(entete: EnTeteDocument, styles: dict[str, ParagraphStyle]) -> list[Any]:
    lignes = [entete.republique]
    for valeur in (entete.ministere, entete.direction, entete.etablissement):
        if valeur:
            lignes.append(valeur)
    elements: list[Any] = [
        Paragraph("<br/>".join(lignes), styles["entete"]),
        Spacer(1, 8 * mm),
    ]
    if entete.titre:
        elements.append(Paragraph(entete.titre.upper(), styles["titre"]))
    if entete.sous_titre:
        elements.append(Paragraph(entete.sous_titre, styles["sous_titre"]))
    return elements


def _table(bloc: BlocTableau, largeur_totale: float) -> Table:
    donnees = [bloc.entetes, *bloc.lignes]
    largeurs = bloc.largeurs
    if largeurs is None:
        largeurs = [largeur_totale / len(bloc.entetes)] * len(bloc.entetes)

    table = Table(donnees, colWidths=largeurs, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BLEU),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D2E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for colonne, alignement in bloc.alignements.items():
        style.append(("ALIGN", (colonne, 1), (colonne, -1), alignement.upper()))
    table.setStyle(TableStyle(style))
    return table


def generer_document(
    entete: EnTeteDocument,
    sections: list[Any],
    *,
    paysage: bool = False,
    pied_de_page: str | None = None,
    code_verification: str | None = None,
) -> bytes:
    """Assemble un document PDF à partir de sections hétérogènes.

    Une section peut être une chaîne (paragraphe), un `BlocTableau`, un
    dictionnaire (fiche clé/valeur) ou `None` (saut de page).
    """
    styles = _styles()
    format_page = landscape(A4) if paysage else A4
    largeur_utile = format_page[0] - 30 * mm

    tampon = io.BytesIO()
    document = SimpleDocTemplate(
        tampon,
        pagesize=format_page,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=entete.titre or "Document EduHub",
        author="EduHub",
    )

    elements: list[Any] = _bloc_entete(entete, styles)

    for section in sections:
        if section is None:
            elements.append(PageBreak())
        elif isinstance(section, BlocTableau):
            elements.extend([_table(section, largeur_utile), Spacer(1, 5 * mm)])
        elif isinstance(section, dict):
            bloc = BlocTableau(
                entetes=["Rubrique", "Valeur"],
                lignes=[[str(cle), str(valeur)] for cle, valeur in section.items()],
                largeurs=[largeur_utile * 0.35, largeur_utile * 0.65],
            )
            elements.extend([_table(bloc, largeur_utile), Spacer(1, 5 * mm)])
        else:
            elements.extend([Paragraph(str(section), styles["normal"]), Spacer(1, 3 * mm)])

    if code_verification:
        elements.append(Spacer(1, 6 * mm))
        elements.append(
            Image(io.BytesIO(generer_qr_code(code_verification)), width=28 * mm, height=28 * mm)
        )
        elements.append(
            Paragraph(
                f"Code de vérification : <b>{code_verification}</b><br/>"
                "Ce document est vérifiable en ligne sur la plateforme EduHub.",
                styles["petit"],
            )
        )

    elements.append(Spacer(1, 5 * mm))
    elements.append(
        Paragraph(
            pied_de_page or f"Document généré le {date.today():%d/%m/%Y} par la plateforme EduHub.",
            styles["petit"],
        )
    )

    document.build(elements)
    return tampon.getvalue()


def exporter_csv(entetes: list[str], lignes: list[list[Any]], separateur: str = ";") -> bytes:
    """Export CSV compatible avec les tableurs francophones."""
    import csv

    tampon = io.StringIO()
    redacteur = csv.writer(tampon, delimiter=separateur, quoting=csv.QUOTE_MINIMAL)
    redacteur.writerow(entetes)
    for ligne in lignes:
        redacteur.writerow(["" if v is None else v for v in ligne])
    return tampon.getvalue().encode("utf-8-sig")
