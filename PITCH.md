# Déjà-vu — spoken pitch (≈ 3 minutes)

Cues in **[brackets]** = what's on screen. Read naturally; pause where there's a line break.

---

**[Slide 1 — Show once, run forever]** · 0:00

Hi, we're [team]. Our project is called **Déjà-vu**.

**[Slide 2 — “Can you resend the quote and confirm the price?”]** · 0:10

You've all received this email.
Replying to it takes thirty seconds of writing… and five minutes of digging.
The quote is somewhere in a folder. The price was agreed on Thursday's call. And this exact sequence — find the file, drag it in, reply — you do it ten times a day.

**[Slide 3 — The answer isn't in your inbox]** · 0:30

Here's our insight: the answer to an email is almost never in your inbox. It's in what you've **seen**.
Gmail sees your emails. **screenpipe sees your work.** So we built on screenpipe.

**[Slide 4 — Three steps]** · 0:45

It works in three steps.
**Show once**: you do the task normally while screenpipe records. We did it about eighty times.
**Learn**: screenpipe's own learning pipes turned that into a workflow — it's literally in its workflow catalog — and into memories.
**Run forever**: a screenpipe pipe replays it on its own, every fifteen minutes.

**[Slide 7 — Demo]** · 1:05

Let me show you. An email from Karim just arrived. I'm taking my hands off the mouse.

**[Interface → “Process now”, let the mouse work]**

It opens the email, hits reply, opens the file explorer, grabs the right PDF, drags it into Gmail, and writes the answer — in my style.

**[Interface — the draft + “What I remembered”]** · 1:40

Now look at this sentence: *“as a reminder, we agreed on €2,400.”*
It didn't make that up. It found it in screenpipe — here's the frame, the time, the window it came from. Every fact has a source.
Confidence: 100 out of 100. Same client, same request, same file — it watched me do it thirteen times. I click send.

**[Interface — “Suite à notre échange”]** · 2:10

And when it doesn't know? Unknown sender, it's about a payment: *“this one's yours.”* It never answers money or legal emails on its own.
And one button: **show me once**. I handle it in front of screenpipe — and next time, it knows.

**[Slide 8 — Why screenpipe]** · 2:35

So why screenpipe? Because the Gmail API can read an email, but it can't recall a price you saw elsewhere, it can't know which file to attach, and it can't learn by watching you. And with screenpipe, everything stays on your machine.

**[Slide 9 — Show once, run forever]** · 2:50

Eighty demonstrations. Six request types learned. Zero emails sent without your OK.
**Show once, run forever.** Thank you.

---

## Likely questions — short answers

- **“What if it's wrong?”** — It cites every fact with its screenshot, scores its confidence, flags missing info, and never sends money or legal emails alone. Default mode is drafts only.
- **“Privacy?”** — Everything runs locally: screenpipe's database, the agent, the UI. Nothing leaves the machine except the email you approve.
- **“Does it generalize beyond this demo?”** — The workflow was learned from ~80 recorded runs and published by screenpipe's native discovery pipes; adding a new task = doing it a few times in a starred session.
- **“Why not just an LLM?”** — An LLM can write, but it doesn't know what you saw or how you work. screenpipe is the memory; the agent only uses facts it can point to.
