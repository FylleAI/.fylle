"""Template strings for the `fylle init` command."""

MANIFEST_YAML = '''fylle_format: "0.1.0"

agent:
  name: "{name}"
  version: "1.0.0"
  description: "TODO: Describe what this agent does"
  role: "TODO: Agent role"

  author:
    name: "TODO: Your name"
  license: "MIT"

  model:
    preferred: "claude-sonnet-4-5"
    minimum_capability:
      - "tool-use"
    settings:
      temperature: 0.7

  prompt_file: "agent.md"

  inputs:
    - name: "task"
      type: "text"
      required: true
      description: "What the agent should do"

  output:
    format: "markdown"

  tools: {{}}

  guardrails:
    max_autonomy: "draft-only"
    limits:
      max_iterations: 30

  tags: []
  category: "general"
'''

AGENT_MD = '''# {name}

You are a helpful assistant. Describe your agent's personality, expertise, and behavior here.

## Your approach

1. Understand the task
2. Plan your response
3. Execute carefully

## Rules

- Be clear and concise
- Cite sources when possible
- Ask for clarification when the task is ambiguous
'''
