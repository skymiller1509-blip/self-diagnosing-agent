# What We Learned

Honest notes from building the Self-Diagnosing Agent on OpenMinion 0.1.24
with a tiny local model (Ollama qwen2.5:0.5b, 397 MB). No API keys, no paid
services, everything local.

## 1. The SDK is real and usable, but the first hour is config-shaped

The happy path works: `pip install openminion`, `openminion setup --provider
ollama`, write tools with `@tool`, drive them with `Agent(...).run(...)`.
The traps are all in configuration, not in the agent idea:

- A hand-written `agents.json` fails with `inbound authenticity denied
  (invalid_channel)`. The fix is to use the config the CLI itself generates
  and add `"default_channel": "console"` to the agent profile.
- The ollama provider defaults to `tool_call_strategy: "fallback"` — the
  model must print tool calls as text. A 0.5B model cannot do that reliably.
  Setting it to `"native"` fixed tool calling outright.
- Write tools need `"action_policy": {"mode": "bypass"}` in the agent profile
  or the run stops for interactive policy confirmation, which never arrives
  in a scripted demo.

## 2. A tiny model needs scaffolding; that is a finding, not a failure

Given one `agent.run()` and five tools, the 0.5B model could not hold the
fail-diagnose-fix-retry plan: it repeated the failing `sum_numbers` call
until the runtime's loop guard stopped it, and never called `diagnose`.
Given one narrow step per turn, with exactly one tool exposed per turn, the
same model made the right call every time, first try, for all six steps.

So the demo runner sequences the steps and checks each one landed. The
model still chooses every tool call and its arguments; the runner never
calls a tool itself. We state this plainly in the README because the
alternative — pretending the model planned all five steps alone — would be
dishonest. A bigger model would likely plan the whole run in one turn; we
could not test one (this machine has ~1.5 GB RAM free, and the next size up
needs ~1 GB on top of everything else running).

## 3. The runtime's own guardrails can misfire on a tiny model

- The LLM freshness classifier labelled "read the numbers in a file" as a
  time-sensitive finance request, and the runtime then refused to answer
  instead of calling the tool. Starting each message with `tool <name>`
  skips freshness classification for explicit tool requests — a documented
  bypass we verified in the SDK source.
- The model's free-text summaries are weak: the demo's final summary came
  out as "failed: None. Fixed: None. Total: None." The tool calls and the
  verified output (`out/total.txt = 106`) are the real evidence; the summary
  is whatever the model said, quoted verbatim in the transcript.
- At temperature 0.7 the model got creative about file paths, absolutising
  `data/numbers.txt` against the OpenMinion home directory. At 0.2 it passes
  paths verbatim. The tools now resolve known project files by suffix as a
  safety net, and write tools are confined to the project directory.

## 4. Environment gotchas worth knowing

- The VM's `NO_PROXY` contains bracketed IPv6 entries (`[::1]`, `[fd8b:...]`)
  that crash httpx with `InvalidURL: Invalid port: ':1]'`. This also broke
  the upstream OpenMinion quickstart in a fresh process, so it is a real SDK
  rough edge on machines with that proxy setup. Workaround: strip bracketed
  entries from the proxy environment before importing anything that builds an
  httpx client.
- Sessions are sticky to the channel they were created under. A session
  created by a failed run (channel `''`) cannot be reused by a fixed run
  (channel `'console'`). Fresh timestamped session ids per run avoid this.
- The first turn of a fresh session occasionally returns a spurious
  `expected_revision 0` reply with no tool call; retrying the same step once
  succeeds. The runner retries each step once.

## 5. What the agent actually proves

The demo is a genuine closed loop: a real model-backed run detects its own
failure (a bad line in a data file), explains the cause in plain language,
applies the fix it recommended, retries, and writes the verified total. The
failure is real (the tool raises), the diagnosis is computed from the actual
failure, and the retry succeeds only because the bad line was quarantined.
Nothing is staged: `run_demo.py` resets the input, runs the agent, and
verifies `out/total.txt` equals the expected total, exiting non-zero
otherwise.
