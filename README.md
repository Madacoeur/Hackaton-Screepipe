# Déjà-vu — show once, run forever

> A mail agent that doesn't guess: it **replays what screenpipe saw you do**, and **answers with what you saw**, with proof.

Built for the screenpipe hackathon *“Teach an agent your workflow”*.

A client emails: *“Can you resend the quote?”*. You've done this a hundred times: open the mail, hit Reply, open File Explorer, find the right PDF, drag it into Gmail, type a short answer, send. Déjà-vu watched you do it through **screenpipe**, learned the workflow, and now does it for you with the real mouse and keyboard, in your style. If the mail asks for something you saw on screen (a price, a delivery date, your availability), it finds it in screenpipe and quotes it, with the frame it came from.

## How it works

```
 Show once                 Learn                          Run forever
 ─────────                 ─────                          ───────────
 You handle mails     →    screenpipe records the    →    "Process now" (or the mail-autopilot pipe)
 while screenpipe          gesture; playbooks are         opens Gmail, replays the gesture,
 is recording              extracted from it               writes the reply, sends or drafts it
```

- **Learned workflows**: one playbook per request type (quote, invoice, contract, schedule, mockup, specs) in `agent/playbooks/`, extracted from the recorded runs and from screenpipe's own workflow catalogue.
- **Context from screenpipe**: prices, dates and agenda slots you saw on screen are found with the screenpipe local API and cited in the reply.
- **Confidence score, out of 100**: request recognised, file found, workflow observed N times, gesture found in screenpipe, sender seen before. The interface shows each reason and the screenpipe frame as proof.
- **Safety first**:
  - In **Auto** mode it sends only above **80/100**. In **I approve** mode it always leaves a Gmail draft for you to approve.
  - Money or legal mails (`payment`, `refund`, `lawyer`, `urgent`…) are **never** answered alone.
  - A mail with no learned workflow is left to you, with a **Show me once** button to teach it.

## How screenpipe is used

screenpipe is the agent's eyes and memory. Every step goes through its local API (`localhost:3030`) or its pipes:

| Stage | What we use in screenpipe | Where in the code |
|---|---|---|
| **Record** | Continuous screen capture: OCR, the accessibility tree, and **input events** (clicks, drags, the app and window they happened in). | screenpipe app, running in the background |
| **Learn the gesture** | For each training run we query `/search` with `content_type=input` and `accessibility` in the 90 s around the reply. This rebuilds the real sequence: Gmail → File Explorer → select file → drag into Gmail → reply. Steps seen in most runs become a **playbook**. | `agent/extract_playbooks.py` → `agent/playbooks/*.json` |
| **Learn natively** | screenpipe's own learning pipes (`workflow-discover`, `workflow-procedures`, …) turned the same sessions into a workflow in its **workflow catalogue** (`/workflows`) and into **memories** (`/search?content_type=memory`). The interface shows the learned workflow; memories are attached as proof. | `ui/app/api/workflows`, `agent/evidence.py` |
| **Prove** | Before acting, the agent looks up past input events on the same file. Each event carries a `frame_id`, and the interface shows that exact screenshot (`/frames/{id}`): *“You showed me 14 times”*. | `agent/evidence.py`, `ui/app/api/frame` |
| **Remember context** | When a mail asks for a price, a delivery date or your availability, `/search?content_type=ocr` finds where you saw it on screen. The reply quotes it, and the interface cites the frame, app and time. | `agent/context.py` |
| **Teach** | **Show me once** stars the next 10 minutes (`/starred-sessions`), so that recording is treated as a new demonstration. | `ui/app/api/teach` |
| **Run** | The `mail-autopilot` pipe runs the agent every 15 minutes. Its definition is in [`screenpipe/pipes/mail-autopilot/pipe.md`](screenpipe/pipes/mail-autopilot/pipe.md). | `agent/process_now.py` |

The API token is read from `training_bot/.env` (`SCREENPIPE_LOCAL_API_KEY`) and never leaves the machine.

## Daily use

Double-click **`Deja-vu.pyw`**. It starts screenpipe if needed, the web interface and the agent service in the background, without any terminal window, then opens http://localhost:3000.

In the interface:

- **Process now** does everything on its own:
  - checks screenpipe;
  - opens the agent's Brave on Gmail;
  - handles up to 3 unread mails;
  - shows the result. *Hands off the mouse while it works.*
- **I approve / Auto** switches the sending mode.
- **Reply to all** sends every ready draft that isn't sensitive.
- **Send / Reject** acts on one draft. It is sent from Gmail, with the attachment checked first.

Other commands:

- Stop everything: `python Deja-vu.pyw stop`
- Automatic runs: `agent/config.json` → `"every_minutes": 15` (`0` = only on demand).
- Logs: `logs/`. The full output of the last run is in `logs/process_now.log`.

## Install from scratch (Windows)

Requirements: Windows 10/11, Python 3.12, Node.js 20+, Brave, and the **screenpipe** app installed and running.

1. **Dependencies**
   ```bash
   pip install -r training_bot/requirements.txt
   ```
   ```bash
   npm --prefix ui install
   ```
2. **Configuration**: copy `training_bot/.env.example` to `training_bot/.env`, then fill in `DEMO_EMAIL`, `SIGNATURE` and `SCREENPIPE_LOCAL_API_KEY` (the file explains how to get the token). `.env` is git-ignored: never commit it.
3. **screenpipe**: on a machine with an AMD GPU, turn audio off in its settings (the Vulkan driver crashes transcription).
4. **Gmail sign-in (once)**: run the command below, then sign in to the demo account yourself in the Brave window that opens. The session stays in `training_bot/browser_profile/` (git-ignored); the agent never sees your password.
   ```bash
   python training_bot/reply_bot.py --login
   ```
5. **Demo files**: this creates `Documents\Freelance-Demo\*.pdf`.
   ```bash
   python training_bot/make_test_files.py
   ```
6. **Teach it** (optional, the playbooks in `agent/playbooks/` are enough for a demo). Show the gesture to screenpipe, then extract the playbooks:
   ```bash
   python training_bot/run_training.py --minutes 30
   ```
   ```bash
   python training_bot/context_bot.py --minutes 30
   ```
   ```bash
   python agent/extract_playbooks.py
   ```
7. **Run**: double-click `Deja-vu.pyw`.

### Optional: the screenpipe pipe

To let screenpipe run the agent every 15 minutes:

1. Copy [`screenpipe/pipes/mail-autopilot/pipe.md`](screenpipe/pipes/mail-autopilot/pipe.md) to `~/.screenpipe/pipes/mail-autopilot/pipe.md`.
2. Replace `<path-to-this-repo>` with your checkout path.

The pipe runs the same entry point as the button:

```bash
python agent/process_now.py --max 3
```

A lock prevents a pipe run and a click from fighting over the mouse. The agent's Brave is started outside the pipe's process group, so it survives the end of the run. Pause the pipe during a live demo so it doesn't fire at the wrong moment.

## Reproduce the demo

The demo runs on one Windows machine with the install above done: Gmail signed in, demo PDFs created, screenpipe recording.

1. **Start** with a double-click on `Deja-vu.pyw`. In the interface, pick **I approve** to get a draft, or **Auto** to let it send above 80/100.
2. **Send a request** from another mail account to the demo Gmail account. The playbooks were learned on French mails, so use their trigger words:

   | Subject / words in the mail | Workflow | File attached |
   |---|---|---|
   | `devis`, `prix`, `tarif`, `chiffrage` | quote | `devis-studio-nova.pdf` |
   | `facture`, `compta` | invoice | `facture-octobre-2026.pdf` |
   | `contrat`, `signature`, `prestation` | contract | `contrat-prestation-boulangeriemax.pdf` |
   | `planning`, `échéances`, `calendrier` | schedule | `planning-projet-novembre.pdf` |
   | `maquette`, `design`, `mockup` | mockup | `maquette-accueil-v2.pdf` |
   | `cahier des charges`, `specs` | specs | `cahier-des-charges-site-vitrine.pdf` |

   For example: subject **`devis`**, body *“Salut, tu peux me renvoyer le devis stp ?”*. Leave it **unread** in Gmail.
3. **Click Process now** and take your hands off the mouse. Brave opens the mail, File Explorer opens on `Documents\Freelance-Demo`, the PDF is dragged into the reply, and the answer is typed in.
4. **Check the result** in the interface:
   - the draft, or the sent reply;
   - the proof card: the screenpipe frame of a past run, *“You showed me N times”*, and the score with **Details**.
5. **Context** (optional). Open `devis-studio-nova.pdf` on screen for a few seconds so screenpipe reads its total. Then send *“tu peux me confirmer le prix ?”*. The reply quotes the price, and **What I remembered** shows where you saw it.
6. **Unknown request** (optional). Send a mail with no trigger word. It is left for you, marked *to check*, with **Show me once**.
7. **Replay** a mail that's already in Gmail, read or not, without sending a new one:

   ```bash
   python agent/run_agent.py --subject "devis"
   ```

[`DEMO.md`](DEMO.md) has our minute-by-minute stage script, and [`PITCH.md`](PITCH.md) the spoken pitch.

## Project layout

| Path | Role |
|---|---|
| `agent/process_now.py` | single entry point (button, service, pipe): prepares screenpipe and Brave, runs the agent, writes `last_run.json` |
| `agent/run_agent.py` | picks the playbook, replays the gesture, scores confidence, drafts or sends |
| `agent/evidence.py`, `agent/context.py` | proof frames and facts found in screenpipe, confidence rules |
| `agent/approve_draft.py` | sends or rejects a draft after human approval |
| `agent/playbooks/` | learned workflows (one JSON per request type) |
| `training_bot/reply_bot.py` | Gmail and Brave automation (Selenium + pyautogui + pywinauto) |
| `training_bot/` | training bots (Gmail gesture, on-screen context), Gmail sign-in |
| `ui/` | Next.js interface: queue, draft, *What I remembered*, proof and score |
| `Deja-vu.pyw` | launcher without any terminal |
| `screenpipe/pipes/` | the screenpipe pipe definition (`mail-autopilot`) |
| `DEMO.md`, `PITCH.md` | demo script and spoken pitch |

## Troubleshooting

| Message | Fix |
|---|---|
| `screenpipe is not responding` | open the screenpipe app, then check http://localhost:3030/health |
| `Gmail is not signed in` | run `python training_bot/reply_bot.py --login` once |
| `a run is already in progress` | wait for the current run (button, service or pipe) to finish |
| `the agent crashed: …` | the full output is in `logs/process_now.log` |

## Notes

- **Platform**: Windows only. The gesture uses the real mouse, File Explorer and Brave.
- **Language**: replies are written in French, like the user's own mails. The interface is in English.
- **Private data stays local and out of git**: the mail log, decisions, mode, Brave profile and secrets.
