# Bot d'entraînement screenpipe

Simule le workflow « un client réclame un fichier → je le retrouve dans l'Explorateur → je le glisse dans Gmail → je réponds », pour que screenpipe l'enregistre.

## Setup (une fois)

```bash
pip install -r requirements.txt
python make_test_files.py        # crée Documents\Freelance-Demo\*.pdf
copy .env.example .env           # puis remplir .env
python reply_bot.py --login      # Brave s'ouvre, connecte-toi au compte démo à la main
```

- SMTP via Brevo (gratuit, 300 mails/jour) : créer un compte, valider l'adresse `SENDER_EMAIL` dans *Expéditeurs*, puis copier login + clé dans *SMTP & API > SMTP*. Au 1er mail reçu, s'il tombe en spam, clique « Non spam » dans le compte démo.
- La session Google reste dans `browser_profile/`, pas besoin de se reconnecter ensuite.

## Lancer

```bash
python send_requests.py devis    # envoie 1 demande (devis, facture, contrat, cahier, maquette, planning)
python reply_bot.py              # traite le dernier mail reçu
python run_training.py -n 10     # boucle complète : demande -> attente -> réponse, x10
```

- Ne touche pas la souris pendant un cycle. Arrêt d'urgence : souris dans le coin haut-gauche.
- Chaque traitement est tracé dans `scenarios_log.jsonl` (heure, fichier, réponse), c'est la vérité terrain pour vérifier ce que screenpipe retrouve.
