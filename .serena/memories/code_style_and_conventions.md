# Code Style and Conventions

## Python Style
- **Formatter**: ruff format (Black-compatible, 88 char line)
- **Linter**: ruff check with --fix --unsafe-fixes
- **Type checker**: ty
- **Imports**: Sorted via isort (ruff)
- **Python**: 3.12+ features (type unions with `|`, etc.)

## Naming Conventions
- **Classes**: PascalCase (e.g., `HedAnnotationWorkflow`, `ValidationResult`)
- **Functions/methods**: snake_case (e.g., `get_complete_system_prompt`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `HED_SYNTAX_RULES`)
- **Files**: snake_case (e.g., `hed_validator.py`)
- **Private methods**: Leading underscore (e.g., `_build_graph`, `_route_after_validation`)

## Type Hints
- Required for all public functions and methods
- Use modern syntax: `list[str]`, `dict[str, Any]`, `str | None`
- TypedDict for state objects
- Literal types for constrained strings

## Docstrings
- Google style
- Required for classes and public methods
- Include Args, Returns, Raises sections

## Patterns
- **TypedDict** for state management (LangGraph)
- **Dataclasses** for data structures (`ValidationIssue`, `ValidationResult`)
- **Async/await** for API endpoints and LangGraph workflows
- **Context managers** for resource management
- **Pathlib** for file operations
- **F-strings** for formatting
- **Logging** via `logging.getLogger(__name__)`

## Commit Messages
- Format: `<type>: <description>` (<50 chars)
- Types: feat, fix, docs, refactor, test, chore
- No emojis, no co-author mentions
- Atomic commits (one logical change each)

## Testing
- NO MOCKS policy (real data, real API calls)
- Use `OPENROUTER_API_KEY_FOR_TESTING` for integration tests
- Mark integration tests with `@pytest.mark.integration`
- Coverage tracking via codecov

## Pre-commit Hooks
- Ruff check with --fix --unsafe-fixes on staged files only
