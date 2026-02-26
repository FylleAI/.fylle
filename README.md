<p align="center">
  <h1 align="center">.fylle</h1>
  <p align="center"><strong>A portable format for AI agents.</strong></p>
  <p align="center">Define your agents once. Run them on any framework.</p>
</p>

<p align="center">
  <a href="#the-problem">Problem</a> &middot;
  <a href="#how-it-works">How it works</a> &middot;
  <a href="#bridge">Bridge</a> &middot;
  <a href="#migrate-from-openclaw">Migrate from OpenClaw</a> &middot;
  <a href="#quickstart">Quickstart</a> &middot;
  <a href="spec/SPECIFICATION.md">Spec</a>
</p>

---

<p align="center">
  <img src="demo.gif" alt=".fylle demo — CrewAI to OpenAI bridge" width="700">
</p>

---

## The problem

We build AI agents for our platform [Fylle](https://fylle.ai). One day we realized: if the framework we use changes its API, gets acquired, or something better comes out — we have to rewrite everything.

Our agents were locked inside the runtime. The prompts, the model configs, the tool declarations, the guardrails — all coupled to one framework.

We needed a way to **define agents independently from the runtime**, so we could:

- Switch frameworks without rewriting agents
- Version agent definitions in Git
- Share agents across teams and projects
- Test and validate agents before deploying them

So we built `.fylle`.

## What is .fylle?

A `.fylle` file is a ZIP archive that contains a complete AI agent definition:

```
my-agent.fylle
├── manifest.yaml      # Identity, model, inputs/outputs, tools
├── agent.md           # System prompt — the agent's personality
├── guardrails.yaml    # Rules, limits, constraints (optional)
├── skills/            # Modular capabilities (optional)
├── memory-schema.yaml # What the agent remembers (optional)
└── README.md          # Human documentation (optional)
```

It's **declarative** — it says WHAT the agent is, not HOW to run it. Any runtime reads the parts it understands and ignores the rest.

## How it works

### 1. Define your agent

```yaml
# manifest.yaml
fylle_format: "0.1.0"

agent:
  name: "Content Curator"
  version: "1.0.0"
  description: "Finds and curates relevant content for newsletters"
  role: "Research Specialist"

  model:
    preferred: "claude-sonnet-4-5"
    minimum_capability: ["tool-use"]
    settings:
      temperature: 0.7

  prompt_file: "agent.md"

  inputs:
    - name: "topic"
      type: "text"
      required: true
      description: "What to research"

  tools:
    required:
      - name: "web_search"
        protocol: "mcp"
        description: "Search the web for current information"

  guardrails:
    max_autonomy: "draft-only"
    limits:
      max_iterations: 30
```

### 2. Parse, validate, build — with the Python SDK

```python
from fylle_format import parse_fylle_package, validate, build_fylle_package

# Parse
agent = parse_fylle_package("my-agent.fylle")
print(agent.manifest.agent.name)   # "Content Curator"
print(agent.personality)            # Full system prompt

# Validate
result = validate(agent)
print(result.valid)     # True
print(result.warnings)  # [...]
```

### 3. Run on any framework

The `.fylle` format is runtime-agnostic. Each framework reads what it needs:

| Runtime | What it reads from .fylle |
|---|---|
| **CrewAI** | role → role, description → goal, agent.md → backstory |
| **OpenAI Assistants** | name, agent.md → instructions, tools, temperature |
| **LangChain** | model, agent.md → system prompt, tools |
| **Your runtime** | Read the manifest, use what you need |

## Bridge

The bridge is where `.fylle` gets practical. It translates agents between frameworks — with `.fylle` as the interchange format in the middle.

**Today it supports:**

| From | To | Status |
|---|---|---|
| CrewAI (YAML) | .fylle | Working |
| .fylle | CrewAI (YAML) | Working |
| OpenAI Assistants (JSON) | .fylle | Working |
| .fylle | OpenAI Assistants (JSON) | Working |
| **OpenClaw (SOUL.md)** | **.fylle** | **Working** |
| **.fylle** | **Claude Code (CLAUDE.md)** | **Working** |
| .fylle | Live execution (Claude / GPT) | Working |

### Import a CrewAI agent, export to OpenAI — in 5 lines

```python
from fylle_bridge import crewai_to_fylle, fylle_to_openai, run_fylle_agent

# CrewAI YAML → .fylle
agent = crewai_to_fylle({"researcher": {"role": "Analyst", "goal": "Research trends", "backstory": "You are an expert analyst..."}})

# .fylle → OpenAI Assistant JSON
openai_config = fylle_to_openai(agent)
# → {"model": "gpt-4o", "name": "Researcher", "instructions": "You are an expert analyst...", ...}

# Or just run it
response = run_fylle_agent(agent, {"task": "Analyze AI agent standards"})
```

### Run the demo

```bash
cd sdk/python

# Install
pip install -e ".[bridge]"

# Run (no API key needed)
python fylle_bridge/demo/run_demo.py --dry-run

# Run with live execution
ANTHROPIC_API_KEY=sk-... python fylle_bridge/demo/run_demo.py
```

The demo shows the full flow: **CrewAI YAML → .fylle → validate → build package → OpenAI JSON → live execution**.

## Migrate from OpenClaw

Moving from OpenClaw to Claude Code? `.fylle` handles the migration. Your SOUL.md agent definition goes in, a complete Claude Code workspace comes out — CLAUDE.md, settings, rules, everything.

```python
from fylle_bridge import openclaw_to_fylle, fylle_to_claude_code

# Step 1: Import your OpenClaw agent
agent = openclaw_to_fylle(open("SOUL.md").read())

# Step 2: Export to Claude Code
workspace = fylle_to_claude_code(agent)

# workspace contains:
# - claude_md:      CLAUDE.md content (your system prompt)
# - settings_json:  .claude/settings.json (model, permissions)
# - rules:          .claude/rules/*.md (your agent rules)
# - mcp_json:       .mcp.json (tool config, if any)
```

### Run the migration demo

```bash
cd sdk/python
pip install -e ".[bridge]"

# Migrate with sample agent
python fylle_bridge/demo/run_migration_demo.py

# Migrate your own agent and write files to disk
python fylle_bridge/demo/run_migration_demo.py --soul /path/to/SOUL.md --output ./my-project

# Then use Claude Code directly
cd ./my-project && claude
```

### What gets migrated

| OpenClaw (SOUL.md) | Claude Code | Notes |
|---|---|---|
| `# AgentName` | CLAUDE.md title | Agent name |
| `## Personality` | CLAUDE.md body | System prompt |
| `## Rules` | `.claude/rules/agent-rules.md` | One rule per line |
| `## Skills` | Tool declarations | Preserved in .fylle |
| `## Identity → Model` | `settings.json → model` | Provider prefix stripped |
| `## Greeting`, `USER.md` | `extensions.openclaw` | Preserved for roundtrip |

## Two formats

| | `.fylle` | `.fyllepack` |
|---|---|---|
| **What** | A single agent | A multi-agent workflow |
| **Contains** | manifest + prompt + skills | manifest + pipeline + N agents |
| **Use case** | "I need a content curator" | "I need a full content pipeline" |

```
newsletter-creator.fyllepack
├── manifest.yaml
├── agents/
│   ├── curator.fylle      # Each agent is independently valid
│   ├── writer.fylle
│   └── reviewer.fylle
├── brief_schema.yaml      # Questions before execution
└── README.md
```

## Design principles

1. **Declarative** — describes what the agent IS, not how to execute it
2. **Human-readable** — YAML and Markdown, no proprietary formats
3. **Graceful degradation** — unknown fields are ignored, not rejected
4. **Extensions welcome** — any runtime can add its own block under `extensions:`
5. **Security by default** — guardrails, autonomy limits, and validation built in

## Relationship to other standards

`.fylle` doesn't replace existing standards — it sits alongside them:

| Standard | What it does | How .fylle relates |
|---|---|---|
| **MCP** (Anthropic) | Connects agents to tools | `.fylle` declares which MCP servers an agent needs |
| **A2A** (Google) | Agent-to-agent communication | `.fylle` agents can participate in A2A |
| **OAF** | Agent format (YAML + Markdown) | Similar goals — `.fylle` adds packaging and bridge |
| **Agent Spec** (Oracle/Google) | Agent schema (JSON/YAML) | Complementary — `.fylle` focuses on portability |

## Quickstart

```bash
# Install the SDK
pip install fylle-format

# Install with bridge adapters (for CrewAI/OpenAI translation)
pip install "fylle-format[bridge]"
```

```python
from fylle_format import create_fylle_from_scratch, build_fylle_package, validate

# Create an agent
agent = create_fylle_from_scratch(
    name="My Agent",
    description="Does amazing things",
    personality="You are a helpful assistant specialized in...",
    author_name="Your Name",
)

# Validate
result = validate(agent)
print(result.valid)  # True

# Package it
build_fylle_package(agent, "my-agent.fylle")
```

## Project structure

```
.fylle/
├── spec/
│   └── SPECIFICATION.md              # Format specification v0.1.0
├── examples/
│   ├── content-curator/              # Single agent example
│   ├── compliance-checker/           # Agent with guardrails
│   └── newsletter-pack/              # Multi-agent workflow
├── sdk/python/
│   ├── fylle_format/                 # Core SDK (parse, validate, build)
│   ├── fylle_bridge/                 # Framework adapters + runner
│   │   ├── adapters/                 # CrewAI, OpenAI, OpenClaw, Claude Code
│   │   ├── runner/                   # Live agent execution
│   │   └── demo/                     # Bridge demo + migration demo
│   └── tests/                        # 72 tests, all passing
├── cli/                              # CLI tool (planned)
└── LICENSE                           # Apache 2.0
```

## Status

> **v0.1.0** — built for our own needs, shared in case it's useful to others.

- [x] Format specification v0.1.0
- [x] Python SDK (parse, validate, build) — 72 tests passing
- [x] CrewAI adapter (import/export)
- [x] OpenAI Assistants adapter (import/export)
- [x] **OpenClaw adapter** (SOUL.md import/export)
- [x] **Claude Code adapter** (CLAUDE.md + settings + rules export)
- [x] **OpenClaw → Claude Code migration** (full pipeline)
- [x] Live agent runner (Anthropic + OpenAI)
- [x] End-to-end demos (bridge + migration)
- [ ] More adapters (AutoGen, Dify, LangChain)
- [ ] CLI tool
- [ ] npm SDK

## Origin

`.fylle` was born as an internal tool at [Fylle](https://fylle.ai), where we build AI-powered content workflows. We needed a way to define our agents independently from the frameworks we use — so that when the ecosystem changes (and it will), our agents survive.

We open-sourced it because if you're building with AI agents, you probably have the same problem.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs for new framework adapters are especially welcome.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
