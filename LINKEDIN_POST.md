# LinkedIn Post — .fylle launch

---

I'm building an AI platform with multiple agents.

One day I realized: if CrewAI changes its API, or something better comes out, I have to rewrite everything. My agents were locked inside the framework — the prompts, the model configs, the tools, the guardrails. All coupled to one runtime.

So I asked a simple question: why isn't there a standard way to define an AI agent, independent from the framework that runs it?

Apps have Docker. Packages have npm. AI agents have... nothing.

Every framework defines agents differently. CrewAI uses YAML. OpenAI uses JSON. LangChain uses Python. Switch framework → rewrite everything.

So I built .fylle — a portable format for AI agents.

A .fylle file is a simple ZIP that contains everything about an agent: identity, system prompt, model preferences, tools, inputs/outputs, guardrails. Framework-agnostic. Human-readable. Versionable in Git.

Today it does this:

→ Take a CrewAI agent (YAML)
→ Convert it to .fylle (3 lines of Python)
→ Export it as an OpenAI Assistant (JSON)
→ Run it live

Same agent. Three formats. Zero lock-in.

It started as an internal tool — I needed to protect my agents from framework changes. I open-sourced it because if you build with AI agents, you probably have the same problem.

It's a v0.1.0. It's early. But the Python SDK works, the bridge works, and there are 44 tests passing.

If this resonates, check it out: https://github.com/FylleAI/.fylle

---

## Notes for posting

**Format:** Plain text, no hashtags spam. Max 2-3 at the end if needed.
**Hashtags (optional):** #AIAgents #OpenSource #BuildInPublic
**Media:** Attach the terminal GIF showing the demo flow (5 steps).
**Length:** ~1300 characters — within LinkedIn's sweet spot.

**Who to tag (optional):**
- Harrison Chase (LangChain) — if you know him
- João Moura (CrewAI) — if you know him
- Relevant AI/ML communities
