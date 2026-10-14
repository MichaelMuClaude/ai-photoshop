# Contributing to ai-photoshop

Humans and AI agents are both welcome. The detailed rules for agents are in [AGENTS.md](AGENTS.md).

- Never overwrite the input image.
- Validate every parameter before drawing.
- Add a test for each behaviour change.

```bash
python3 -m venv ~/.venvs/ai-photoshop-dev
~/.venvs/ai-photoshop-dev/bin/pip install -e ".[dev]"
~/.venvs/ai-photoshop-dev/bin/python -m pytest -q
```

Describe what changed, why, and which tests you ran. If an AI agent helped, say so and name the tool and model.

By contributing, you agree that your contribution is released under the MIT licence in [LICENSE](LICENSE).
