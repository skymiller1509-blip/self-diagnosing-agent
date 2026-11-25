# Building Blocks Tested (OpenMinion 0.1.24)

What this entry exercised in the OpenMinion 0.1 Python SDK, and what happened
with each block. All of it ran locally against Ollama (qwen2.5:0.5b) with no
API keys and no paid services.

## Used and working

- **`openminion.Agent`** (`from openminion import Agent`) — created with
  `instructions`, `tools`, `config_path`, `agent_id`, `model`, `session_id`.
  One `Agent` per turn, all sharing one session id, so history carries
  across turns. Works.
- **`@tool` decorator** (`from openminion import tool`) — five tools:
  `read_numbers` and `sum_numbers` (`min_scope="READ_ONLY"`, `idempotent=True`),
  `diagnose_failure` (read-only), `quarantine_bad_lines` and `write_total`
  (write tools). All five executed for real in the demo run.
- **`agent.run(prompt, timeout_seconds=...)`** — one turn per step. Each turn
  returned after its tool call; the runner verified each step from the
  tool-call log before moving on.
- **`openminion setup --provider ollama --model qwen2.5:0.5b --no-chat`** —
  generates a working config (`.openminion/agents.json`) with the ollama
  provider. The generated profile is the only config that worked; see below.
- **Action policy bypass** — agent profile
  `"action_policy": {"mode": "bypass"}` lets the two genuine write tools run
  without interactive confirmation, as documented. Writes stay inside the
  project directory by a path check in the tool code.
- **Native tool calling for Ollama** — the provider setting
  `providers.ollama.tool_call_strategy: "native"` makes the model emit real
  tool calls. With the default `"fallback"` (text-format tool calls) the
  0.5B model could not follow the format at all.
- **Tool result as evidence** — the runtime feeds each tool result back to
  the model, and the model acts on it (e.g. it called `diagnose_failure`
  after `sum_numbers` returned an error).

## Rough edges found (also in WHAT_WE_LEARNED.md)

1. A hand-written config fails with
   `RuntimeError('inbound authenticity denied (reason=invalid_channel,
   mode=warn)')`. Agent profiles need `"default_channel": "console"`.
   Only the CLI-generated config worked.
2. A session created under a failed channel cannot be reused:
   `ValueError("Session ... belongs to channel '', not 'console'")`.
   The demo uses a fresh timestamped session id per run.
3. The VM's `NO_PROXY` contains bracketed IPv6 entries (`[::1]`) that
   httpx cannot parse: `InvalidURL: Invalid port: ':1]'`. The same error hit
   the upstream quickstart in a fresh process, so it is an SDK rough edge on
   this machine, not our code. Workaround: strip bracketed entries before
   any httpx client is created.
4. The runtime's LLM freshness classifier can misclassify a local file task
   as a time-sensitive finance request, and then the runtime refuses with a
   "grounded current finance answer" template instead of calling the tool.
   The documented bypass is to start the message with `tool <name>`, which
   skips freshness classification for explicit tool requests.
5. A 0.5B model cannot hold a five-step conditional plan in one `run()`: it
   repeats the failing call until the runtime's loop guard stops it. The
   demo therefore drives one step per turn with exactly one tool exposed per
   turn. The model still chooses every call and argument within each turn.

## Not tested

- Any provider other than `ollama` (all others need API keys).
- Portal / Gemma4 (optional for the hackathon; not needed for this entry).
- Multi-agent / A2A features, memory capture, or skills — not used by
  this entry.
