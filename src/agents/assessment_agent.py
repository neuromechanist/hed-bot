"""Assessment Agent for final annotation comparison.

This agent performs the final assessment to identify any still-missing
elements or dimensions in the HED annotation.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import HedAnnotationState


class AssessmentAgent:
    """Agent that performs final assessment of HED annotations.

    This agent compares the final annotation against the original description
    to provide annotators with feedback on completeness and missing elements.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize the assessment agent.

        Args:
            llm: Language model for assessment
        """
        self.llm = llm

    def _build_system_prompt(self) -> str:
        """Build the system prompt for assessment.

        Returns:
            System prompt string
        """
        return """You are a HED annotation assessment specialist.

Your task is to provide a final comprehensive assessment comparing the generated HED annotation
against the original event description, identifying any still-missing elements or dimensions.

## Assessment Focus

### 1. Completeness Check
- Are all explicitly mentioned elements captured?
- Are all implicit but important aspects included?
- Is contextual information preserved?

### 2. Dimensional Analysis
Check if these dimensions are captured where relevant:
- Sensory modalities (visual, auditory, tactile, etc.)
- Spatial information (location, position, direction)
- Temporal information (duration, timing, sequence)
- Object properties (color, shape, size, texture)
- Agent information (who, role)
- Action information (what action, how)
- Relationships (spatial, temporal, causal)

### 3. Annotator Guidance
- What was captured well?
- What might still be missing?
- What optional details could enhance the annotation?

## Response Format

Provide assessment in this structure:

COMPLETENESS: [complete/mostly-complete/incomplete]

CAPTURED ELEMENTS:
- [Elements successfully captured]

MISSING ELEMENTS:
- [Elements not captured]

OPTIONAL ENHANCEMENTS:
- [Additional details that could be added]

ANNOTATOR NOTES:
- [Guidance for annotators]

FINAL STATUS: [COMPLETE/NEEDS-REVIEW]
"""

    def _build_user_prompt(self, description: str, annotation: str) -> str:
        """Build the user prompt for assessment.

        Args:
            description: Original natural language description
            annotation: Final HED annotation

        Returns:
            User prompt string
        """
        return f"""Provide final assessment for this annotation:

ORIGINAL DESCRIPTION:
{description}

FINAL HED ANNOTATION:
{annotation}

Provide a comprehensive assessment following the specified format."""

    async def assess(self, state: HedAnnotationState) -> dict:
        """Perform final assessment of the annotation.

        Args:
            state: Current annotation workflow state

        Returns:
            State update with assessment feedback
        """
        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            state["input_description"],
            state["current_annotation"],
        )

        # Generate assessment
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        feedback = response.content.strip()

        # Parse completion status
        is_complete = "FINAL STATUS: COMPLETE" in feedback

        # Update state
        return {
            "assessment_feedback": feedback,
            "is_complete": is_complete,
            "messages": state.get("messages", []) + messages + [response],
        }
