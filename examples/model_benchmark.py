#!/usr/bin/env python3
"""Model benchmark for HED annotation quality comparison.

This script compares multiple LLM models on HED annotation tasks across
different domains, using a reconstruction-based evaluation methodology.

Related GitHub Issues:
- #64: Explore alternative candidates for the default model
- #69: Revisit Agent Prompts (semantic grouping issues)

Methodology:
1. Generate HED annotation from natural language description
2. Reconstruct natural language from HED annotation
3. Compare reconstruction to original (semantic similarity)
4. Measure validation success rate and iteration count

Test Domains (avoiding examples in prompt):
1. Standard cognitive experiments (different stimuli than prompt examples)
2. Animal experiments (monkey/rat reaching, navigation, reward)
3. Image annotations (NSD dataset images)
4. Optional paradigms (oddball, face processing, reaching)
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.agents.vision_agent import VisionAgent  # noqa: E402
from src.agents.workflow import HedAnnotationWorkflow  # noqa: E402
from src.utils.openrouter_llm import create_openrouter_llm  # noqa: E402

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SCHEMA_VERSION = "8.4.0"
MAX_VALIDATION_ATTEMPTS = 5

# Models to benchmark
# Ordered by expected cost (lowest to highest)
MODELS_TO_BENCHMARK = [
    # Current default (Cerebras - ultra fast, cheap)
    {
        "id": "openai/gpt-oss-120b",
        "name": "GPT-OSS-120B",
        "provider": "Cerebras",
        "category": "fast",
    },
    # Qwen large (Cerebras - fast)
    {
        "id": "qwen/qwen3-235b-a22b-2507",
        "name": "Qwen3-235B",
        "provider": "Cerebras",
        "category": "fast",
    },
    # Claude Haiku (cheap, cacheable)
    {
        "id": "anthropic/claude-3.5-haiku",
        "name": "Claude Haiku 3.5",
        "provider": None,  # OpenRouter auto-routes
        "category": "balanced",
    },
    # GPT-4o-mini (OpenAI's cheap option)
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o-mini",
        "provider": None,
        "category": "balanced",
    },
    # Claude Sonnet (high quality, cacheable)
    {
        "id": "anthropic/claude-sonnet-4",
        "name": "Claude Sonnet 4",
        "provider": None,
        "category": "quality",
    },
]

# Vision model for image descriptions
VISION_MODEL = "qwen/qwen3-vl-30b-a3b-instruct"


# ============================================================================
# TEST CASES
# ============================================================================
# IMPORTANT: These are intentionally DIFFERENT from examples in the prompts
# to avoid "cheating" where models just pattern-match from training.


@dataclass
class TestCase:
    """A single test case for benchmarking."""

    id: str
    domain: str
    description: str
    expected_elements: list[str]  # Key elements that should appear in annotation
    difficulty: str  # easy, medium, hard
    notes: str = ""


# Domain 1: Standard Cognitive Experiments
# (Different from prompt examples: no red circles, blue squares, etc.)
COGNITIVE_TESTS = [
    TestCase(
        id="cog_01",
        domain="cognitive",
        description="An orange star flashes briefly at the top of the display",
        expected_elements=["Sensory-event", "Visual-presentation", "Orange", "Star", "Top"],
        difficulty="easy",
        notes="Simple visual event with color, shape, location",
    ),
    TestCase(
        id="cog_02",
        domain="cognitive",
        description="A low-frequency buzzer sounds for 500 milliseconds followed by a high-frequency beep",
        expected_elements=["Sensory-event", "Auditory-presentation", "Duration", "Frequency"],
        difficulty="medium",
        notes="Auditory sequence with temporal and frequency information",
    ),
    TestCase(
        id="cog_03",
        domain="cognitive",
        description="The participant fixates on a central cross while a peripheral distractor appears in the lower right quadrant",
        expected_elements=[
            "Sensory-event",
            "Visual-presentation",
            "Fixation",
            "Cross",
            "Distractor",
        ],
        difficulty="medium",
        notes="Fixation task with spatial relationships",
    ),
    TestCase(
        id="cog_04",
        domain="cognitive",
        description="A white noise burst masks the target word which was spoken by a female voice",
        expected_elements=["Auditory-presentation", "Noise", "Speech", "Female"],
        difficulty="hard",
        notes="Auditory masking paradigm with voice characteristics",
    ),
    TestCase(
        id="cog_05",
        domain="cognitive",
        description="The go signal consists of a green diamond appearing centrally, prompting a bimanual key press",
        expected_elements=[
            "Agent-action",
            "Visual-presentation",
            "Green",
            "Press",
            "Participant-response",
        ],
        difficulty="hard",
        notes="Go/No-Go task with motor response",
    ),
]

# Domain 2: Animal Experiments
# (Monkey, rat, VR navigation, reaching, reward paradigms)
ANIMAL_TESTS = [
    TestCase(
        id="animal_01",
        domain="animal",
        description="A macaque monkey reaches toward a target on a touchscreen and receives a juice reward",
        expected_elements=["Agent-action", "Animal-agent", "Reach", "Target", "Reward"],
        difficulty="medium",
        notes="Primate reaching task with reward",
    ),
    TestCase(
        id="animal_02",
        domain="animal",
        description="The rat navigates through a virtual reality T-maze and turns left at the choice point",
        expected_elements=["Agent-action", "Animal-agent", "Navigate", "Left"],
        difficulty="medium",
        notes="Rodent VR navigation",
    ),
    TestCase(
        id="animal_03",
        domain="animal",
        description="A rhesus monkey successfully grasps a pellet with a precision grip using thumb and index finger",
        expected_elements=["Agent-action", "Animal-agent", "Grasp"],
        difficulty="hard",
        notes="Fine motor control in primates",
    ),
    TestCase(
        id="animal_04",
        domain="animal",
        description="The mouse receives an air puff to the whiskers as an aversive stimulus after incorrect lever press",
        expected_elements=["Sensory-event", "Animal-agent", "Incorrect-action", "Aversive"],
        difficulty="hard",
        notes="Aversive conditioning paradigm",
    ),
    TestCase(
        id="animal_05",
        domain="animal",
        description="A marmoset vocalizes in response to a playback of a conspecific phee call",
        expected_elements=["Agent-action", "Animal-agent", "Vocalize", "Auditory-presentation"],
        difficulty="hard",
        notes="Vocal communication in primates",
    ),
]

# Domain 3: Optional Paradigms (Oddball, Face Processing, Reaching)
PARADIGM_TESTS = [
    TestCase(
        id="para_01",
        domain="paradigm",
        description="A rare deviant tone at 1200 Hz interrupts a sequence of standard 800 Hz tones",
        expected_elements=["Auditory-presentation", "Frequency", "Oddball"],
        difficulty="medium",
        notes="Auditory oddball paradigm",
    ),
    TestCase(
        id="para_02",
        domain="paradigm",
        description="An upright neutral face is presented for 200ms followed by a scrambled face mask",
        expected_elements=["Sensory-event", "Visual-presentation", "Face", "Duration"],
        difficulty="medium",
        notes="Face processing with masking",
    ),
    TestCase(
        id="para_03",
        domain="paradigm",
        description="The participant reaches to grasp a cylinder placed 30 centimeters in front of them",
        expected_elements=["Agent-action", "Reach", "Grasp", "Distance", "Participant-response"],
        difficulty="medium",
        notes="Reaching and grasping task",
    ),
    TestCase(
        id="para_04",
        domain="paradigm",
        description="A fearful facial expression appears in the left visual field while a happy face appears on the right",
        expected_elements=[
            "Sensory-event",
            "Visual-presentation",
            "Face",
            "Emotion",
            "Left",
            "Right",
        ],
        difficulty="hard",
        notes="Emotional face lateralization",
    ),
    TestCase(
        id="para_05",
        domain="paradigm",
        description="Target letters T and L embedded among distractor letters O are searched in a visual array",
        expected_elements=[
            "Sensory-event",
            "Visual-presentation",
            "Target",
            "Distractor",
            "Search",
        ],
        difficulty="hard",
        notes="Visual search paradigm",
    ),
]


# Domain 4: Image Annotations (using NSD images)
# Images are dynamically discovered from examples/images/ directory
# Selection methodology: 20 images randomly sampled from NSD shared1000 dataset
# using seed=42 for reproducibility. See README in images/ for details.
def _discover_image_tests() -> list[TestCase]:
    """Dynamically discover image test cases from examples/images/ directory.

    Returns:
        List of TestCase objects for each image found
    """
    images_dir = Path(__file__).parent / "images"
    if not images_dir.exists():
        return []

    image_tests = []
    image_files = sorted(
        list(images_dir.glob("*.jpg"))
        + list(images_dir.glob("*.jpeg"))
        + list(images_dir.glob("*.png"))
    )

    for i, img_path in enumerate(image_files, 1):
        image_tests.append(
            TestCase(
                id=f"img_{i:02d}",
                domain="image",
                description=f"[VLM_DESCRIBE:{img_path.name}]",
                expected_elements=["Sensory-event", "Visual-presentation"],
                difficulty="hard",
                notes=f"NSD image: {img_path.stem}",
            )
        )

    return image_tests


IMAGE_TESTS = _discover_image_tests()

ALL_TEST_CASES = COGNITIVE_TESTS + ANIMAL_TESTS + PARADIGM_TESTS + IMAGE_TESTS


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""

    test_id: str
    model_id: str
    model_name: str
    domain: str
    input_description: str
    annotation: str
    is_valid: bool
    is_faithful: bool
    validation_attempts: int
    validation_errors: list[str]
    evaluation_feedback: str
    execution_time_seconds: float
    reconstruction: str | None  # Natural language reconstruction from HED
    reconstruction_similarity: float | None  # Semantic similarity score
    error: str | None = None


class ReconstructionEvaluator:
    """Evaluates HED annotations by reconstructing natural language."""

    def __init__(self, llm):
        self.llm = llm

    async def reconstruct(self, hed_annotation: str) -> str:
        """Reconstruct natural language from HED annotation.

        Args:
            hed_annotation: The HED annotation string

        Returns:
            Natural language description
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = """You are an expert at reading HED (Hierarchical Event Descriptors) annotations.

Given a HED annotation, reconstruct a natural language description of the event.
The description should:
1. Be a single, clear sentence
2. Include all key elements from the annotation
3. Be written as if describing what happened in an experiment

Output ONLY the natural language description, nothing else."""

        user_prompt = f"""Reconstruct a natural language description from this HED annotation:

{hed_annotation}

Natural language description:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    async def compute_similarity(self, original: str, reconstruction: str) -> float:
        """Compute semantic similarity between original and reconstruction.

        Args:
            original: Original natural language description
            reconstruction: Reconstructed description from HED

        Returns:
            Similarity score 0-1
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = """You are an expert at evaluating semantic similarity.

Compare two event descriptions and rate their semantic similarity.
Consider:
1. Core event type (stimulus, response, action)
2. Main objects and entities mentioned
3. Key attributes (color, shape, location, timing)
4. Relationships between elements

Rate on a scale from 0.0 to 1.0:
- 1.0: Semantically equivalent (same meaning)
- 0.8-0.9: Very similar (minor details differ)
- 0.6-0.7: Similar (same core event, some details differ)
- 0.4-0.5: Partially similar (related but missing key elements)
- 0.2-0.3: Weakly similar (only basic overlap)
- 0.0-0.1: Not similar (different events)

Output ONLY a number between 0.0 and 1.0."""

        user_prompt = f"""Compare these two event descriptions:

ORIGINAL:
{original}

RECONSTRUCTED:
{reconstruction}

Similarity score (0.0-1.0):"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        try:
            score = float(response.content.strip())
            return max(0.0, min(1.0, score))
        except ValueError:
            # Try to extract a number from the response
            import re

            match = re.search(r"(\d+\.?\d*)", response.content)
            if match:
                return max(0.0, min(1.0, float(match.group(1))))
            return 0.5  # Default if parsing fails


class ModelBenchmark:
    """Benchmark runner for comparing HED annotation models."""

    def __init__(
        self,
        api_key: str,
        schema_dir: Path,
        output_dir: Path | None = None,
    ):
        self.api_key = api_key
        self.schema_dir = schema_dir
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(exist_ok=True)
        self.results: list[BenchmarkResult] = []

        # Create evaluator LLM (use a reliable model)
        self.evaluator_llm = create_openrouter_llm(
            model="anthropic/claude-3.5-haiku",
            api_key=api_key,
            temperature=0.1,
        )
        self.reconstruction_evaluator = ReconstructionEvaluator(self.evaluator_llm)

        # Vision agent for image descriptions
        self.vision_agent = None

    async def _get_image_description(self, image_path: str) -> str:
        """Get description of an image using VLM.

        Args:
            image_path: Path to image file (relative to examples/)

        Returns:
            Natural language description of the image
        """
        if self.vision_agent is None:
            vision_llm = create_openrouter_llm(
                model=VISION_MODEL,
                api_key=self.api_key,
                temperature=0.1,
                provider="Cerebras",
            )
            self.vision_agent = VisionAgent(llm=vision_llm)

        # Construct full path (images are in examples/images/)
        images_dir = Path(__file__).parent / "images"
        full_path = images_dir / image_path

        if not full_path.exists():
            return f"[Image not found: {image_path}]"

        # Read and encode image
        import base64

        with open(full_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # Create data URI
        suffix = full_path.suffix.lower()
        mime_type = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"
        data_uri = f"data:{mime_type};base64,{image_data}"

        # Get description
        result = await self.vision_agent.describe_image(
            image_data=data_uri,
            prompt="Describe what you see in this image as if it were an experimental stimulus. "
            "Focus on: main objects, their colors, positions, actions, and any notable features. "
            "Be specific and objective. Maximum 100 words.",
        )

        return result.get("description", "[Failed to describe image]")

    async def _process_test_description(self, test_case: TestCase) -> str:
        """Process test description, handling VLM placeholders.

        Args:
            test_case: The test case

        Returns:
            Processed description string
        """
        description = test_case.description

        # Check for VLM placeholder
        if description.startswith("[VLM_DESCRIBE:"):
            # Extract image path
            image_path = description[14:-1]  # Remove [VLM_DESCRIBE: and ]
            description = await self._get_image_description(image_path)
            print(f"    VLM description: {description[:100]}...")

        return description

    async def benchmark_model(
        self,
        model_config: dict,
        test_cases: list[TestCase],
    ) -> list[BenchmarkResult]:
        """Run benchmark for a single model.

        Args:
            model_config: Model configuration dict
            test_cases: List of test cases to run

        Returns:
            List of benchmark results
        """
        model_id = model_config["id"]
        model_name = model_config["name"]
        provider = model_config.get("provider")

        print(f"\n{'=' * 80}")
        print(f"Benchmarking: {model_name} ({model_id})")
        print(f"{'=' * 80}")

        results = []

        # Create LLM for this model
        annotation_llm = create_openrouter_llm(
            model=model_id,
            api_key=self.api_key,
            temperature=0.1,
            provider=provider,
        )

        # Create workflow
        workflow = HedAnnotationWorkflow(
            llm=annotation_llm,
            evaluation_llm=self.evaluator_llm,  # Use consistent evaluator
            assessment_llm=annotation_llm,
            feedback_llm=annotation_llm,
            schema_dir=self.schema_dir,
            validator_path=None,
            use_js_validator=False,
        )

        for test_case in test_cases:
            print(f"\n  Test: {test_case.id} ({test_case.domain})")
            print(f"    Difficulty: {test_case.difficulty}")

            try:
                # Process description (handle VLM placeholders)
                description = await self._process_test_description(test_case)
                print(f"    Description: {description[:80]}...")

                # Run annotation
                start_time = time.time()
                result = await workflow.run(
                    input_description=description,
                    schema_version=SCHEMA_VERSION,
                    max_validation_attempts=MAX_VALIDATION_ATTEMPTS,
                    run_assessment=False,
                )
                execution_time = time.time() - start_time

                annotation = result["current_annotation"]
                print(f"    Annotation: {annotation[:80]}...")
                print(f"    Valid: {result['is_valid']}, Faithful: {result['is_faithful']}")
                print(f"    Attempts: {result['validation_attempts']}, Time: {execution_time:.2f}s")

                # Reconstruction evaluation
                reconstruction = None
                similarity = None
                if result["is_valid"]:
                    try:
                        reconstruction = await self.reconstruction_evaluator.reconstruct(annotation)
                        similarity = await self.reconstruction_evaluator.compute_similarity(
                            description, reconstruction
                        )
                        print(f"    Reconstruction: {reconstruction[:80]}...")
                        print(f"    Similarity: {similarity:.2f}")
                    except Exception as e:
                        print(f"    Reconstruction failed: {e}")

                results.append(
                    BenchmarkResult(
                        test_id=test_case.id,
                        model_id=model_id,
                        model_name=model_name,
                        domain=test_case.domain,
                        input_description=description,
                        annotation=annotation,
                        is_valid=result["is_valid"],
                        is_faithful=result["is_faithful"],
                        validation_attempts=result["validation_attempts"],
                        validation_errors=result.get("validation_errors", []),
                        evaluation_feedback=result.get("evaluation_feedback", ""),
                        execution_time_seconds=execution_time,
                        reconstruction=reconstruction,
                        reconstruction_similarity=similarity,
                    )
                )

            except Exception as e:
                print(f"    ERROR: {e}")
                import traceback

                traceback.print_exc()

                results.append(
                    BenchmarkResult(
                        test_id=test_case.id,
                        model_id=model_id,
                        model_name=model_name,
                        domain=test_case.domain,
                        input_description=test_case.description,
                        annotation="",
                        is_valid=False,
                        is_faithful=False,
                        validation_attempts=0,
                        validation_errors=[],
                        evaluation_feedback="",
                        execution_time_seconds=0,
                        reconstruction=None,
                        reconstruction_similarity=None,
                        error=str(e),
                    )
                )

        return results

    async def run_full_benchmark(
        self,
        models: list[dict] | None = None,
        test_cases: list[TestCase] | None = None,
        domains: list[str] | None = None,
    ):
        """Run full benchmark across all models and test cases.

        Args:
            models: List of model configs (defaults to MODELS_TO_BENCHMARK)
            test_cases: List of test cases (defaults to ALL_TEST_CASES)
            domains: Filter to specific domains (e.g., ["cognitive", "animal"])
        """
        models = models or MODELS_TO_BENCHMARK
        test_cases = test_cases or ALL_TEST_CASES

        # Filter by domain if specified
        if domains:
            test_cases = [tc for tc in test_cases if tc.domain in domains]

        print(f"\n{'#' * 80}")
        print("# HED MODEL BENCHMARK")
        print(f"# Date: {datetime.now().isoformat()}")
        print(f"# Models: {len(models)}")
        print(f"# Test Cases: {len(test_cases)}")
        print(f"# Domains: { {tc.domain for tc in test_cases} }")
        print(f"{'#' * 80}")

        for model_config in models:
            model_results = await self.benchmark_model(model_config, test_cases)
            self.results.extend(model_results)

        # Save results
        self._save_results()

        # Generate report
        self._generate_report()

    def _save_results(self):
        """Save benchmark results to JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"benchmark_{timestamp}.json"

        results_data = []
        for r in self.results:
            results_data.append(
                {
                    "test_id": r.test_id,
                    "model_id": r.model_id,
                    "model_name": r.model_name,
                    "domain": r.domain,
                    "input_description": r.input_description,
                    "annotation": r.annotation,
                    "is_valid": r.is_valid,
                    "is_faithful": r.is_faithful,
                    "validation_attempts": r.validation_attempts,
                    "validation_errors": r.validation_errors,
                    "evaluation_feedback": r.evaluation_feedback,
                    "execution_time_seconds": r.execution_time_seconds,
                    "reconstruction": r.reconstruction,
                    "reconstruction_similarity": r.reconstruction_similarity,
                    "error": r.error,
                }
            )

        with open(output_file, "w") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "schema_version": SCHEMA_VERSION,
                    "results": results_data,
                },
                f,
                indent=2,
            )

        print(f"\nResults saved to: {output_file}")

    def _generate_report(self):
        """Generate summary report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"report_{timestamp}.md"

        # Aggregate statistics by model
        model_stats = {}
        for r in self.results:
            if r.model_name not in model_stats:
                model_stats[r.model_name] = {
                    "model_id": r.model_id,
                    "total": 0,
                    "valid": 0,
                    "faithful": 0,
                    "total_attempts": 0,
                    "total_time": 0.0,
                    "similarities": [],
                    "errors": 0,
                    "by_domain": {},
                }

            stats = model_stats[r.model_name]
            stats["total"] += 1
            stats["valid"] += 1 if r.is_valid else 0
            stats["faithful"] += 1 if r.is_faithful else 0
            stats["total_attempts"] += r.validation_attempts
            stats["total_time"] += r.execution_time_seconds
            if r.reconstruction_similarity is not None:
                stats["similarities"].append(r.reconstruction_similarity)
            if r.error:
                stats["errors"] += 1

            # Domain stats
            if r.domain not in stats["by_domain"]:
                stats["by_domain"][r.domain] = {
                    "total": 0,
                    "valid": 0,
                    "faithful": 0,
                    "similarities": [],
                }
            domain_stats = stats["by_domain"][r.domain]
            domain_stats["total"] += 1
            domain_stats["valid"] += 1 if r.is_valid else 0
            domain_stats["faithful"] += 1 if r.is_faithful else 0
            if r.reconstruction_similarity is not None:
                domain_stats["similarities"].append(r.reconstruction_similarity)

        # Generate markdown report
        report_lines = [
            "# HED Model Benchmark Report",
            "",
            f"**Date**: {datetime.now().isoformat()}",
            f"**Schema Version**: {SCHEMA_VERSION}",
            f"**Total Tests**: {len(self.results)}",
            "",
            "## Summary",
            "",
            "| Model | Valid Rate | Faithful Rate | Avg Similarity | Avg Attempts | Avg Time | Errors |",
            "|-------|------------|---------------|----------------|--------------|----------|--------|",
        ]

        for model_name, stats in model_stats.items():
            valid_rate = stats["valid"] / stats["total"] * 100 if stats["total"] > 0 else 0
            faithful_rate = stats["faithful"] / stats["total"] * 100 if stats["total"] > 0 else 0
            avg_sim = (
                sum(stats["similarities"]) / len(stats["similarities"])
                if stats["similarities"]
                else 0
            )
            avg_attempts = stats["total_attempts"] / stats["total"] if stats["total"] > 0 else 0
            avg_time = stats["total_time"] / stats["total"] if stats["total"] > 0 else 0

            report_lines.append(
                f"| {model_name} | {valid_rate:.1f}% | {faithful_rate:.1f}% | "
                f"{avg_sim:.2f} | {avg_attempts:.1f} | {avg_time:.1f}s | {stats['errors']} |"
            )

        report_lines.extend(
            [
                "",
                "## By Domain",
                "",
            ]
        )

        domains = {r.domain for r in self.results}
        for domain in sorted(domains):
            report_lines.extend(
                [
                    f"### {domain.title()}",
                    "",
                    "| Model | Valid Rate | Faithful Rate | Avg Similarity |",
                    "|-------|------------|---------------|----------------|",
                ]
            )

            for model_name, stats in model_stats.items():
                if domain in stats["by_domain"]:
                    d = stats["by_domain"][domain]
                    valid_rate = d["valid"] / d["total"] * 100 if d["total"] > 0 else 0
                    faithful_rate = d["faithful"] / d["total"] * 100 if d["total"] > 0 else 0
                    avg_sim = (
                        sum(d["similarities"]) / len(d["similarities"]) if d["similarities"] else 0
                    )
                    report_lines.append(
                        f"| {model_name} | {valid_rate:.1f}% | {faithful_rate:.1f}% | {avg_sim:.2f} |"
                    )

            report_lines.append("")

        # Detailed results
        report_lines.extend(
            [
                "## Detailed Results",
                "",
            ]
        )

        for r in self.results:
            report_lines.extend(
                [
                    f"### {r.test_id} - {r.model_name}",
                    "",
                    f"**Domain**: {r.domain}",
                    f"**Input**: {r.input_description[:200]}{'...' if len(r.input_description) > 200 else ''}",
                    "",
                    f"**Annotation**: `{r.annotation}`",
                    "",
                    f"**Valid**: {r.is_valid} | **Faithful**: {r.is_faithful} | "
                    f"**Attempts**: {r.validation_attempts} | **Time**: {r.execution_time_seconds:.2f}s",
                    "",
                ]
            )

            if r.reconstruction:
                report_lines.extend(
                    [
                        f"**Reconstruction**: {r.reconstruction}",
                        f"**Similarity**: {r.reconstruction_similarity:.2f}"
                        if r.reconstruction_similarity
                        else "",
                        "",
                    ]
                )

            if r.validation_errors:
                report_lines.extend(
                    [
                        "**Validation Errors**:",
                        *[f"- {e}" for e in r.validation_errors[:5]],
                        "",
                    ]
                )

            if r.error:
                report_lines.append(f"**Error**: {r.error}")
                report_lines.append("")

            report_lines.append("---")
            report_lines.append("")

        with open(report_file, "w") as f:
            f.write("\n".join(report_lines))

        print(f"Report saved to: {report_file}")


async def main():
    """Run the benchmark."""
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set")
        return

    # Schema directory
    schema_dir = Path.home() / "Documents/git/HED/hed-schemas/schemas_latest_json"
    if not schema_dir.exists():
        # Try alternative path
        schema_dir = Path.home() / "git/hed-schemas/schemas_latest_json"

    if not schema_dir.exists():
        print(f"ERROR: Schema directory not found: {schema_dir}")
        return

    # Output directory
    output_dir = Path(__file__).parent / "benchmark_results"

    # Create and run benchmark
    benchmark = ModelBenchmark(
        api_key=OPENROUTER_API_KEY,
        schema_dir=schema_dir,
        output_dir=output_dir,
    )

    # Run with optional domain filter
    import sys

    domains = None
    if len(sys.argv) > 1:
        domains = sys.argv[1].split(",")
        print(f"Filtering to domains: {domains}")

    await benchmark.run_full_benchmark(domains=domains)


if __name__ == "__main__":
    asyncio.run(main())
