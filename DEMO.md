# Démo Déjà-vu Mail — 3 minutes

**Pitch en une phrase :** un agent mail qui ne devine pas : il refait ce que screenpipe t'a vu faire, et répond avec ce que tu as vu, preuves à l'appui.

## Avant de monter sur scène (10 min avant)

- [ ] PC branché, session déverrouillée, mise en veille désactivée (un PC verrouillé bloque Brave).
- [ ] screenpipe tourne : `curl localhost:3030/health` → `healthy`, `frame_status: ok`. L'audio reste coupé (pilote AMD).
- [ ] Brave ouvert sur Gmail (compte démo), **un seul onglet**.
- [ ] Interface lancée : `npm --prefix ui run dev` → http://localhost:3000, mode **« Je valide »**.
- [ ] Pipe `mail-autopilot` **en pause** pendant la démo (sinon elle peut se déclencher au mauvais moment) : app screenpipe → Pipes → mail-autopilot → désactiver. On déclenche à la main.
- [ ] Mail de démo prêt. Brevo est suspendu : **depuis ton Gmail perso**, envoie à hacktestazerty@gmail.com
      sujet **« Prix et livraison du site »**, texte *« Salut, tu peux me renvoyer le devis et me confirmer le prix et la date de livraison qu'on avait dit jeudi ? »*
      Envoie-le 2 min avant de passer et **ne l'ouvre pas** (il doit rester non lu).
- [ ] Plan B si le mail n'arrive pas : `python agent/run_agent.py --subject "Devis site Studio Nova"` (rejoue un mail de Karim déjà dans Gmail).
- [ ] Fenêtres Claude / terminal fermées ou sur un autre écran (screenpipe capture tout ce qui est à l'écran).

## Le déroulé

| Temps | À l'écran | Ce que tu dis |
|---|---|---|
| 0:00 | Gmail, le mail de Karim | « Répondre à un mail, c'est rarement écrire : c'est aller chercher le devis, retrouver le prix dit en réunion. L'info n'est pas dans ta boîte mail. Elle est dans ce que tu as vu. » |
| 0:20 | App screenpipe → **Workflows** : « Joindre au mail client le fichier PDF demandé » | « J'ai fait ce geste devant screenpipe une soixantaine de fois. Il l'a appris tout seul : c'est dans son catalogue de workflows, et dans sa mémoire. Show once, run forever. » |
| 0:45 | Interface → **Traiter maintenant** | « Je ne touche plus à rien. » La souris ouvre le mail, Répondre, l'Explorateur sur Freelance-Demo, glisse le devis dans Gmail, tape la réponse. Laisse-la faire en silence 5 secondes. |
| 1:35 | Interface : le brouillon | « Le brouillon est dans Gmail, dans mon style. Et regardez cette phrase : *pour rappel, on était partis sur 2 400 €*. » |
| 1:50 | Carte **« Ce que je me suis rappelé »** → clic sur la vignette | « Il ne l'a pas inventé : il l'a retrouvé dans screenpipe. Voilà la capture, l'heure, la fenêtre. Chaque info a sa source. » |
| 2:05 | Carte menthe **« Tu me l'as montré 14 fois »** → **Envoyer** | « Confiance 100 : même client, même demande, même fichier. En mode auto, il l'aurait envoyé seul. Là, je valide. » Montrer Gmail → Envoyés. |
| 2:25 | Clic sur **« Suite à notre échange »** | « Et s'il ne sait pas ? Expéditeur inconnu, ça parle de paiement : *celui-là, je te le laisse*. Un bouton : *montre-moi une fois*. Je le fais devant screenpipe, et la prochaine fois il saura. » |
| 2:45 | Retour sur le titre | « Tout tourne en local sur screenpipe : la capture, la mémoire, l'apprentissage des workflows, et l'agent qui est une pipe screenpipe. Gmail ou Superhuman voient ta boîte mail. Nous, on voit ton travail. » |

## Si quelque chose casse en direct

- **L'agent ne démarre pas** (Traiter maintenant ne fait rien) : lancer `python agent/run_agent.py --max 1` dans un terminal.
- **Brave ne répond plus** : fermer Brave, relancer `python training_bot/reply_bot.py --login` (la session Gmail est gardée).
- **screenpipe planté** : le relancer depuis le menu Démarrer ; `python training_bot/screenpipe_watchdog.py` le surveille.
- **Tout est cassé** : passer la vidéo de secours (ci-dessous).

## Vidéo de secours

Faire une répétition complète, puis exporter ce passage directement depuis screenpipe (il l'a enregistré) :

```bash
curl -X POST localhost:3030/export -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d "{\"start\": \"5m ago\", \"end\": \"now\"}"
```

(token : `bun x screenpipe@latest auth token`). Ou l'enregistreur Windows : `Win + Alt + R`.

## Questions probables du jury

- **« Pourquoi screenpipe et pas l'API Gmail ? »** L'API Gmail donne les mails, pas le contexte : le prix était dans des notes et un devis vus à l'écran, et le geste « Explorateur → glisser » n'existe que dans l'enregistrement.
- **« Et la vie privée ? »** Tout est local : base screenpipe sur le PC, agent local, envoi seulement après validation (ou auto au-dessus de 80/100, jamais sur un mail sensible).
- **« Il peut se tromper ? »** Il cite chaque fait avec sa capture, refuse ce qu'il n'a jamais vu, bloque les mails d'argent ou juridiques, et signale une info demandée qu'il n'a pas retrouvée.
- **« Ça marche hors démo ? »** Les workflows ont été appris sur ~80 exécutions et publiés par les pipes natives de screenpipe ; l'agent tourne en pipe screenpipe toutes les 15 min.
