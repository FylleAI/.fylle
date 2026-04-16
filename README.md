<p align="center">
  <h1 align="center">.fylle</h1>
  <p align="center"><strong>Move AI agents between frameworks without rewriting them.</strong></p>
  <p align="center">CrewAI &rarr; .fylle &rarr; OpenAI. &nbsp; OpenClaw &rarr; .fylle &rarr; Claude Code. &nbsp; Works today.</p>
</p>

<p align="center">
  <img src="assets/demo.gif" alt=".fylle migration demo — OpenClaw to Claude Code" width="700">
</p>

---

## What works today

`.fylle` is a migration compiler for AI agents. You define an agent once in a portable YAML+Markdown format, then import/export it across frameworks.

**4 framework adapters, all working:**

| Direction | What happens |
|---|---|
| CrewAI YAML &harr; .fylle | Import/export CrewAI agent definitions |
| OpenAI Assistants JSON &harr; .fylle | Import/export OpenAI assistant configs |
| OpenClaw SOUL.md &harr; .fylle | Import/export OpenClaw agent definitions |
| Claude Code workspace &harr; .fylle | Import/export CLAUDE.md + settings + rules |

**Core SDK:**
- Parser, builder, validator for the `.fylle` format
- `.fyllepack` format for multi-agent workflows
- Simple runner (Anthropic + OpenAI live execution)
- 72 tests, all passing

**Full migration pipeline:**
OpenClaw &rarr; .fylle &rarr; Claude Code in one command — writes CLAUDE.md, settings.json, rules, and MCP config to disk. Then you run `claude` and your agent is live.

---

## Try the migration demo in 30 seconds

```bash
git clone https://github.com/FylleAI/.fylle.git fylle
cd fylle/sdk/python && pip install -e .

# This is the migration — one command:
python fylle_bridge/demo/run_migration_demo.py --output ./my-agent

# Then use your migrated agent:
cd ./my-agent && claude
```

No API key needed for the migration. The demo takes a sample OpenClaw agent, converts it through `.fylle`, and generates a ready-to-use Claude Code workspace.

> Add `[bridge]` to the install (`pip install -e ".[bridge]"`) if you want live execution with Anthropic or OpenAI APIs.

---

## How it works

A `.fylle` file is a ZIP archive containing a complete agent definition:

```
my-agent.fylle
├── manifest.yaml      # Identity, model, inputs/outputs, tools
├── agent.md           # System prompt
├── guardrails.yaml    # Rules, limits, constraints (optional)
├── skills/            # Modular capabilities (optional)
├── memory-schema.yaml # What the agent remembers (optional)
└── README.md          # Documentation (optional)
```

It's YAML and Markdown. Any runtime reads what it understands, ignores the rest.

### Define an agent

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

### Migrate between frameworks

```python
from fylle_bridge import crewai_to_fylle, fylle_to_openai

# CrewAI YAML → .fylle → OpenAI Assistant JSON
agent = crewai_to_fylle({
    "researcher": {
        "role": "Analyst",
        "goal": "Research trends",
        "backstory": "You are an expert analyst..."
    }
})
openai_config = fylle_to_openai(agent)

# Or from an existing CrewAI YAML file:
from fylle_bridge import crewai_to_fylle_yaml
agent = crewai_to_fylle_yaml("my_crew/agents.yaml")
```

```python
from fylle_bridge import openclaw_to_fylle, fylle_to_claude_code

# OpenClaw SOUL.md → .fylle → Claude Code workspace
agent = openclaw_to_fylle(open("SOUL.md").read())
workspace = fylle_to_claude_code(agent)
# → CLAUDE.md, settings.json, rules/*.md, .mcp.json
```

### Run the bridge demo

```bash
cd sdk/python
pip install -e ".[bridge]"

# Dry run (no API key needed)
python fylle_bridge/demo/run_demo.py --dry-run

# Live execution
ANTHROPIC_API_KEY=sk-... python fylle_bridge/demo/run_demo.py
```

---

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
│   ├── curator.fylle
│   ├── writer.fylle
│   └── reviewer.fylle
├── brief_schema.yaml
└── README.md
```

---

## Relationship to other standards

`.fylle` is not trying to replace any framework — it sits between them as a translation layer.

| Standard / Framework | Relationship |
|---|---|
| **CrewAI** | Bidirectional adapter. Import/export CrewAI YAML definitions |
| **OpenAI Assistants** | Bidirectional adapter. Import/export assistant JSON configs |
| **OpenClaw** | Bidirectional adapter. Import/export SOUL.md agent definitions |
| **Claude Code** | Bidirectional adapter. Import/export CLAUDE.md + full workspace |
| **Claude Agent SDK** | Planned adapter. Next priority |
| **LangGraph** | Planned adapter. Graph-based workflow mapping |

---

## Status

**Done:**
- Format specification v0.1.0
- Python SDK — parser, builder, validator
- `.fyllepack` multi-agent format
- CrewAI adapter (import + export)
- OpenAI Assistants adapter (import + export)
- OpenClaw adapter (import + export)
- Claude Code adapter (import + export)
- Simple runner (Anthropic + OpenAI)
- OpenClaw → Claude Code full migration pipeline
- 72 tests passing

**Coming:**
- Python CLI
- `.fyllepack` runner (multi-agent orchestration)
- Claude Agent SDK adapter
- LangGraph adapter
- Fylle Hub (agent registry)

---

## Project structure

```
.fylle/
├── spec/
│   └── SPECIFICATION.md           # Format specification v0.1.0
├── examples/
│   ├── content-curator/           # Single agent example
│   ├── compliance-checker/        # Agent with guardrails
│   └── newsletter-pack/          # Multi-agent workflow
├── sdk/python/
│   ├── fylle_format/              # Core SDK (parse, validate, build)
│   ├── fylle_bridge/              # Framework adapters + runner
│   │   ├── adapters/              # CrewAI, OpenAI, OpenClaw, Claude Code
│   │   ├── runner/                # Live agent execution
│   │   └── demo/                  # Bridge demo + migration demo
│   └── tests/                     # 72 tests
├── assets/
│   └── demo.gif                   # Migration demo recording
└── LICENSE                        # Apache 2.0
```

## Why this exists

We build AI-powered content workflows at [Fylle](https://fylle.ai). Our agents were locked inside one framework — every time the API changed or something better came out, we had to rewrite everything.

`.fylle` started as our internal migration tool. We open-sourced it because if you work with AI agents across multiple frameworks, you probably have the same problem.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs for new framework adapters are especially welcome.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
