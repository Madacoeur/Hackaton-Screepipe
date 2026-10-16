"""Crée le dossier de fichiers de test (devis, facture, contrat...) en PDF."""
from fpdf import FPDF

from config import FILES_DIR
from scenarios import SCENARIOS

CONTENT = {
    "devis": [
        "DEVIS N° 2026-041",
        "Client : Studio Nova - Karim",
        "Objet : Refonte du site web vitrine",
        "",
        "Conception graphique (maquettes) ........ 600 EUR",
        "Intégration et développement ............ 1 400 EUR",
        "Mise en ligne et formation ................ 400 EUR",
        "",
        "TOTAL HT : 2 400 EUR",
        "Livraison prévue : 30 novembre 2026",
        "Validité du devis : 30 jours",
    ],
    "facture": [
        "FACTURE N° F-2026-10",
        "Période : octobre 2026",
        "Client : BoulangerieMax - Léa",
        "",
        "Maintenance site + correctifs formulaire ... 350 EUR",
        "Hébergement (1 mois) ......................... 25 EUR",
        "",
        "TOTAL HT : 375 EUR",
        "Échéance de paiement : 30 jours",
    ],
    "contrat": [
        "CONTRAT DE PRESTATION DE SERVICES",
        "Entre : Table En, développeur freelance",
        "Et : BoulangerieMax, représentée par Léa",
        "",
        "Article 1 - Objet : création d'un site de commande en ligne",
        "Article 2 - Durée : 3 mois à compter de la signature",
        "Article 3 - Rémunération : 3 200 EUR HT, payable en 2 fois",
        "Article 4 - Propriété : le code est cédé au client à paiement complet",
        "",
        "Fait en deux exemplaires.",
    ],
    "cahier": [
        "CAHIER DES CHARGES - SITE VITRINE",
        "",
        "1. Pages : Accueil, Services, Réalisations, Contact",
        "2. Formulaire de contact avec anti-spam",
        "3. Site responsive (mobile first)",
        "4. Back-office simple pour modifier les textes",
        "5. Référencement de base (balises, sitemap)",
        "6. Hébergement en France",
    ],
    "maquette": [
        "MAQUETTE PAGE D'ACCUEIL - V2",
        "",
        "- Header : logo à gauche, menu à droite, bouton 'Devis gratuit'",
        "- Hero : grande photo + accroche 'Votre projet, notre savoir-faire'",
        "- Section 3 colonnes : services principaux",
        "- Bandeau témoignages clients",
        "- Footer : coordonnées, réseaux sociaux, mentions légales",
        "",
        "Couleurs : bleu nuit #1B2A41, corail #FF6B5B",
    ],
    "planning": [
        "PLANNING PROJET - NOVEMBRE 2026",
        "",
        "03/11 : kick-off et validation cahier des charges",
        "10/11 : livraison maquettes",
        "17/11 : intégration pages principales",
        "24/11 : recette client",
        "30/11 : mise en ligne",
    ],
}


def make_pdf(path, lines):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, lines[0], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    for line in lines[1:]:
        pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def main():
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    for key, scenario in SCENARIOS.items():
        path = FILES_DIR / scenario["file"]
        make_pdf(path, CONTENT[key])
        print("créé", path)


if __name__ == "__main__":
    main()
