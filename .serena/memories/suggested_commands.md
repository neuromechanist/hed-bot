# Suggested Commands

## Environment Setup
```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Skip integration tests (no API calls)
uv run pytest -m "not integration"

# Only integration tests
uv run pytest -m integration

# Specific test file
uv run pytest tests/test_hed_lsp.py -v
```

## Linting & Formatting
```bash
# Format code
ruff format src/ tests/

# Lint with auto-fix
ruff check --fix --unsafe-fixes src/ tests/

# Type checking
ty check src/
```

## Version Bumping
```bash
# Never edit version manually; use the script
python scripts/bump_version.py patch --prerelease dev   # develop branch
python scripts/bump_version.py patch --prerelease a     # main branch
```

## Running the API
```bash
# Local development
uv run uvicorn src.api.main:app --reload --port 8000

# Docker
docker compose up
```

## CLI
```bash
# Initialize CLI config
hedit init --api-key sk-or-xxx

# Annotate text
hedit annotate "A red circle appears on screen"

# Annotate image
hedit annotate-image image.png

# Validate HED string
hedit validate "Sensory-event, Visual-presentation, (Red, Circle)"

# Check API health
hedit health
```

## Git
```bash
# Feature branch from develop
git checkout develop
git checkout -b feature/my-feature

# Atomic commits
git add -p
git commit -m "feat: description"

# Push and create PR (targets develop)
git push -u origin feature/my-feature
gh pr create --base develop
```

## System (Darwin/macOS)
```bash
git status
git log --oneline
ls -la
grep -r "pattern" src/
find . -name "*.py"
```
