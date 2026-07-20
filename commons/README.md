# Fylle Commons

Reference implementations of reusable AI-agent behavior: native harness
skills, portable `.fylle` agents, and multi-agent `.fyllepack` workflows.

The working assumption behind this library is simple:

> Agent behavior and process are shareable. Compounding context is not.

Prompts, skills, and pipeline topology are useful building blocks, but the
durable advantage of an operational agent usually lives in its information,
memory, feedback, evaluation rules, relationships, and history. The commons
publishes the building blocks without publishing private context.

## Catalog

### Skills

- [`critical-reviewer`](skills/critical-reviewer/) — evidence-bound stress
  testing for documents, code, architecture, strategy, products, and theories.

### Portable agents

- [`critical-reviewer`](agents/critical-reviewer/) — the reviewer as a
  standalone `.fylle` source directory.

### Workflow packs

- [`blog-post-with-hero`](packs/blog-post-with-hero/) — research → edit →
  contextual hero image.
- [`social-post-with-visuals`](packs/social-post-with-visuals/) — copy and
  platform variants → two generated visuals.
- [`static-ad-variants`](packs/static-ad-variants/) — creative strategy → four
  static paid-social variants.
- [`video-ad-10s`](packs/video-ad-10s/) — ten-second paid-social strategy →
  video generation.

The original newsletter workflow remains in
[`examples/newsletter-pack/`](../examples/newsletter-pack/).

## Source and artifact convention

- Track human-readable source directories in Git.
- Build `.fylle` and `.fyllepack` ZIP artifacts for distribution.
- Do not commit generated archives; releases or registries should carry them.
- Treat model and tool names as preferences or capabilities, not hidden
  runtime dependencies.
- When the same behavior has harness-specific and `.fylle` representations,
  declare the canonical source in a namespaced extension. For
  `critical-reviewer`, the native `SKILL.md` is canonical and the portable
  agent is its maintained adapter.

## Publication gate

Every contribution must pass all of these checks:

1. **Used** — exercised in a real workflow or explicitly marked experimental.
2. **Generalized** — client, person, industry, path, and vendor assumptions are
   represented as declared inputs or capabilities.
3. **Sanitized** — no private context, customer data, credentials, signed URLs,
   account identifiers, logs, local paths, or production output.
4. **Portable** — dependencies state what is needed; the runtime decides how
   to provide it.
5. **Validated** — native skills pass their validator; `.fylle` agents and
   `.fyllepack` graphs pass `commons/validate.py`.
6. **Bounded** — documentation states tested behavior and known limitations.

## Validate

From the repository root:

```bash
python commons/validate.py
```

The script validates native skill metadata, builds and reparses every
`.fylle` agent in a temporary directory, validates every pack graph, and
assembles temporary `.fyllepack` archives. It does not modify the source tree.

## Contributing

See the root [CONTRIBUTING.md](../CONTRIBUTING.md). Contributions should be
small, reviewable, and tied to one observable use case. A generic prompt dump
is not a commons entry.
