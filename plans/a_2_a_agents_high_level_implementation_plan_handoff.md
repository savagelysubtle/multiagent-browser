# A2A Agents – High‑Level Implementation Plan (handoff)

This Markdown is a **coding handoff** for building out the remaining A2A agents. It captures decisions, shapes, and recurring patterns so an implementer can code without ambiguity. Keep each agent narrowly scoped, expose a few high‑quality skills, and let a **Conductor** agent orchestrate.

---

## 0) Objectives
- Stand up a family of **A2A‑compliant agents** with consistent endpoints and discoverable skills.
- Enable **multi‑agent orchestration** via a Conductor that discovers agent cards and delegates.
- Keep everything testable with `curl` and portable to a UI (CopilotKit/AG‑UI) later.

**Deliverables**
- Per‑agent server (Python FastA2A) exposing:
  - `/.well-known/agent.json` (Agent Card)
  - `POST /` (Run endpoint)
- Declarative **skills** with JSON Schemas and worker implementations.
- Optional: streaming updates and artifacts.

---

## 1) Agent anatomy (contract)
Every agent provides:

- **Agent Card** at `/.well-known/agent.json`:
  - `name`, `version`, `description`
  - `capabilities` (e.g., `streaming` true/false)
  - `skills[]` with `name`, `description`, `input_schema`, `output_schema`
  - `authentication` (optional)
- **Run endpoint** `POST /`:
  - Body: `{ "skill": string, "input": object, "meta?": object }`
  - Response: task record with status + optional streaming events until final `result`.
- **Task lifecycle**: accept → (optional) stream progress → return final `result` and artifacts.

> Consistency across agents is critical so the Conductor can call them uniformly.

---

## 2) Base implementation pattern (FastA2A)
We standardize on **FastA2A** to minimize boilerplate and guarantee shape parity.

**Server responsibilities**
1. Declare `Skill(...)` objects (schemas first!)
2. Register workers: `@app.task_manager.worker("<skill>")`
3. Return structured results; the framework wires card + run endpoint.

**Startup**
- `uvicorn app:app --port <PORT> --reload`
- Smoke tests below in §7.

---

## 3) Skill design guidelines
- **One job per skill**, verbs in imperative (`search_web`, `summarize_docs`, `extract_invoice_fields`).
- **Input schema**: small, explicit, validated (types, enums, required fields).
- **Output schema**: succinct, consumer‑friendly (avoid dumping raw internals).
- **Idempotency**: where feasible; document side‑effects.
- **Time/locale**: include `timezone?`/`locale?` if behavior changes by region.
- **Errors**: return typed `error` object when business errors occur; reserve HTTP 5xx for server faults.

**Schema checklist**
- [ ] Type safety (numbers vs strings)
- [ ] Minimal required set
- [ ] Stable keys (no renames without version bump)
- [ ] Examples added (for docs/testing)

---

## 4) Cross‑cutting concerns
- **Versioning**: bump `version` on any breaking schema/behavior change. Use semver.
- **Auth** (if needed): define in card `authentication.schemes` (e.g., bearer) and enforce on `POST /`.
- **Observability**: log task id, skill, input hash, duration, success/error, and emit counters.
- **Artifacts**: when producing files/links, return `{ artifacts: [{ type, name, uri }] }` alongside `result`.
- **Streaming**: if emitting progress, mark `capabilities.streaming=true` and send events: `status`, `progress`, `message`, final `result`.

---

## 5) Reference skill set (initial wave)
Implement as separate micro‑agents for clean ownership. Each bullet shows **skill signature** and **notes**.

### A) Search Agent
- `search_web(query: string, top_k?: integer = 5) -> { results: Array<{ title: string, url: string, snippet: string }>} `
  - Notes: add `region?`, `safe?` flags if needed.

### B) Summarizer Agent
- `summarize(urls: string[], style?: "bullets"|"abstract"|"qa") -> { summary: string }`
  - Notes: optionally chain to Search Agent when `urls` empty.

### C) Extractor Agent (Docs)
- `extract_invoice_fields(pdf_url: string) -> { vendor: string, date: string, total: number, line_items: Array<{ desc: string, qty: number, unit_price: number, amount: number }> }`
  - Notes: return normalized ISO date, numeric totals.

### D) Code‑Ops Agent
- `run_tests(repo_url: string, path?: string) -> { passed: boolean, report: string }`
- `lint(repo_url: string, path?: string) -> { issues: Array<{ file: string, line: number, rule: string, msg: string }>} `

### E) Router / Conductor Agent
- `solve(goal: string, context?: object) -> { plan: Array<string>, results: object }`
  - Internals: discovers cards, selects agents by skill, delegates, aggregates.

> Add domain‑specific agents later (Finance, DevOps, Docs QA) by repeating the pattern.

---

## 6) Conductor design (multi‑agent orchestration)
**Responsibilities**
1. **Discovery**: fetch `/.well-known/agent.json` for known agent URLs.
2. **Routing**: map intents → `(agent, skill)` by description matching and/or static config.
3. **Planning**: break `goal` into steps; maintain a scratchpad of intermediate results.
4. **Execution**: call agents in sequence/parallel; handle retries/timeouts.
5. **Aggregation**: produce a clean, typed final result (and artifacts) for the caller/UI.

**Minimal algorithm**
- Build an in‑memory registry: `{ skill_name | keyword: [agent_url] }`.
- For each plan step, choose the agent with the most specific skill.
- Fan‑out for parallelizable steps; join on completion.
- Stream progress messages if `capabilities.streaming` is available downstream.

**Failure policy**
- Budget retries (e.g., 2x) on network errors.
- Short circuit on non‑recoverable schema errors (surface to caller with advice).

---

## 7) Testing & smoke scripts
**Card**
```bash
curl -s http://localhost:8000/.well-known/agent.json | jq
```
**Run**
```bash
curl -s http://localhost:8000/ \
  -H 'Content-Type: application/json' \
  -d '{"skill":"calc_total","input":{"values":[1,2,3,4]}}' | jq
```
**Streaming (if enabled)**
- Use `--no-buffer` and watch SSE/NDJSON depending on implementation.

---

## 8) Directory & naming conventions
```
agent-<domain>/
  app.py                 # FastA2A app (card + run wired here)
  skills/
    <skill_name>.py      # schema + worker
  tests/
    smoke_*.sh           # curl recipes
  README.md
```
- Skill names: `snake_case`, verb‑first.
- Module names match skill names.

---

## 9) UI bridge (optional)
If/when a UI is needed:
- **Backend**: thin gateway that accepts chat/events and delegates to Conductor; conforms to AG‑UI/CopilotKit streaming contract.
- **Frontend**: CopilotKit (React) consuming the stream; display messages, tool calls, artifacts.

This keeps A2A services unchanged; only the gateway translates chat↔A2A calls.

---

## 10) Roadmap (incremental build order)
1) Scaffold **Calculator** (demo) → verify card/run.
2) Implement **Search Agent** (A).
3) Implement **Summarizer Agent** (B) using (A) when `urls` empty.
4) Implement **Extractor Agent** (C).
5) Stand up **Conductor** (E) with static registry of the three above.
6) Add **Code‑Ops** (D) and plug into Conductor.
7) Add streaming & artifacts where it adds value.

---

## 11) Acceptance criteria (per agent)
- [ ] `/.well-known/agent.json` returns valid JSON with skills & version.
- [ ] `POST /` executes all declared skills with schema validation.
- [ ] Errors are typed and informative.
- [ ] Smoke tests pass.
- [ ] Logs expose task id, duration, and outcome.

---

## Appendix A: Example skill schemas (ready to paste)

### `search_web`
```json
{
  "name": "search_web",
  "description": "Web search returning top_k results.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "title": {"type": "string"},
            "url": {"type": "string"},
            "snippet": {"type": "string"}
          },
          "required": ["title", "url", "snippet"]
        }
      }
    },
    "required": ["results"]
  }
}
```

### `summarize`
```json
{
  "name": "summarize",
  "description": "Summarize a set of documents or URLs.",
  "input_schema": {
    "type": "object",
    "properties": {
      "urls": {"type": "array", "items": {"type": "string"}},
      "style": {"type": "string", "enum": ["bullets", "abstract", "qa"], "default": "bullets"}
    },
    "required": ["urls"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "summary": {"type": "string"}
    },
    "required": ["summary"]
  }
}
```

### `extract_invoice_fields`
```json
{
  "name": "extract_invoice_fields",
  "description": "Extract structured fields from an invoice PDF.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pdf_url": {"type": "string"}
    },
    "required": ["pdf_url"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "vendor": {"type": "string"},
      "date": {"type": "string", "description": "ISO 8601 date"},
      "total": {"type": "number"},
      "line_items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "desc": {"type": "string"},
            "qty": {"type": "number"},
            "unit_price": {"type": "number"},
            "amount": {"type": "number"}
          },
          "required": ["desc", "qty", "unit_price", "amount"]
        }
      }
    },
    "required": ["vendor", "date", "total", "line_items"]
  }
}
```

### `run_tests`
```json
{
  "name": "run_tests",
  "description": "Run test suite and return a pass/fail with report.",
  "input_schema": {
    "type": "object",
    "properties": {
      "repo_url": {"type": "string"},
      "path": {"type": "string"}
    },
    "required": ["repo_url"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "passed": {"type": "boolean"},
      "report": {"type": "string"}
    },
    "required": ["passed", "report"]
  }
}
```

### `lint`
```json
{
  "name": "lint",
  "description": "Run linter and return issues.",
  "input_schema": {
    "type": "object",
    "properties": {
      "repo_url": {"type": "string"},
      "path": {"type": "string"}
    },
    "required": ["repo_url"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "issues": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "file": {"type": "string"},
            "line": {"type": "number"},
            "rule": {"type": "string"},
            "msg": {"type": "string"}
          },
          "required": ["file", "line", "rule", "msg"]
        }
      }
    },
    "required": ["issues"]
  }
}
```

---

## Appendix B: Coding notes
- Keep external dependencies behind interfaces so we can swap providers.
- Guardrail LLM calls with max tokens/timeouts; return partial results if budget exceeded.
- Prefer pure functions inside workers; isolate I/O.

---

**End of handoff.**

