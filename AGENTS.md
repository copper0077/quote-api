# Repository Guidelines for Codex Agents

This repository contains a Flask-based API for generating fleet quotes. To maintain consistency and quality, follow these rules when updating the codebase:

## Coding Style
- Use **4 spaces** for indentation in Python files.
- Use **2 spaces** for indentation in HTML templates.
- Keep line lengths under **120 characters** when possible.

## Programmatic Checks
Run these commands before committing any changes:

```bash
pytest -q
python -m py_compile $(git ls-files '*.py')
```

Both commands should exit with a zero status. If they fail, fix the issues before committing.

## Pull Request Guidelines
- Summarize the changes in a "Summary" section.
- Include the output of the programmatic checks in a "Testing" section.
