# .fylle Format Specification

**Version:** 0.1.0
**Status:** Draft
**License:** Apache 2.0

---

## 1. Overview

A `.fylle` file is a ZIP archive with the `.fylle` extension that contains a complete, portable AI agent definition. The format is designed to be:

- **Declarative** — describes what an agent IS, not how to execute it
- **Runtime-agnostic** — any platform can interpret and run a .fylle agent
- **Human-readable** — YAML and Markdown, inspectable without tools
- **Extensible** — unknown fields are ignored, not rejected

### 1.1 Why ZIP and not a flat file or a bare directory

`.fylle` deliberately chooses ZIP over the two obvious alternatives:

- **A single YAML/JSON file with the prompt and skills inlined.** Simpler to email, but: (a) loses the readable separation between config (YAML) and prose (Markdown system prompts), (b) forces escaping of every newline and quote in long prompts, (c) makes `git diff` painful for the most-edited file, (d) cannot grow to hold binary assets (fixtures, classifiers, sample inputs) without base64 bloat.
- **A bare directory.** This _is_ how you author a `.fylle` agent — and it is the canonical source form (see the development-workflow section in the README). But for distribution, a directory is awkward: there is no canonical hash to verify integrity, no single artifact to upload to a registry, no MIME type, no file association in operating systems, and no obvious unit for a CDN or signed URL.

ZIP gives you both:

| Property | Why it matters |
|---|---|
| Single file with a stable extension | One artifact to publish, sign, hash, share, or attach to a release |
| Standard ZIP headers (`PK\x03\x04`) | Every OS, language, and HTTP client reads it without a custom library |
| Internal directory structure preserved | `manifest.yaml`, `agent.md`, `skills/` stay editable and diffable when unpacked |
| Allows non-text payloads | A future skill can ship a small binary (e.g. classifier, fixture, sample) without re-encoding |
| Streamable + random-access | A registry can serve `manifest.yaml` from a remote `.fylle` without downloading the whole package |
| MIME-typeable | `application/vnd.fylle.agent+zip` enables content negotiation and OS handlers |

The trade-off accepted: a `.fylle` is not edited in place with a text editor — you `unpack`, edit, then `pack` again. This matches the directory-as-source / ZIP-as-artifact convention already used by `.docx`, `.epub`, `.jar`, `.whl`, and similar formats.

## 2. Package structure

```
my-agent.fylle (ZIP archive)
├── manifest.yaml          # REQUIRED — agent identity and configuration
├── agent.md               # REQUIRED — system prompt / agent instructions
├── skills/                # OPTIONAL — modular skill definitions
│   ├── skill-name.yaml
│   └── ...
├── guardrails.yaml        # OPTIONAL — rules, constraints, limits
├── memory-schema.yaml     # OPTIONAL — memory structure declaration
└── README.md              # OPTIONAL — human documentation (not parsed)
```

### 2.1 Required files

| File | Purpose |
|---|---|
| `manifest.yaml` | Agent identity, model requirements, inputs, outputs, tool declarations |
| `agent.md` | The agent's system prompt — its complete behavioral instructions |

### 2.2 Optional files

| File | Purpose |
|---|---|
| `skills/*.yaml` | Modular capabilities the agent can perform |
| `guardrails.yaml` | Behavioral rules, content policies, operational limits |
| `memory-schema.yaml` | Declaration of what the agent should remember across sessions |
| `README.md` | Human-readable documentation (ignored by parsers) |

## 3. manifest.yaml — Complete schema

```yaml
# ============================================================
# .fylle manifest — version 0.1.0
# ============================================================

fylle_format: "0.1.0"          # REQUIRED — format version (semver)

agent:
  # ── IDENTITY (required) ──────────────────────────────────
  name: "string"               # REQUIRED — display name, max 100 chars
  version: "string"            # REQUIRED — agent version, semver (e.g. "1.0.0")
  description: "string"        # REQUIRED — one-line description, max 500 chars
  role: "string"               # OPTIONAL — agent's role/persona (e.g. "Research Specialist")

  # ── AUTHORSHIP (required) ────────────────────────────────
  author:
    name: "string"             # REQUIRED — author or organization name
    url: "string"              # OPTIONAL — website URL
    email: "string"            # OPTIONAL — contact email
  license: "string"            # REQUIRED — SPDX identifier (e.g. "MIT", "Apache-2.0")

  # ── MODEL REQUIREMENTS (required) ───────────────────────
  model:
    preferred: "string"        # REQUIRED — preferred model ID (e.g. "claude-sonnet-4-5")
    minimum_capability:        # OPTIONAL — list of required capabilities
      - "tool-use"             #   Can use tools/function calling
      - "long-context"         #   Needs >32K context window
      - "vision"               #   Can process images
      - "code-execution"       #   Can execute code
    settings:                  # OPTIONAL — default model settings
      temperature: 0.7         #   Sampling temperature (0.0–2.0)
      max_tokens: 4000         #   Max tokens per response

  # ── SYSTEM PROMPT (required) ─────────────────────────────
  prompt_file: "agent.md"      # REQUIRED — path to system prompt file
  tone: "string"               # OPTIONAL — comma-separated tone descriptors
  language:                    # OPTIONAL — supported languages (ISO 639-1)
    - "en"
    - "it"

  # ── INPUTS (optional but recommended) ────────────────────
  # Declares what the agent expects to receive from the runtime.
  # This enables composability: runtimes know what to inject.
  inputs:
    - name: "string"           # Input identifier (snake_case)
      type: "string"           # One of: "text", "json", "file", "image"
      required: true           # Whether the agent needs this to function
      description: "string"    # Human-readable description of this input

  # ── OUTPUT (optional) ────────────────────────────────────
  output:
    format: "string"           # Expected output format:
                               #   "markdown", "json", "text", "html",
                               #   "structured_report", "free"

  # ── TOOLS (optional) ────────────────────────────────────
  # Declares external tools/services the agent needs.
  # The runtime maps these to actual implementations.
  tools:
    required:                  # Agent won't work without these
      - name: "string"        #   Tool identifier (e.g. "web_search")
        protocol: "string"    #   "mcp", "function", "api"
        description: "string" #   Why this tool is needed
        server: "string"      #   OPTIONAL — specific server (e.g. "perplexity")
    optional:                  # Agent works but with reduced capabilities
      - name: "string"
        protocol: "string"
        description: "string"
        server: "string"

  # ── SKILLS (optional) ────────────────────────────────────
  skills:
    - ref: "skills/skill-name.yaml"   # Relative path to skill file

  # ── GUARDRAILS (optional) ────────────────────────────────
  guardrails:
    file: "guardrails.yaml"    # Path to guardrails file
    max_autonomy: "string"     # One of:
                               #   "full" — agent executes without approval
                               #   "draft-only" — agent creates drafts, human publishes
                               #   "human-approval" — agent proposes, human approves each step
    limits:                    # OPTIONAL — inline limits (override guardrails.yaml)
      max_iterations: 50       #   Max tool/action iterations per run
      max_tokens_per_response: 4000

  # ── MEMORY (optional) ───────────────────────────────────
  memory:
    schema_file: "memory-schema.yaml"  # Path to memory schema
    persistence: "host-managed"        # Always "host-managed" — runtime decides storage

  # ── METADATA (optional) ─────────────────────────────────
  tags:                        # Searchable tags
    - "marketing"
    - "content"
  category: "string"           # Primary category
  homepage: "string"           # URL to project page
  repository: "string"         # URL to source code

  # ── RUNTIME EXTENSIONS (optional) ───────────────────────
  # Any runtime can add its own configuration block here.
  # Unknown extensions are ignored by other runtimes (graceful degradation).
  extensions:
    fylle:                     # Fylle-specific extensions
      original_agent_name: "string"    # Agent name in Fylle pack
      original_pack_id: "string"       # Pack ID in Fylle platform
      feedback_loop:
        enabled: true
        metrics:
          - "content_engagement"
          - "approval_rate"
          - "revision_count"
      context_sources:
        - type: "brand"
        - type: "audience"
        - type: "compliance"
    # Other runtimes can add their own:
    # langchain:
    #   agent_type: "react"
    # crewai:
    #   allow_delegation: true
```

## 4. agent.md — System prompt

The `agent.md` file contains the agent's complete behavioral instructions in Markdown format. This is the "brain" of the agent — the system prompt that defines how it thinks, responds, and acts.

### Guidelines

- Write in the imperative: "You are a...", "Your goal is...", "When asked to..."
- Use Markdown headers to organize sections
- Include examples where helpful
- Reference inputs by name: "Use the `brand_context` input to..."
- Reference skills: "When the user asks to write content, use the Content Writing skill"
- Keep it focused — one agent, one clear purpose

### Example

```markdown
# Content Curator

You are a content curation specialist. Your job is to find, evaluate,
and organize relevant content for marketing newsletters.

## Your approach

1. Analyze the `topic` input to understand what to research
2. Use web search to find current, relevant sources
3. If `brand_context` is provided, align findings with brand voice
4. Synthesize findings into a structured, actionable brief

## Output format

Always structure your output as:
- **Key findings** (3-5 bullet points)
- **Recommended sources** (with links)
- **Suggested angles** for content creation

## Rules

- Never fabricate sources or statistics
- Prefer recent content (last 30 days)
- Always cite your sources
```

## 5. skills/skill-name.yaml — Skill schema

Skills are modular capabilities that an agent can perform. Each skill is a YAML file in the `skills/` directory.

```yaml
skill:
  # ── IDENTITY (required) ──────────────────────────────────
  name: "string"               # Display name
  version: "string"            # Semver
  description: "string"        # What this skill does (multiline OK)

  # ── TRIGGERS (optional) ──────────────────────────────────
  triggers:                    # Natural language phrases that activate this skill
    - "write content"
    - "create a post"
    - "draft an article"

  # ── INSTRUCTIONS (required) ──────────────────────────────
  instructions: |              # Detailed instructions for the LLM
    When asked to create content:
    1. Check brand_guidelines in memory
    2. Identify target platform and audience
    3. Draft content matching brand tone
    4. Include required disclaimers

  # ── TOOLS USED (optional) ────────────────────────────────
  tools_used:                  # Which tools this skill needs
    - "web_search"
    - "save_notes"

  # ── OUTPUT (optional) ───────────────────────────────────
  output_format: "string"      # Expected output: "markdown", "json", "text", "free"

  # ── INPUT SCHEMA (optional) ─────────────────────────────
  # For structured invocation — declares expected parameters
  input_schema:
    type: "object"
    properties:
      topic:
        type: "string"
        description: "Content topic"
      platform:
        type: "string"
        enum: ["linkedin", "twitter", "blog", "newsletter"]
        description: "Target platform"
    required: ["topic"]
```

## 6. guardrails.yaml — Rules and constraints

```yaml
guardrails:
  # ── BEHAVIORAL RULES ─────────────────────────────────────
  rules:
    - id: "string"            # Rule identifier (kebab-case)
      description: "string"   # What this rule enforces
      severity: "string"      # One of:
                               #   "block" — hard stop, prevent action
                               #   "warn" — flag for review
                               #   "log" — track silently
      condition: "string"     # Natural language condition description

  # ── CONTENT POLICIES ─────────────────────────────────────
  content_policies:
    prohibited_topics: []      # Topics the agent must never discuss
    required_disclaimers: []   # Disclaimers to always include
    tone_boundaries: "string"  # What tone is NOT acceptable

  # ── OPERATIONAL LIMITS ───────────────────────────────────
  limits:
    max_tokens_per_response: 4000
    max_iterations: 50
    require_human_review: false    # Override: always require review
```

## 7. memory-schema.yaml — Memory declaration

Declares what the agent wants to remember. The runtime decides HOW to store it.

```yaml
memory:
  entities:
    - name: "string"           # Entity identifier (snake_case)
      type: "string"           # One of:
                               #   "document" — static reference material
                               #   "feed" — streaming/updating data
                               #   "log" — append-only history
                               #   "profile" — evolving user/context data
                               #   "index" — searchable knowledge base
      description: "string"   # Human-readable description
      retention: "string"     # One of:
                               #   "permanent"
                               #   "rolling_30_days"
                               #   "rolling_90_days"
                               #   "rolling_1_year"
                               #   "session"
```

How different runtimes interpret memory:

| Runtime | Implementation |
|---|---|
| Fylle | Structured DB with feedback loops and versioning |
| LangChain | Vector store entries or checkpointer state |
| Local runtime | Markdown files in workspace directory |
| Claude Agent SDK | Filesystem-based (CLAUDE.md pattern) |

## 8. Validation rules

A valid `.fylle` package MUST satisfy:

### Required
1. `manifest.yaml` exists and is valid YAML
2. `manifest.yaml` contains `fylle_format` version field
3. `manifest.yaml` contains `agent.name`, `agent.version`, `agent.description`
4. `manifest.yaml` contains `agent.author.name` and `agent.license`
5. `manifest.yaml` contains `agent.model.preferred`
6. `manifest.yaml` contains `agent.prompt_file` pointing to an existing file
7. The file referenced by `agent.prompt_file` exists and is non-empty
8. `agent.version` is valid semver
9. `fylle_format` is valid semver

### Recommended (warnings if missing)
1. At least one input declared
2. Output format specified
3. At least one skill defined

### Security
1. No path traversal in file paths (no `../`)
2. Package size must not exceed 10MB
3. Only allowed file types: `.yaml`, `.yml`, `.md`
4. No executable files
5. SHA-256 hash should be computed for integrity verification

## 9. Versioning

The `fylle_format` field declares which version of this specification the package targets.

- **Patch** (0.1.x): Bug fixes in spec wording, no schema changes
- **Minor** (0.x.0): New optional fields added (backward compatible)
- **Major** (x.0.0): Breaking changes to required fields

Runtimes SHOULD:
- Accept packages with a compatible `fylle_format` version
- Warn on unknown fields (don't reject)
- Reject packages with an incompatible major version

## 10. Extension mechanism

The `extensions` block in the manifest allows any runtime to add its own configuration. Extensions MUST:

1. Be namespaced under a unique key (e.g., `fylle`, `langchain`, `crewai`)
2. Be ignored by runtimes that don't recognize them
3. Never be required for the agent to function at a basic level

```yaml
extensions:
  fylle:
    feedback_loop:
      enabled: true
  langchain:
    agent_type: "react"
    memory_type: "buffer"
  crewai:
    allow_delegation: true
    reasoning: true
```

## 11. .fyllepack — Multi-agent workflow packages

While a `.fylle` file defines a **single agent**, a `.fyllepack` file defines a **multi-agent workflow** — an ordered pipeline of agents that collaborate to produce a final output.

Think of it this way:
- **`.fylle`** = a single worker (portable across any runtime)
- **`.fyllepack`** = a team of workers with a defined process (portable workflow)

### 11.1 Package structure

```
my-workflow.fyllepack (ZIP archive)
├── manifest.yaml              # REQUIRED — workflow identity and pipeline definition
├── agents/                    # REQUIRED — agent packages
│   ├── curator.fylle          # Each agent is a complete .fylle package
│   ├── writer.fylle
│   └── reviewer.fylle
├── brief_schema.yaml          # OPTIONAL — input questions for the workflow
├── guardrails.yaml            # OPTIONAL — workflow-level rules and limits
└── README.md                  # OPTIONAL — human documentation
```

### 11.2 manifest.yaml for .fyllepack

```yaml
fylle_format: "0.1.0"

pack:
  # ── IDENTITY (required) ──────────────────────────────────
  name: "string"               # Workflow name, max 100 chars
  version: "string"            # Semver
  description: "string"        # One-line description, max 500 chars

  # ── AUTHORSHIP (required) ────────────────────────────────
  author:
    name: "string"
    url: "string"              # optional
  license: "string"            # SPDX identifier

  # ── PIPELINE (required) ──────────────────────────────────
  # Ordered sequence of agents. Each step references a .fylle file.
  # Agents execute in order. Each agent can receive outputs from previous agents.
  pipeline:
    - name: "curator"                        # Step identifier (unique within pack)
      agent: "agents/curator.fylle"          # Path to .fylle package
      receives_from: []                      # First in chain — no dependencies
      input_mapping:                         # OPTIONAL — map workflow inputs to agent inputs
        topic: "brief.topic"                 #   agent input ← workflow source
        brand_context: "context.brand"

    - name: "writer"
      agent: "agents/writer.fylle"
      receives_from: ["curator"]             # Receives curator's output
      input_mapping:
        research: "agents.curator.output"    # Output from previous agent
        topic: "brief.topic"
        brand_context: "context.brand"

    - name: "reviewer"
      agent: "agents/reviewer.fylle"
      receives_from: ["writer"]
      input_mapping:
        content_to_review: "agents.writer.output"
        compliance_rules: "context.compliance"

  # ── EXECUTION MODE (optional) ────────────────────────────
  execution:
    mode: "sequential"         # "sequential" | "parallel" | "conditional"
    final_output: "reviewer"   # Which agent's output is the workflow result
    error_handling: "stop"     # "stop" | "skip" | "retry"

  # ── BRIEF SCHEMA (optional) ─────────────────────────────
  brief_schema:
    file: "brief_schema.yaml"  # Questions the user answers before execution

  # ── GUARDRAILS (optional) ────────────────────────────────
  guardrails:
    file: "guardrails.yaml"
    max_autonomy: "draft-only"

  # ── METADATA (optional) ─────────────────────────────────
  tags: ["marketing", "newsletter", "content"]
  category: "content-production"

  # ── RUNTIME EXTENSIONS (optional) ───────────────────────
  extensions:
    fylle:
      original_pack_id: "string"
      feedback_loop:
        enabled: true
        metrics: ["content_engagement", "approval_rate"]
      context_sources:
        - type: "brand"
        - type: "audience"
```

### 11.3 brief_schema.yaml

Defines the input questions a user answers before the workflow runs. The answers become available as `brief.*` variables in `input_mapping`.

```yaml
brief:
  questions:
    - id: "topic"
      question: "What's the main topic for this newsletter?"
      type: "text"                    # "text" | "select" | "multiselect" | "number"
      required: true

    - id: "audience"
      question: "Who is the target audience?"
      type: "select"
      options: ["B2B decision makers", "Developers", "General public"]
      required: true

    - id: "tone"
      question: "What tone should the content have?"
      type: "select"
      options: ["Professional", "Casual", "Technical"]
      required: false
      default: "Professional"
```

### 11.4 Input mapping syntax

The `input_mapping` field connects data sources to agent inputs using dot notation:

| Source | Syntax | Description |
|---|---|---|
| Brief answers | `brief.<question_id>` | User's answer to a brief question |
| Context data | `context.<type>` | Runtime-provided context (brand, audience, etc.) |
| Agent output | `agents.<name>.output` | Output from a previous agent in the pipeline |
| Static value | `"literal string"` | A hardcoded value |

### 11.5 Execution modes

| Mode | Description |
|---|---|
| `sequential` | Agents run one after another, in pipeline order (default) |
| `parallel` | Independent agents run simultaneously (requires no cross-dependencies) |
| `conditional` | Agents run based on conditions (e.g., skip reviewer if curator found nothing) |

> **Note:** `parallel` and `conditional` modes are planned for a future spec version. `sequential` is the only mode implemented in v0.1.0.

### 11.6 Relationship between .fylle and .fyllepack

```
.fyllepack (workflow)
│
├── Uses N × .fylle agents as building blocks
│
├── Adds orchestration:
│   ├── Pipeline order (who runs when)
│   ├── Input mapping (data flow between agents)
│   ├── Brief schema (user questions)
│   └── Execution mode (sequential/parallel/conditional)
│
└── Each .fylle agent remains independently portable
    └── You can extract curator.fylle and use it alone in LangChain
```

Key principle: **a .fylle agent inside a .fyllepack is a complete, valid .fylle package**. It doesn't depend on the pack to function. The pack only adds orchestration.

### 11.7 Validation rules for .fyllepack

1. `manifest.yaml` exists with `pack` root key (not `agent`)
2. `pack.pipeline` has at least one step
3. Each step references a `.fylle` file that exists in the archive
4. Each referenced `.fylle` is independently valid
5. `receives_from` references only steps that appear earlier in the pipeline
6. Step names are unique within the pipeline
7. `final_output` references a valid step name
8. No circular dependencies in `receives_from`

## 12. MIME types and file associations

| Format | Extension | MIME type | Description |
|---|---|---|---|
| Single agent | `.fylle` | `application/vnd.fylle.agent+zip` | One portable AI agent |
| Workflow pack | `.fyllepack` | `application/vnd.fylle.pack+zip` | Multi-agent workflow |

Both use standard ZIP headers (`PK\x03\x04`).

---

## Appendix A: Complete examples

- [`examples/content-curator/`](../examples/content-curator/) — A single agent (.fylle)
- [`examples/compliance-checker/`](../examples/compliance-checker/) — A single agent with guardrails (.fylle)
- [`examples/newsletter-pack/`](../examples/newsletter-pack/) — A multi-agent workflow (.fyllepack)

## Appendix B: Comparison with existing formats

| Feature | .fylle | .fyllepack | ADL | AGENTS.md | OpenAI Assistants |
|---|---|---|---|---|---|
| Scope | Single agent | Multi-agent workflow | Single agent | Project config | Single agent |
| Format | ZIP (YAML+MD) | ZIP (YAML + .fylle files) | JSON/YAML | Markdown | JSON API |
| Packaging | Yes (single file) | Yes (single file) | No | No | No (API only) |
| System prompt | Separate .md file | Per-agent .md files | Inline | Inline | Inline |
| Tool declaration | Declarative | Per-agent | Declarative | No | JSON Schema |
| Input/Output schema | Yes | Yes + mapping | No | No | Partial |
| Pipeline/orchestration | No | Yes | No | No | No |
| Skills/capabilities | Yes | Per-agent | No | No | No |
| Guardrails | Yes | Per-agent + workflow-level | Permissions | No | No |
| Memory schema | Yes | Per-agent | No | No | No |
| Extensions | Yes | Yes | No | No | Metadata only |
| Human-readable | Yes | Yes | Yes | Yes | No |
| Runtime-agnostic | Yes | Yes | Yes | Partial | No (OpenAI only) |
