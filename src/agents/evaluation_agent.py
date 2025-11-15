"""Evaluation Agent for assessing annotation faithfulness.

This agent evaluates how faithfully a HED annotation captures
the original natural language event description.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import HedAnnotationState


class EvaluationAgent:
    """Agent that evaluates the faithfulness of HED annotations.

    This agent compares the generated HED annotation against the original
    description to assess completeness, accuracy, and semantic fidelity.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize the evaluation agent.

        Args:
            llm: Language model for evaluation
        """
        self.llm = llm

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
        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            state["input_description"],
            state["current_annotation"],
        )

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
