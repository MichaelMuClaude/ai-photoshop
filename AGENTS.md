# AGENTS.md — guide for AI agents contributing to ai-photoshop

This file is for AI coding agents that read, test, or change this project. The human-facing rules are in [CONTRIBUTING.md](CONTRIBUTING.md).

## What this project is

`ai-photoshop` applies recipes of explicit image operations. An agent can read the operation list, write a recipe, check it, apply it to a new file, and look at the result.

## Promises to keep

1. **The input is never overwritten.** `save_image` must refuse an output that is the input.
2. **Validate before drawing.** Every step passes `recipe.py` before any image is touched. Unknown names and parameters are errors, never ignored.
3. **Every operation is in `ops.py`.** Each one has a summary, typed parameters with ranges, and an implementation. The `ops` command is generated from this list, so it stays accurate.
4. **Stable output.** `apply` prints JSON with the input, output, and per-step sizes. Keep the keys stable.
5. **Size limit.** Keep `MAX_PIXELS` in place. Decoding very large images is slow and can exhaust memory.
6. **No network access.** Everything is local.

## Layout

```
src/ai_photoshop/
  ops.py      operations, their parameters, and their implementations
  recipe.py   reads and checks recipes
  engine.py   loads images, applies steps, saves results
  cli.py      info, ops, validate, apply
tests/        pytest suite; conftest.py makes a small sample image
```

## Setup and checks

```bash
python3 -m venv ~/.venvs/ai-photoshop-dev
~/.venvs/ai-photoshop-dev/bin/pip install -e ".[dev]"
~/.venvs/ai-photoshop-dev/bin/python -m pytest -q
```

## Adding an operation

1. Add an `_register(...)` call in `ops.py` with a summary and typed parameters.
2. Write the implementation and check every parameter in it.
3. Add tests for the result and for each invalid value.
4. Update the operation table in `README.md` and `SKILL.md`.

## Rules for changes

- One change per pull request, with tests.
- Keep the Python floor at 3.10.
- Do not add a dependency unless Pillow cannot do the job.

## Security

Do not report vulnerabilities in a public issue. Use a private security advisory on GitHub.
