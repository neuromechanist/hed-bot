"""Annotation Agent for generating HED tags from natural language.

This agent is responsible for converting natural language event descriptions
into HED annotation strings, using vocabulary constraints and best practices.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import HedAnnotationState
from src.utils.schema_loader import HedSchemaLoader


class AnnotationAgent:
    """Agent that generates HED annotations from natural language descriptions.

    This agent uses an LLM with specialized prompts and vocabulary constraints
    to generate syntactically and semantically correct HED annotations.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        schema_loader: HedSchemaLoader,
    ) -> None:
        """Initialize the annotation agent.

        Args:
            llm: Language model for generation
            schema_loader: HED schema loader for vocabulary
        """
        self.llm = llm
        self.schema_loader = schema_loader

    def _build_system_prompt(self, schema_version: str, vocabulary: list[str]) -> str:
        """Build the system prompt for the annotation agent.

        Args:
            schema_version: HED schema version
            vocabulary: List of valid HED tags

        Returns:
            System prompt string
        """
        vocab_sample = ", ".join(vocabulary[:100])  # Show first 100 tags
        vocab_note = f"... and {len(vocabulary) - 100} more tags" if len(vocabulary) > 100 else ""

        return f"""You are an expert HED (Hierarchical Event Descriptors) annotation agent using schema version {schema_version}.

Your task is to convert natural language event descriptions into valid HED annotation strings.

## CRITICAL RULES

### 1. Vocabulary Constraints
You MUST use ONLY tags from the HED {schema_version} vocabulary. Do not invent or hallucinate tags.
Available tags include: {vocab_sample}{vocab_note}

### 2. Required Classifications
Every event annotation MUST include:
- An Event tag (Sensory-event, Agent-action, Data-feature, etc.)
- A Task-event-role tag (Experimental-stimulus, Cue, Participant-response, etc.)

### 3. Semantic Grouping Rules
- Group object properties together: `(Red, Circle)` not `Red, Circle`
- Nest agent-action-object: `Agent-action, ((Human-agent), (Press, (Mouse-button)))`
- Use curly braces for column references: `{{column_name}}`
- Keep independent concepts separate
- Use directional pattern for relationships: `(A, (Relation-tag, B))`

### 4. Sensory Events
Every `Sensory-event` MUST have a sensory-modality tag like:
- Visual-presentation
- Auditory-presentation
- Somatosensory-presentation

### 5. Reversibility Principle
Your annotation should be translatable back into coherent English.
Example: `Sensory-event, Visual-presentation, (Red, Circle)` = "A sensory event is a visual presentation of a red circle"

### 6. Common Patterns

Simple sensory stimulus:
```
Sensory-event, Experimental-stimulus, Visual-presentation, (Red, Circle)
```

Agent action:
```
Agent-action, Participant-response, ((Human-agent, Experiment-participant), (Press, (Left, Mouse-button)))
```

Stimulus with location:
```
Sensory-event, Experimental-stimulus, Visual-presentation, ((Green, Square), (Center-of, Computer-screen))
```

### 7. Validation Feedback
If you receive validation errors, carefully read them and fix the issues.
Common fixes:
- Invalid tag → Use correct tag from vocabulary
- Missing parentheses → Add proper grouping
- Wrong syntax → Follow HED format rules

## Response Format
Provide ONLY the HED annotation string, nothing else. No explanations, no markdown formatting.
"""

    def _build_user_prompt(
        self,
        description: str,
        validation_errors: list[str] | None = None,
    ) -> str:
        """Build the user prompt for annotation.

        Args:
            description: Natural language event description
            validation_errors: Previous validation errors (if retrying)

        Returns:
            User prompt string
        """
        if validation_errors:
            errors_str = "\n".join(f"- {error}" for error in validation_errors)
            return f"""Previous annotation had validation errors:
{errors_str}

Please fix these errors and generate a corrected HED annotation for:
{description}

Remember to use only valid HED tags and follow proper grouping rules.
Provide ONLY the corrected HED annotation string."""

        return f"""Generate a HED annotation for this event description:
{description}

Provide ONLY the HED annotation string."""

    async def annotate(self, state: HedAnnotationState) -> dict:
        """Generate or refine a HED annotation.

        Args:
            state: Current annotation workflow state

        Returns:
            State update with new annotation
        """
        # Load schema and vocabulary
        schema = self.schema_loader.load_schema(state["schema_version"])
        vocabulary = self.schema_loader.get_schema_vocabulary(schema)

        # Build prompts
        system_prompt = self._build_system_prompt(state["schema_version"], vocabulary)
        user_prompt = self._build_user_prompt(
            state["input_description"],
            state["validation_errors"] if state["validation_attempts"] > 0 else None,
        )

        # Generate annotation
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        annotation = response.content.strip()

        # Update state
        return {
            "current_annotation": annotation,
            "messages": messages + [response],
        }
