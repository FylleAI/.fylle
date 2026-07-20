# Contributing to .fylle

We built `.fylle` for our own needs and open-sourced it in case it's useful to others. Contributions are welcome — especially new framework adapters.

## What we'd love help with

1. **New adapters** — AutoGen, LangChain, Dify, n8n, or any framework you use
2. **Bug reports** — if you find issues parsing, building, or validating
3. **Spec feedback** — if something in the format doesn't work for your use case
4. **SDK ports** — TypeScript/npm, Go, Rust
5. **Commons entries** — used, sanitized skills and portable workflow packs

## How to contribute

### Reporting issues

Use [GitHub Issues](https://github.com/FylleAI/.fylle/issues) for bugs, feature requests, and spec discussions.

### Adding a new adapter

The fastest way to contribute is adding a new framework adapter. Here's the pattern:

```python
# sdk/python/fylle_bridge/adapters/your_framework_adapter.py

from fylle_bridge.adapters.base import FrameworkAdapter
from fylle.schema import FylleAgent

class YourFrameworkAdapter(FrameworkAdapter):
    @property
    def framework_name(self) -> str:
        return "YourFramework"

    def to_fylle(self, source: dict) -> FylleAgent:
        # Map framework config → FylleAgent
        ...

    def from_fylle(self, agent: FylleAgent) -> dict:
        # Map FylleAgent → framework config
        ...
```

Look at `crewai_adapter.py` and `openai_adapter.py` for working examples.

### Development setup

```bash
cd sdk/python
pip install -e ".[dev,bridge]"
pytest  # 83 tests, all should pass
cd ../..
python commons/validate.py
```

### Adding a Commons entry

Read [`commons/README.md`](commons/README.md) before contributing. New entries
must be tied to an observable use case and must not contain private context,
customer data, credentials, signed URLs, account identifiers, logs, local
paths, or production output.

Choose one canonical source form:

- `commons/skills/<name>/` for a native harness skill;
- `commons/agents/<name>/` for a standalone `.fylle` source directory;
- `commons/packs/<name>/` for a `.fyllepack` workflow.

Run `python commons/validate.py` from the repository root before submitting.
Generated `.fylle` and `.fyllepack` archives do not belong in Git.

### Submitting code

1. Fork the repository
2. Create a branch for your change
3. Write tests for new functionality
4. Submit a PR with a clear description

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
