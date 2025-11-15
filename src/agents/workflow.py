"""LangGraph workflow for HED annotation generation.

This module defines the multi-agent workflow that orchestrates
annotation, validation, evaluation, and assessment.
"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from src.agents.annotation_agent import AnnotationAgent
from src.agents.assessment_agent import AssessmentAgent
from src.agents.evaluation_agent import EvaluationAgent
from src.agents.state import HedAnnotationState
from src.agents.validation_agent import ValidationAgent
from src.utils.schema_loader import HedSchemaLoader


class HedAnnotationWorkflow:
    """Multi-agent workflow for HED annotation generation and validation.

    The workflow follows this pattern:
    1. Annotation: Generate HED tags from natural language
    2. Validation: Check HED compliance
    3. If errors and attempts < max: Return to annotation with feedback
    4. If valid: Proceed to evaluation
    5. Evaluation: Assess faithfulness to original description
    6. If needs refinement: Return to annotation
    7. If faithful: Proceed to assessment
    8. Assessment: Final comparison for completeness
    9. End: Return final annotation with feedback
    """

    def __init__(
        self,
        llm: BaseChatModel,
        schema_loader: HedSchemaLoader | None = None,
        validator_path: Path | None = None,
        use_js_validator: bool = True,
    ) -> None:
        """Initialize the workflow.

        Args:
            llm: Language model for agents
            schema_loader: HED schema loader (creates default if None)
            validator_path: Path to hed-javascript for validation
            use_js_validator: Whether to use JavaScript validator
        """
        # Initialize schema loader
        self.schema_loader = schema_loader or HedSchemaLoader()

        # Initialize agents
        self.annotation_agent = AnnotationAgent(llm, self.schema_loader)
        self.validation_agent = ValidationAgent(
            self.schema_loader,
            use_javascript=use_js_validator,
            validator_path=validator_path,
        )
        self.evaluation_agent = EvaluationAgent(llm)
        self.assessment_agent = AssessmentAgent(llm)

        # Build graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Compiled StateGraph
        """
        # Create graph
        workflow = StateGraph(HedAnnotationState)

        # Add nodes
        workflow.add_node("annotate", self._annotate_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("evaluate", self._evaluate_node)
        workflow.add_node("assess", self._assess_node)

        # Add edges
        workflow.set_entry_point("annotate")

        # After annotation, always validate
        workflow.add_edge("annotate", "validate")

        # After validation, route based on result
        workflow.add_conditional_edges(
            "validate",
            self._route_after_validation,
            {
                "annotate": "annotate",  # Retry if invalid and attempts remain
                "evaluate": "evaluate",  # Proceed if valid
                "end": END,  # End if max attempts reached
            },
        )

        # After evaluation, route based on faithfulness
        workflow.add_conditional_edges(
            "evaluate",
            self._route_after_evaluation,
            {
                "annotate": "annotate",  # Refine if not faithful
                "assess": "assess",  # Proceed to assessment if faithful
            },
        )

        # After assessment, always end
        workflow.add_edge("assess", END)

        return workflow.compile()

    async def _annotate_node(self, state: HedAnnotationState) -> dict:
        """Annotation node: Generate or refine HED annotation.

        Args:
            state: Current workflow state

        Returns:
            State update
        """
        return await self.annotation_agent.annotate(state)

    async def _validate_node(self, state: HedAnnotationState) -> dict:
        """Validation node: Validate HED annotation.

        Args:
            state: Current workflow state

        Returns:
            State update
        """
        return await self.validation_agent.validate(state)

    async def _evaluate_node(self, state: HedAnnotationState) -> dict:
        """Evaluation node: Evaluate annotation faithfulness.

        Args:
            state: Current workflow state

        Returns:
            State update
        """
        return await self.evaluation_agent.evaluate(state)

    async def _assess_node(self, state: HedAnnotationState) -> dict:
        """Assessment node: Final assessment.

        Args:
            state: Current workflow state

        Returns:
            State update
        """
        return await self.assessment_agent.assess(state)

    def _route_after_validation(
        self,
        state: HedAnnotationState,
    ) -> str:
        """Route after validation based on result.

        Args:
            state: Current workflow state

        Returns:
            Next node name
        """
        if state["validation_status"] == "valid":
            return "evaluate"
        elif state["validation_status"] == "max_attempts_reached":
            return "end"
        else:
            return "annotate"

    def _route_after_evaluation(
        self,
        state: HedAnnotationState,
    ) -> str:
        """Route after evaluation based on faithfulness.

        Args:
            state: Current workflow state

        Returns:
            Next node name
        """
        if state["is_faithful"]:
            return "assess"
        else:
            return "annotate"

    async def run(
        self,
        input_description: str,
        schema_version: str = "8.3.0",
        max_validation_attempts: int = 5,
    ) -> HedAnnotationState:
        """Run the complete annotation workflow.

        Args:
            input_description: Natural language event description
            schema_version: HED schema version to use
            max_validation_attempts: Maximum validation retry attempts

        Returns:
            Final workflow state with annotation and feedback
        """
        from src.agents.state import create_initial_state

        # Create initial state
        initial_state = create_initial_state(
            input_description,
            schema_version,
            max_validation_attempts,
        )

        # Run workflow
        final_state = await self.graph.ainvoke(initial_state)

        return final_state
