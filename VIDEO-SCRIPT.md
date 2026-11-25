# Demo video script — Self-Diagnosing Agent (Cortensor Hackathon #5)

- Target length: **about 4 minutes** (event allows 1–5 minutes).
- Format: screen recording of the verified run's transcript and tool calls, read aloud in plain words. Do NOT re-run the live demo on camera: the real run takes about 9 minutes, so this video shows the trimmed arc — fail, diagnose, fix, verified total — from the verified run of 23 Nov 2026.
- The sentence a judge should repeat an hour later: **"The agent failed, explained why in plain words, fixed it, and proved the total is 106."**

## Hook options — pick the clearest, say it aloud, keep the best take

1. "My agent failed — and then it fixed itself."
2. "Line 4 says 'twelve'. That is not a number. Watch the agent find that."
3. "It got the sum wrong, told me why, and proved the right answer: 106."

## Shot-by-shot script

### 0:00–0:05 — Hook (sound off must still work)

- On screen, big text: **"IT FAILED. THEN IT FIXED ITSELF."**
- Show the verified end state first: `out/total.txt` open, showing `106`.
- Say: "My agent failed — and then it fixed itself. The answer is 106, and it can prove it."

### 0:05–0:20 — Problem, one sentence, one named user

- On screen: `data/numbers.txt` open, line 4 highlighted: `twelve`.
- Say: "Ada runs a small agent that adds up numbers from a file. One line in the file says the word 'twelve' instead of the number 12, and most agents just crash there. Mine stops, works out what went wrong, and carries on."

### 0:20–2:30 — The one live flow (trimmed from the verified run)

Show the transcript (`demo-transcript.md`) and the tool calls in order. Use jump cuts between steps — say out loud that the full run took about 9 minutes and this is the trimmed version. Do not pretend it ran in real time.

- **Step 1 — Read (0:20–0:45).** Show `read_numbers` and the file contents, lines 1–7. Say: "First it reads the file. Seven lines. Line 4 says 'twelve'."
- **Step 2 — Fail (0:45–1:10).** Show `sum_numbers` returning the error: `line 4: 'twelve' is not a number`. Say: "Then it tries to add them up, and it fails. That error is the whole demo — what happens next is the point."
- **Step 3 — Diagnose (1:10–1:50).** Show the `diagnose_failure` result in full: "Line 4 says 'twelve', which is a word, not a number. The sum stopped there. 1 bad line in total, 6 valid numbers." Say: "It looks at the file and explains the failure in plain words: one bad line, six good numbers. And it says what to do: move the bad line aside and try again."
- **Step 4 — Fix (1:50–2:10).** Show `quarantine_bad_lines`: "Quarantined 1 bad line to out/quarantined.txt. Kept 6 valid numbers." Say: "It moves the bad line to a quarantine file and keeps the six good numbers."
- **Step 5 — Retry and verify (2:10–2:30).** Show `sum_numbers` returning `total: 106 from 6 numbers`, then `write_total` writing 106 to `out/total.txt`. Say: "It adds them again. Total: 106, from six numbers. Then it writes 106 to the answer file. The run checks the file itself, so the total is verified, not just printed."

### 2:30–3:00 — How it works (the hard part, in plain words)

- On screen: the six tool names in a list, and the line `openminion.Agent` in `agent.py`.
- Say: "Underneath, this is the real OpenMinion 0.1 Python SDK driving every tool call, with a small local model — qwen2.5 0.5B — running on my own machine through Ollama. No paid service, no API key, no cloud. The hard part was that the tiny model could not hold a five-step plan in one go — it just repeated the failing call — so the runner gives it one narrow step per turn, and the model still chooses every tool call itself. The diagnosis itself comes from plain code that reads the real file, so the explanation is grounded, never invented."

### 3:00–3:30 — Honest limits (say them out loud)

- Say: "Two honest limits. First, the model's own summary was weak — it literally said 'failed: None. Fixed: None. Total: None.' The tool calls and the verified file are the real evidence, not the summary. Second, I have not run this against Cortensor Portal or Gemma 4 — I do not have access, and the rules say that is not held against you."

### 3:30–4:00 — What's next, and the close

- Say: "Next I would run the same loop with a bigger model that can plan the whole fix in one turn, and against Cortensor Portal when I get access. This is the Self-Diagnosing Agent, built with OpenMinion and Ollama for Cortensor Hackathon 5. It fails, it explains why, it fixes it, and it proves the answer."
- End screen, big text: **"FAILED. EXPLAINED. FIXED. TOTAL: 106."**

## What NOT to say or show

- Do not claim the video is a single live run in real time. It is a trimmed cut of a 9-minute verified run — say so.
- Do not read the agent's final summary as proof of anything. It was wrong/empty; the tool calls and `out/total.txt` are the proof.
- Do not claim Portal or Gemma 4 was used. It was not.
- Do not show any API key on screen. There is none in this project — keep it that way.

## Recording notes (phone)

- Android screen recorder: swipe down twice, tap Screen record, microphone ON, wait for the countdown.
- Turn on Do Not Disturb first, so no notification lands mid-take.
- Film in landscape. Browser zoom 100–125%, full screen, bookmarks bar hidden, extra tabs closed.
- Open `demo-transcript.md` and `out/total.txt` in tabs before you start, so there is no fumbling.
- Add captions in CapCut (free) after recording — judges may watch with sound off.
- Record the hook (0:00–0:05) two or three times and keep the best take.
- Also save a separate 60-second insurance capture of the transcript and the verified total, in case anything breaks on submission day.
