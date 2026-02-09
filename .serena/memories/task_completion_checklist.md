# Task Completion Checklist

When completing a coding task, run these steps:

## 1. Format
```bash
ruff format src/ tests/
```

## 2. Lint
```bash
ruff check --fix --unsafe-fixes src/ tests/
```

## 3. Test
```bash
# Quick: skip integration tests
uv run pytest -m "not integration"

# Full: all tests
uv run pytest

# With coverage
uv run pytest --cov=src
```

## 4. Verify
- Check that all modified files pass linting
- Ensure no new test failures
- Verify type hints are correct for public APIs

## 5. Commit
- Atomic commits with `<type>: <description>` format
- No emojis, no co-author mentions
- PRs target `develop` branch (not main)
- Use `scripts/bump_version.py` if version needs updating
