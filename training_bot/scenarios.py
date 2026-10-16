"""Scénarios d'entraînement : chaque fichier de test, les mots-clés qui le
désignent, et les mails "client" qui le réclament."""

SCENARIOS = {
    "devis": {
        "file": "devis-studio-nova.pdf",
        "label": "le devis",
        "keywords": ["devis", "prix", "tarif", "chiffrage"],
        "requests": [
            ("Devis site Studio Nova", "Salut,\n\nTu peux me renvoyer le devis pour le site ? Je dois le faire valider en interne demain.\n\nMerci !"),
            ("Re: prix du site", "Hello,\n\nJe ne retrouve plus le devis qu'on avait validé, tu peux me le renvoyer stp ?\n\nBonne journée"),
            ("Chiffrage", "Bonjour,\n\nPourrais-tu m'envoyer le devis à jour ? Notre comptable me le demande.\n\nCordialement"),
        ],
    },
    "facture": {
        "file": "facture-octobre-2026.pdf",
        "label": "la facture d'octobre",
        "keywords": ["facture", "octobre", "compta", "comptable"],
        "requests": [
            ("Facture octobre", "Bonjour,\n\nIl me manque ta facture d'octobre pour clôturer le mois. Tu peux me l'envoyer ?\n\nMerci"),
            ("Pièce manquante - compta", "Salut,\n\nPour la compta j'ai besoin de la facture d'octobre, tu me l'envoies quand tu peux ?\n\nA+"),
        ],
    },
    "contrat": {
        "file": "contrat-prestation-boulangeriemax.pdf",
        "label": "le contrat de prestation",
        "keywords": ["contrat", "signature", "prestation"],
        "requests": [
            ("Contrat BoulangerieMax", "Coucou,\n\nTu peux me renvoyer le contrat de prestation ? Je dois le faire signer par mon associé.\n\nMerci beaucoup"),
            ("Re: signature contrat", "Bonjour,\n\nJe n'ai pas reçu le contrat, tu peux me le renvoyer en PDF ?\n\nBonne fin de journée"),
        ],
    },
    "cahier": {
        "file": "cahier-des-charges-site-vitrine.pdf",
        "label": "le cahier des charges",
        "keywords": ["cahier des charges", "specs", "spécifications", "fonctionnalités"],
        "requests": [
            ("Cahier des charges", "Salut,\n\nTu peux m'envoyer le cahier des charges du site vitrine ? Je veux le montrer au graphiste.\n\nMerci"),
            ("Specs du site", "Hello,\n\nOn fait le point vendredi, tu peux m'envoyer le cahier des charges avant ?\n\nMerci d'avance"),
        ],
    },
    "maquette": {
        "file": "maquette-accueil-v2.pdf",
        "label": "la maquette de la page d'accueil",
        "keywords": ["maquette", "design", "mockup", "accueil"],
        "requests": [
            ("Maquette v2", "Salut,\n\nTu peux me partager la maquette v2 de la page d'accueil ? Je veux avoir l'avis de l'équipe.\n\nMerci !"),
            ("Re: design accueil", "Bonjour,\n\nPourrais-tu me renvoyer la dernière maquette de l'accueil ?\n\nCordialement"),
        ],
    },
    "planning": {
        "file": "planning-projet-novembre.pdf",
        "label": "le planning du projet",
        "keywords": ["planning", "échéances", "calendrier", "dates"],
        "requests": [
            ("Planning projet", "Hello,\n\nTu peux m'envoyer le planning du projet avec les échéances de novembre ?\n\nMerci"),
            ("Dates de livraison", "Bonjour,\n\nJ'aurais besoin du planning à jour pour caler nos réunions. Tu me l'envoies ?\n\nBonne journée"),
        ],
    },
}


def match_scenario(text):
    """Renvoie la clé du scénario dont les mots-clés apparaissent le plus dans le texte."""
    text = text.lower()
    scores = {k: sum(text.count(kw) for kw in s["keywords"]) for k, s in SCENARIOS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None
