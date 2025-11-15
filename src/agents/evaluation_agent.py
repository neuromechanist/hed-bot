"""Evaluation Agent for assessing annotation faithfulness.

This agent evaluates how faithfully a HED annotation captures
the original natural language event description.
"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import HedAnnotationState
from src.utils.json_schema_loader import load_latest_schema


class EvaluationAgent:
    """Agent that evaluates the faithfulness of HED annotations.

    This agent compares the generated HED annotation against the original
    description to assess completeness, accuracy, and semantic fidelity.
    Also suggests schema matches for tags that might not exist.
    """

    def __init__(self, llm: BaseChatModel, schema_dir: Path | str | None = None) -> None:
        """Initialize the evaluation agent.

        Args:
            llm: Language model for evaluation
            schema_dir: Directory containing JSON schemas
        """
        self.llm = llm
        self.schema_dir = schema_dir
        self.json_schema_loader = None

    def _build_system_prompt(self) -> str:
        """Build the system prompt for evaluation.

        Returns:
            System prompt string
        """
        return """You are an expert HED annotation evaluator.

Your task is to assess how faithfully a HED annotation captures the original natural language event description.

## Evaluation Criteria

### 1. Completeness
- Are all important aspects of the event captured?
- Are key attributes (colors, shapes, positions, etc.) included?
- Is the event type correctly identified?
- Is the task role properly specified?

### 2. Accuracy
- Do the HED tags correctly represent the described event?
- Are sensory modalities accurate (visual, auditory, etc.)?
- Are spatial relationships correct?
- Are temporal aspects properly captured?

### 3. Semantic Fidelity
- Does the annotation follow the reversibility principle?
- Can the HED annotation be translated back to coherent English?
- Is the grouping semantically correct?
- Are relationships properly expressed?

### 4. Missing Elements
- What important details are missing?
- What dimensions could be added for better description?
- Are there implicit aspects that should be made explicit?

### 5. Tag Validity Check
- Are all tags from the HED schema vocabulary?
- If invalid tags detected, suggest closest schema matches
- Consider if tag extension is needed (extensionAllowed tags)

## Response Format

Provide your evaluation in this structure:

FAITHFUL: [yes/no/partial]

STRENGTHS:
- [What the annotation captures well]

WEAKNESSES:
- [What the annotation misses or misrepresents]

MISSING ELEMENTS:
- [Specific missing aspects]

REFINEMENT SUGGESTIONS:
- [Specific suggestions for improvement]

DECISION: [ACCEPT/REFINE]
"""

    def _build_user_prompt(self, description: str, annotation: str) -> str:
        """Build the user prompt for evaluation.

        Args:
            description: Original natural language description
            annotation: Generated HED annotation

        Returns:
            User prompt string
        """
        return f"""Evaluate this HED annotation:

ORIGINAL DESCRIPTION:
{description}

HED ANNOTATION:
{annotation}

Provide a thorough evaluation following the specified format."""

    async def evaluate(self, state: HedAnnotationState) -> dict:
        """Evaluate the faithfulness of the current annotation.

        Args:
            state: Current annotation workflow state

        Returns:
            State update with evaluation feedback
        """
        # Load schema if needed
        if self.json_schema_loader is None:
            self.json_schema_loader = load_latest_schema(self.schema_dir)

        # Check for potentially invalid tags and suggest matches
        annotation = state["current_annotation"]
        suggestions = self._check_tags_and_suggest(annotation)

        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            state["input_description"],
            annotation,
        )

        # Add tag suggestions if any
        if suggestions:
            user_prompt += f"\n\n**Tag Suggestions**:\n{suggestions}"

        # Generate evaluation
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        feedback = response.content.strip()

        # Parse decision
        is_faithful = "DECISION: ACCEPT" in feedback

        # Update state
        return {
            "evaluation_feedback": feedback,
            "is_faithful": is_faithful,
            "messages": state.get("messages", []) + messages + [response],
        }

    def _check_tags_and_suggest(self, annotation: str) -> str:
        """Check annotation for invalid tags and suggest alternatives.

        Args:
            annotation: HED annotation string

        Returns:
            Suggestion text (empty if all tags valid)
        """
        if not self.json_schema_loader:
            return ""

        # Extract tags from annotation (simple tokenization)
        # Remove parentheses, split by comma
        cleaned = annotation.replace("(", "").replace(")", "")
        tags = [t.strip() for t in cleaned.split(",")]

        vocabulary = set(self.json_schema_loader.get_vocabulary())
        suggestions = []

        for tag in tags:
            # Skip empty, value placeholders, or column references
            if not tag or "#" in tag or "{" in tag:
                continue

            # Check if tag or its base (before /) is in vocabulary
            base_tag = tag.split("/")[0]
            if base_tag not in vocabulary:
                # Find closest matches
                matches = self.json_schema_loader.find_closest_match(base_tag)
                if matches:
                    suggestions.append(
                        f"- '{base_tag}' not in schema. Did you mean: {', '.join(matches)}?"
                    )
                else:
                    # Check if it's a valid extension
                    if "/" in tag:
                        if self.json_schema_loader.is_extendable(base_tag):
                            suggestions.append(
                                f"- '{tag}' uses extension (dataset-specific, non-portable)"
                            )
                        else:
                            suggestions.append(
                                f"- '{base_tag}' doesn't allow extension. Use schema tag instead."
                            )

        return "\n".join(suggestions) if suggestions else ""
