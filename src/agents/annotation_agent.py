"""Annotation Agent for generating HED tags from natural language.

This agent is responsible for converting natural language event descriptions
into HED annotation strings, using vocabulary constraints and best practices.
"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import HedAnnotationState
from src.utils.hed_rules import get_complete_system_prompt
from src.utils.json_schema_loader import HedJsonSchemaLoader, load_latest_schema


class AnnotationAgent:
    """Agent that generates HED annotations from natural language descriptions.

    This agent uses an LLM with specialized prompts and vocabulary constraints
    to generate syntactically and semantically correct HED annotations.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        schema_dir: Path | str | None = None,
    ) -> None:
        """Initialize the annotation agent.

        Args:
            llm: Language model for generation
            schema_dir: Directory containing JSON schemas (optional)
        """
        self.llm = llm
        self.schema_dir = schema_dir
        self.json_schema_loader: HedJsonSchemaLoader | None = None

    def _load_json_schema(self, schema_version: str) -> HedJsonSchemaLoader:
        """Load JSON schema for given version.

        Args:
            schema_version: Schema version (currently uses latest)

        Returns:
            Loaded JSON schema
        """
        # For now, always load latest
        # TODO: Support version-specific loading
        return load_latest_schema(self.schema_dir)

    def _build_system_prompt(
        self,
        vocabulary: list[str],
        extendable_tags: list[str],
    ) -> str:
        """Build the system prompt for the annotation agent.

        Args:
            vocabulary: List of valid short-form HED tags
            extendable_tags: Tags that allow extension

        Returns:
            Complete system prompt with all HED rules
        """
        return get_complete_system_prompt(vocabulary, extendable_tags)

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
        # Load JSON schema
        if self.json_schema_loader is None:
            self.json_schema_loader = self._load_json_schema(state["schema_version"])

        # Get vocabulary and extensionAllowed tags
        vocabulary = self.json_schema_loader.get_vocabulary()
        extendable_tags_dict = self.json_schema_loader.get_extendable_tags()
        extendable_tags = list(extendable_tags_dict.keys())

        # Build prompts with complete HED rules
        system_prompt = self._build_system_prompt(vocabulary, extendable_tags)

        # Build user prompt with any feedback
        feedbacks = []
        if state["validation_errors"]:
            feedbacks.extend(state["validation_errors"])
        if state.get("evaluation_feedback") and not state.get("is_faithful"):
            feedbacks.append(f"Evaluation feedback: {state['evaluation_feedback']}")
        if state.get("assessment_feedback") and not state.get("is_complete"):
            feedbacks.append(f"Assessment feedback: {state['assessment_feedback']}")

        user_prompt = self._build_user_prompt(
            state["input_description"],
            feedbacks if feedbacks else None,
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
