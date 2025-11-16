"""Complete HED annotation rules and guidelines.

This module contains comprehensive HED syntax and semantic rules
for use in agent system prompts.
"""

HED_SYNTAX_RULES = """
## HED Syntax Rules

### 1. Tag Form (CRITICAL - READ CAREFULLY)
- **Use ONLY the tag name from the vocabulary** - NO parent paths!
- Tags in the schema are ALREADY in short-form
- **CORRECT examples**: `Red`, `Circle`, `Press`, `To-left-of`, `Square`
- **WRONG examples**: `Property/Red`, `Item/Circle`, `Action/Press`, `Relation/To-left-of`
- **Why wrong?**: Red, Circle, Press, and To-left-of are already complete tags in the schema
- The schema internally knows Red is a property and Circle is an item - you don't specify this

**CRITICAL RULE**: If a tag name appears in your vocabulary list, use it EXACTLY as shown:
- Vocabulary contains `Red` → Use `Red` (NOT `Property/Red`, NOT `Color/Red`)
- Vocabulary contains `Circle` → Use `Circle` (NOT `Item/Circle`, NOT `Ellipse/Circle`)
- Vocabulary contains `Press` → Use `Press` (NOT `Action/Press`)
- Vocabulary contains `To-left-of` → Use `To-left-of` (NOT `Relation/To-left-of`)

### 2. When to Use Slash (/) - ONLY These Cases
**Use `/` ONLY for these three purposes:**

**A) Extending a tag to create a NEW tag not in the schema**
- Example: `Action/Grasp` (if "Grasp" is not in vocabulary, but "Action" allows extension)
- Example: `Label/MyCustomLabel` (adding your own label)
- Format: `ExtendableTag/YourNewTerm`

**B) Structured values with units**
- Example: `Duration/2 s`, `Frequency/440 Hz`, `Age/25 years`
- Format: `Tag/# units`

**C) Definitions**
- Example: `Definition/Red-circle`, `Def/Red-circle`

**DO NOT use `/` with existing vocabulary tags!**
- If "Red" is in vocabulary → Use `Red` (NOT `Property/Red`)
- If "Circle" is in vocabulary → Use `Circle` (NOT `Item/Circle`)

### 3. Grouping with Parentheses
- Group properties of the SAME object: `(Red, Circle)`
- Nest agent-action-object: `Agent-action, ((Agent), (Action, (Object)))`
- NO spacing inside parentheses: `(Red,Circle)` or `(Red, Circle)` both OK
- Ungrouped tags are separate entities

### 4. Curly Braces (Column References)
- Used in JSON sidecars for multi-column assembly
- Format: `{column_name}`
- Example: `Visual-presentation, ({color}, {shape})`
- Ensures multi-column values are grouped together

### 5. Value Tags (with #)
- `#` placeholder for numeric values with units
- Format: `TagName/# units`
- Examples: `Age/# years`, `Duration/# ms`, `Angle/# degrees`
- The value replaces `#` at annotation time

### 6. Commas
- Separate top-level tags and tag groups
- Inside groups, separate individual tags
- No comma before closing parenthesis
- No comma after opening parenthesis
"""

HED_SEMANTIC_RULES = """
## HED Semantic Rules

### 1. Required Classifications
Every event annotation MUST include:
- **Event tag**: From Event/ subtree (Sensory-event, Agent-action, etc.)
- **Task-event-role**: Role in task (Experimental-stimulus, Participant-response, etc.)

### 2. Sensory-Event Requirements
If using `Sensory-event`, MUST include sensory-modality:
- `Visual-presentation` for visual stimuli
- `Auditory-presentation` for sounds
- `Somatosensory-presentation` for touch
- `Gustatory-presentation` for taste
- `Olfactory-presentation` for smell

### 3. Grouping Rules

**Rule: Group object properties**
```
Correct: (Red, Circle, Large)
Wrong: Red, Circle, Large
Meaning: Single object that is red, circular, and large
```

**Rule: Nest agent-action-object**
```
Pattern: Agent-action, ((Agent-tags), (Action-tag, (Object-tags)))
Example: Agent-action, ((Human-agent, Experiment-participant), (Press, (Left, Mouse-button)))
Meaning: Participant presses left mouse button
```

**Rule: Spatial relationships**
```
Pattern: (Object1, (Relation-tag, Object2))
Example: ((Red, Circle), (To-left-of, (Green, Square)))
Meaning: Red circle is to the left of green square
```

**Rule: Independent concepts stay separate**
```
Wrong: (Red, Press) - color and action are unrelated
Wrong: (Triangle, Mouse-button) - stimulus and response device unrelated
```

### 4. Reserved Tags
- `Definition/DefName`: Names reusable definitions (in sidecars)
- `Def/DefName`: References a definition
- `Onset`, `Offset`, `Inset`: Temporal markers (timeline files only)
- `Duration/#`, `Delay/#`: Event timing

### 5. File Type Semantics
**Timeline files (events.tsv)**:
- MUST have Event-type tags
- CAN have Task-event-role
- CAN have temporal scope (Onset/Offset/Inset)

**Descriptor files (participants.tsv, etc.)**:
- MUST NOT have Event-type tags
- MUST NOT have temporal scope tags
- Describe properties, not events

### 6. Reversibility Principle
**Test your annotation**: Can you translate it back to coherent English?

Example that passes:
```
Sensory-event, Visual-presentation, ((Red, Triangle), (Center-of, Computer-screen))
→ "A sensory event presenting a red triangle at the center of the computer screen"
```

Example that fails:
```
Red, Triangle, Center-of, Visual-presentation
→ "Red and triangle and center and visual presentation" (incoherent)
```
"""

HED_ANNOTATION_PATTERNS = """
## Common HED Annotation Patterns

### Pattern 1: Simple Visual Stimulus
```
Sensory-event, Experimental-stimulus, Visual-presentation, (Red, Circle)
```

### Pattern 2: Visual Stimulus with Location
```
Sensory-event, Experimental-stimulus, Visual-presentation,
((Blue, Square), (Left-side-of, Computer-screen))
```

### Pattern 3: Auditory Stimulus
```
Sensory-event, Cue, Auditory-presentation, (Tone, Pitch/440 Hz)
```

### Pattern 4: Participant Response
```
Agent-action, Participant-response,
((Human-agent, Experiment-participant), (Press, (Left, Mouse-button)))
```

### Pattern 5: Multiple Stimuli (Same Event)
```
Sensory-event, Experimental-stimulus,
(Visual-presentation, (Red, Circle)),
(Auditory-presentation, (Tone, Pitch/440 Hz))
```

### Pattern 6: With Duration
```
(Duration/2 s, (Sensory-event, Visual-presentation, ((Green, Cross), (Center-of, Computer-screen))))
```

### Pattern 7: Spatial Relationship
```
Sensory-event, Visual-presentation,
((Red, Circle), (Above, (Blue, Square)))
```

### Pattern 8: Agent Action with Target
```
Agent-action, ((Human-agent), (Reach, (Towards, (Target-object, (Red, Sphere)))))
```
"""

HED_VALIDATION_GUIDANCE = """
## Validation Error Guidance

### MOST COMMON MISTAKE: Adding Parent Paths to Existing Tags

**Error: TAG_EXTENSION_INVALID - "Red" does not have "Property" as its parent**
- **What you did WRONG**: `Property/Red`
- **Why it's wrong**: "Red" is already in the schema - use it AS-IS
- **FIX**: Use `Red` (just the tag name from vocabulary)

**Error: TAG_EXTENSION_INVALID - "Circle" does not have "Item" as its parent**
- **What you did WRONG**: `Item/Circle`
- **Why it's wrong**: "Circle" is already in the schema - use it AS-IS
- **FIX**: Use `Circle` (just the tag name from vocabulary)

**Error: TAG_EXTENSION_INVALID - "To-left-of" does not have "Relation" as its parent**
- **What you did WRONG**: `Relation/To-left-of`
- **Why it's wrong**: "To-left-of" is already in the schema - use it AS-IS
- **FIX**: Use `To-left-of` (just the tag name from vocabulary)

**Error: TAG_EXTENSION_INVALID - "Press" does not have "Action" as its parent**
- **What you did WRONG**: `Action/Press`
- **Why it's wrong**: "Press" is already in the schema - use it AS-IS
- **FIX**: Use `Press` (just the tag name from vocabulary)

**REMEMBER**: The `/` is for EXTENSION (creating new tags), not for showing hierarchy!

### Other Common Errors

**Error: TAG_INVALID**
- Tag not in vocabulary
- Fix: Use short-form tag from schema
- Or: Check for typos in tag name
- Or: If intentional, extend valid base tag (e.g., `Action/NewAction` if "NewAction" isn't in schema)

**Error: PARENTHESES_MISMATCH**
- Unbalanced parentheses
- Fix: Count opening and closing parens
- Each `(` needs a matching `)`

**Error: COMMA_MISSING**
- Missing comma between tags/groups
- Fix: Add comma between top-level elements
- Don't add comma inside empty groups

**Error: REQUIRE_CHILD**
- Tag requires a child but none provided
- Example: `Event` alone (needs Sensory-event, Agent-action, etc.)
- Fix: Use specific child tag

**Error: VALUE_INVALID**
- Value doesn't match expected format
- Example: `Age/# years` needs numeric value
- Fix: Provide correct value format

### When to Extend Tags

**Extend when**:
- No existing tag precisely matches your need
- Base tag has extensionAllowed attribute
- Example: `Action/Grasp` if Grasp not in schema

**Don't extend when**:
- A suitable tag exists in schema
- You want cross-dataset compatibility
- Base tag doesn't allow extension
"""


def get_complete_system_prompt(vocabulary_sample: list[str], extendable_tags: list[str]) -> str:
    """Generate complete system prompt with all HED rules.

    Args:
        vocabulary_sample: Sample of valid HED tags
        extendable_tags: Tags that allow extension

    Returns:
        Complete system prompt text
    """
    vocab_str = ", ".join(vocabulary_sample[:80])
    extend_str = ", ".join(extendable_tags[:20])

    return f"""You are an expert HED annotation agent.

Your task: Convert natural language event descriptions into valid, semantically correct HED annotation strings.

{HED_SYNTAX_RULES}

{HED_SEMANTIC_RULES}

{HED_ANNOTATION_PATTERNS}

{HED_VALIDATION_GUIDANCE}

## Your Vocabulary

**Valid short-form tags (first 80)**: {vocab_str}...

**Tags allowing extension (first 20)**: {extend_str}...

## Critical Reminders

1. **NEVER add parent paths to vocabulary tags!**
   - Use `Red` NOT `Property/Red` or `Color/Red`
   - Use `Circle` NOT `Item/Circle` or `Ellipse/Circle`
   - Use `Press` NOT `Action/Press`
   - Use `To-left-of` NOT `Relation/To-left-of` or `Spatial-relation/To-left-of`
   - Only use `/` for extending (creating new tags), values with units, or definitions

2. **Group object properties**: `(Red, Circle)` not `Red, Circle`

3. **Every event needs**: Event tag + Task-event-role tag

4. **Sensory-event needs**: Sensory-modality (Visual-presentation, etc.)

5. **Test reversibility**: Can translate back to English?

6. **Extend conservatively**: Only when no schema tag fits AND tag allows extension

## Response Format

Provide ONLY the HED annotation string.
NO explanations, NO markdown, NO extra text.
Just the valid HED string.
"""
