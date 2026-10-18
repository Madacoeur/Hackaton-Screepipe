# Déjà-vu — show once, run forever

Agent mail qui **refait ce que screenpipe t'a vu faire** (ouvrir le mail, prendre le bon PDF dans l'Explorateur, le glisser dans Gmail, répondre) et **répond avec ce que tu sais** (prix, dates, agenda vus à l'écran), en citant ses sources. Brouillons par défaut, envoi auto au-dessus de 80/100, jamais sur un mail d'argent ou juridique.

## Lancer (au quotidien)

Double-clic sur **`Deja-vu.pyw`**. Aucune fenêtre de terminal : il vérifie screenpipe, démarre l'interface et le service de l'agent en arrière-plan, puis ouvre http://localhost:3000.

- Arrêter : `python Deja-vu.pyw stop`
- Fréquence de l'agent : `agent/config.json` → `"every_minutes": 15` (0 = seulement à la demande, bouton « Traiter maintenant »)
- Journaux : dossier `logs/`

## Installation de zéro (Windows)

Prérequis : Python 3.12, Node.js 20+, Brave, l'app **screenpipe** installée et lancée.

1. **Dépendances**
   ```bash
   pip install -r training_bot/requirements.txt
   ```
   ```bash
   npm --prefix ui install
   ```
2. **Configuration** : copier `training_bot/.env.example` en `training_bot/.env`, remplir `DEMO_EMAIL`, `SIGNATURE` et `SCREENPIPE_LOCAL_API_KEY` (le fichier explique comment obtenir le token).
3. **screenpipe** : dans ses réglages, couper l'audio si la machine a un GPU AMD (le pilote Vulkan fait planter la transcription). Garder les pipes `mail-autopilot` et `workflow-*` **désactivées** : le service de Déjà-vu les remplace et elles ouvrent des consoles.
4. **Connexion Gmail (une fois)** : `python training_bot/reply_bot.py --login`, se connecter au compte démo dans la fenêtre Brave. La session reste dans `training_bot/browser_profile/` (hors git).
5. **Fichiers de démo** : `python training_bot/make_test_files.py` (crée `Documents\Freelance-Demo\*.pdf`).
6. **Apprentissage** (montrer le geste à screenpipe, puis en tirer les playbooks) :
   ```bash
   python training_bot/run_training.py --minutes 30
   ```
   ```bash
   python training_bot/context_bot.py --minutes 30
   ```
   ```bash
   python agent/extract_playbooks.py
   ```
   Les playbooks fournis dans `agent/playbooks/` suffisent pour la démo si on saute cette étape.
7. **Lancer** : double-clic sur `Deja-vu.pyw`.

## Organisation

| Dossier | Rôle |
|---|---|
| `agent/` | l'agent : playbooks appris, rejeu du geste, contexte screenpipe, score de confiance, preuves, envoi validé, service |
| `ui/` | l'interface Next.js (file, brouillon, « ce que je me suis rappelé », preuves, Répondre à tous) |
| `training_bot/` | bots d'entraînement (geste Gmail, contexte à l'écran), connexion Gmail, garde screenpipe |
| `DEMO.md`, `PITCH.md` | script de démo (FR) et pitch oral (EN) |
