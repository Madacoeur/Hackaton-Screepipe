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

The `mail-autopilot` pipe (in `~/.screenpipe/pipes/mail-autopilot/pipe.md`) runs the same entry point every 15 minutes:

```bash
python agent/process_now.py --max 3
```

A lock prevents a pipe run and a click from fighting over the mouse. The agent's Brave is started outside the pipe's process group, so it survives the end of the run.

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
