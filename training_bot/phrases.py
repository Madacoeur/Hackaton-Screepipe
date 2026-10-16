"""Génère des réponses variées mais cohérentes, dans un ton freelance tutoyant."""
import random

GREETINGS = ["Salut {name},", "Hello {name},", "Coucou {name},", "Bonjour {name},", "Hey {name},"]

INTROS = [
    "Merci pour ton message.",
    "Bien reçu, merci !",
    "Pas de souci, je m'en occupe tout de suite.",
    "Oui bien sûr.",
    "Désolé pour le délai, la semaine a été chargée.",
    "Merci de m'avoir relancé.",
]

ATTACH = [
    "Tu trouveras {label} en pièce jointe.",
    "Je te mets {label} en PJ.",
    "Voici {label}, en pièce jointe.",
    "Je t'envoie {label} ci-joint.",
    "Tu as {label} en pièce jointe de ce mail.",
]

EXTRAS = [
    "C'est bien la dernière version.",
    "N'hésite pas si tu as des questions.",
    "Dis-moi si quelque chose ne va pas.",
    "Si tu veux qu'on en parle de vive voix, on peut s'appeler cette semaine.",
    "Je reste dispo si besoin de modifications.",
    "Tiens-moi au courant après lecture.",
    "Normalement tout y est, mais dis-moi s'il manque un élément.",
]

CLOSINGS = ["Bonne journée,", "A plus,", "Bonne fin de journée,", "A bientôt,", "Belle journée,", "Bonne soirée,"]


def build_reply(name, label, signature):
    lines = [
        random.choice(GREETINGS).format(name=name),
        "",
        random.choice(INTROS) + " " + random.choice(ATTACH).format(label=label),
    ]
    lines += random.sample(EXTRAS, k=random.randint(1, 2))
    lines += ["", random.choice(CLOSINGS), signature]
    return "\n".join(lines)


if __name__ == "__main__":
    for _ in range(3):
        print(build_reply("Karim", "le devis", "Table En"), "\n---")
