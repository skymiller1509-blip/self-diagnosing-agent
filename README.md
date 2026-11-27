# Self-Diagnosing Agent — Cortensor Hackathon #5

An agent that fails, explains why in plain words, fixes it, and proves the answer.

**Total: 106, verified — from 6 numbers, after the agent found and fixed the bad line itself.**

## Demo video

> TODO — record the 1–5 minute demo video (see `VIDEO-SCRIPT.md`) and paste the public link here. Raw footage received 26 Nov 2026 (transcript scroll); final video build pending.

## What it does and why

An agent that runs a task, detects its own failure, explains the cause in
plain language, and retries with a fix. Built with the real
**OpenMinion 0.1 Python SDK** (`openminion` 0.1.24, PyPI) and a local model
via Ollama. No paid service, no API key, no cloud.

The one workflow below is the whole demo: a dirty input file, one failure,
one plain-language diagnosis, one fix, and a verified total of 106.

## Hackathon Requirements Met

Cortensor Hackathon #5, DoraHacks — prize $1,150, deadline 18 Dec 2026. Each requirement, with proof:

- [x] Build complete and verified — demo run PASS, total 106, transcript saved (`demo-transcript.md`, run 2026-11-23, all six steps first try).
- [x] 5 unit tests, no model needed (`tests/test_diagnosis.py`).
- [x] README with tagline, demo-video slot, what/why, tech stack, try-it-yourself, honest limits (this file).
- [ ] Demo video, 1–5 min — script in `VIDEO-SCRIPT.md`; raw footage received 26 Nov 2026, final video build pending.
- [ ] Submission PR — **BLOCKED: the dedicated Hackathon #5 repository URL is still listed as "will be added before kickoff" in the official docs.** Nothing can be submitted until Cortensor publishes it.
- [ ] DoraHacks BUIDL page kept up to date once the PR exists.

Demo failure-proofing: the video is built from the verified transcript (`demo-transcript.md`, run 2026-11-23, all six steps first try), not from a fresh live run — the 9-minute run is trimmed to the 60 seconds that matter (fail, "twelve", fix, 106). The demo never depends on the model improvising on camera.

## Judging Highlights

- **Innovation:** an agent that fails, explains why in plain words, fixes it, and proves the answer — the diagnosis is grounded in the real file, never invented.
- **Technical execution:** the real OpenMinion 0.1 SDK driving a local Ollama model (`qwen2.5:0.5b`, no key, no cloud); deterministic diagnosis logic, unit-tested; 5 unit tests that need no model.
- **Impact:** self-diagnosing agents that explain themselves in plain language — the failure, the cause, the fix, the proof — instead of failing silently.
- **Completeness:** the one workflow runs end to end and is verified (total 106 in `out/total.txt`); the transcript is committed; the scaffolding the tiny model needs is stated plainly, not hidden.

## Tech stack

- Python, OpenMinion 0.1 SDK (`openminion` 0.1.24, PyPI)
- Ollama local model `qwen2.5:0.5b` (free, no key, no cloud)
- Deterministic diagnosis logic in `self_diagnosing_agent/diagnosis.py`
- pytest (5 unit tests, no model needed)

## The one workflow

Task: total the numbers in `data/numbers.txt` and write the answer to
`out/total.txt`.

The input is deliberately dirty: line 4 says `twelve` instead of `12`.
The run goes:

1. `read_numbers` — the agent reads the file.
2. `sum_numbers` — fails: `line 4: 'twelve' is not a number`.
3. `diagnose_failure` — the agent inspects the file and explains, in plain
   language, that line 4 is a word, not a number, and recommends
   quarantining the bad lines.
4. `quarantine_bad_lines` — the bad lines move to `out/quarantined.txt`,
   the valid numbers stay.
5. `sum_numbers` again — succeeds: total **106**.
6. `write_total` — writes `106` to `out/total.txt`.

The model drives every tool call through `openminion.Agent`. The diagnosis
logic itself is deterministic (`self_diagnosing_agent/diagnosis.py`) and
unit-tested, so the explanation is always grounded in the real file, never
invented.

## Setup

```bash
cd self-diagnosing-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Local model (free, no key): Ollama + a small model
# Install Ollama from https://ollama.com, then:
ollama pull qwen2.5:0.5b
ollama serve   # in a separate terminal, if not already running

# Tell OpenMinion to use the local model (project-local config)
OPENMINION_HOME="$PWD/.openminion-home" \
  .venv/bin/openminion setup --provider ollama --model qwen2.5:0.5b --no-chat
```

## Run the demo

```bash
OPENMINION_HOME="$PWD/.openminion-home" \
  PYTHONPATH=. .venv/bin/python run_demo.py
```

The demo resets `data/numbers.txt` to the known-bad input, runs the agent,
prints every real tool call as it happens, and verifies `out/total.txt`
equals `106`. It saves a transcript to `runs/<timestamp>/transcript.md`.
Exit code 0 means the total was verified. The verified run's transcript is
also committed as `demo-transcript.md`.

Run the unit tests (no model needed):

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
```

## How the OpenMinion SDK is used

- `Agent` (`openminion.Agent`) is the runtime: instructions, tool list,
  session id, and a project-local config path.
- `@tool` declares each tool with a contract. `read_numbers`,
  `sum_numbers`, and `diagnose_failure` are `READ_ONLY` and idempotent;
  the two write tools (`quarantine_bad_lines`, `write_total`) run under
  the agent profile's `"action_policy": {"mode": "bypass"}` so a scripted
  demo does not stop for interactive confirmation. Writes are confined to
  the project directory by a path check in the tool code.
- The ollama provider is configured with `tool_call_strategy: "native"`;
  the default `"fallback"` (text-format tool calls) is unusable with a
  0.5B model.
- The config is the one `openminion setup` generates, with
  `"default_channel": "console"` added to the agent profile (a hand-written
  config is rejected by the runtime).
- A fresh timestamped session id is used per run (`self-diagnosing-<time>`),
  all turns sharing it, so the whole diagnose-fix-retry loop is inspectable
  with `openminion agent logs` and `openminion agent inspect`.
- Provider errors are caught as `ProviderError` (see `error_handling.py`
  in the upstream examples, which this follows).
- The `ollama` provider is the only credential-free provider in
  `openminion setup --list-providers`. Every other built-in provider needs
  an API key, which this project deliberately does not use.

## How the demo is driven — stated plainly

The runner (`run_demo.py`) drives the agent **one step per turn, with
exactly one tool exposed per turn**. This is scaffolding the tiny local
model needs, and we do not hide it:

- In a single `agent.run()`, qwen2.5:0.5b could not hold the five-step
  fail-diagnose-fix-retry plan: it repeated the failing `sum_numbers` call
  until the runtime's loop guard stopped it, and never called `diagnose`.
- Given one narrow step per turn, the same model made the right call
  first try for all six steps in the verified run.
- The model still chooses every tool call and its arguments within each
  turn. The runner never calls a tool itself; it only sequences the steps
  and verifies each one landed by reading the tool-call log.
- Each prompt starts with `tool <name>`. That is OpenMinion's documented
  way to mark an explicit tool request, and it skips the runtime's LLM
  freshness classifier — which otherwise sometimes mislabels this local
  file task as a time-sensitive finance request and refuses to call the
  tool at all.
- `diagnose_failure` and `write_total` are called with no arguments: they
  read the last failure / last successful sum from the run log, so the
  model never has to retype an error message or a number (retyping produced
  "Invalid tool arguments" failures). The values used are the real recorded
  ones.
- The verified run (2026-11-23, ~9 minutes, all six steps first try) is
  saved at `runs/20261123-193434/transcript.md`. `out/total.txt` was
  verified to equal `106`.

## Files

- `self_diagnosing_agent/agent.py` — the tools and the Agent wiring.
- `self_diagnosing_agent/diagnosis.py` — pure diagnosis logic + tests.
- `run_demo.py` — demo runner with verification and transcript.
- `data/numbers.txt` — sample input (bad line: `twelve` on line 4).
- `tests/test_diagnosis.py` — 5 unit tests, no model needed.
- `BUILDING_BLOCKS.md` — what was tested, what worked, what did not.
- `WHAT_WE_LEARNED.md` — product feedback for the OpenMinion team.

## Honest limits

- The demo model is `qwen2.5:0.5b`, a tiny local model. It can follow a
  short tool loop, but it is not a strong reasoner; the diagnosis text
  comes from deterministic code over the real file, not from the model
  guessing. Its free-text summaries are weak — the verified run's summary
  was literally "failed: None. Fixed: None. Total: None." The tool calls
  and the verified output are the real evidence.
- The demo needs the step-per-turn scaffolding described above. A bigger
  model would likely plan the whole run in one turn; this machine could not
  run one (about 1.5 GB RAM free; the next size up needs ~1 GB more).
- The demo has not been run against Cortensor Portal or Gemma4 (no access;
  Portal is optional for qualification and participants without access are
  not penalised).
- No demo video yet; the 1–5 minute video still needs to be recorded from
  a real run.
- Submission (a PR to the dedicated Hackathon #5 repository) is not done:
  the repository URL is still listed as "will be added before kickoff" in
  the official docs.

## Links

- Hackathon rules: https://docs-v2.cortensor.network/ecosystem/hackathon-5/
- DoraHacks page: https://dorahacks.io/hackathon/2418/detail
- OpenMinion repo: https://github.com/OpenMinion/openminion
- OpenMinion docs: https://www.openminion.com
- OpenMinion PyPI: https://pypi.org/project/openminion/
