# HED Language Server Protocol (LSP) Integration

## Overview
The HED LSP provides semantic search capabilities for finding valid HED tags from natural language descriptions. It is used by the OSA project's `suggest_hed_tags` tool and should be integrated into HEDit for better tag discovery.

## HED LSP Repository
- Location: `~/Documents/git/HED/hed-lsp/`
- CLI tool: `server/out/cli.js`
- Also installable as `hed-suggest` global CLI

## How It Works
1. Takes natural language search terms (e.g., "button press", "visual flash")
2. Performs semantic search against the HED schema vocabulary
3. Returns ranked list of matching HED tags per search term

## CLI Usage
```bash
# Using global install
hed-suggest --json --top 10 "button press" "visual flash"

# Using local dev path
node ~/Documents/git/HED/hed-lsp/server/out/cli.js --json --top 10 "button press"
```

## Output Format
```json
{
  "button press": ["Press", "Button", "Response-button", "Mouse-button"],
  "visual flash": ["Flash", "Flickering", "Visual-presentation"]
}
```

## Discovery Order (from OSA implementation)
1. Check PATH for `hed-suggest` CLI (global install)
2. Check `HED_LSP_PATH` environment variable
3. Check common dev path: `~/Documents/git/HED/hed-lsp/server/out/cli.js`
4. Graceful degradation: returns empty results if unavailable

## Integration Strategy for HEDit
The annotation agent could use HED LSP to:
1. Convert natural language concepts to valid HED tag candidates
2. Validate tag choices against schema before annotation
3. Provide tag suggestions in the CLI and API responses

This is similar to how OSA's `suggest_hed_tags` tool works (see `osa/src/assistants/hed/tools.py`).

## Key Advantage
Instead of relying solely on the LLM's knowledge of HED tags (which can hallucinate), the LSP provides ground-truth tag lookup from the actual schema, reducing invalid tag usage.
