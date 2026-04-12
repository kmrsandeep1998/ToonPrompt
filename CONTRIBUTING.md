# Contributing

Thanks for helping improve ToonPrompt.

## What to work on

- Docs, packaging, and workflow improvements are the safest first contributions.
- Runtime changes should include tests unless the change is strictly documentation or metadata.
- Keep prompt-transform behavior fail-open unless a change is clearly covered by tests.

## Local workflow

```bash
git clone https://github.com/kmrsandeep1998/ToonPrompt.git
cd ToonPrompt
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

If you use pre-commit:

```bash
pre-commit install
pre-commit run --all-files
```

## Pull requests

- Keep PRs focused on one change set.
- Describe user-visible impact and any packaging or release implications.
- Link related issues when relevant.
- Do not include generated artifacts unless the change explicitly requires them.

## Release hygiene

- Bump the alpha version in `pyproject.toml` and `src/toonprompt/__init__.py` together.
- Update `CHANGELOG.md` with a short release summary.
- Verify `python -m build` succeeds before tagging.
