"""Test workflow with examples from FRONTEND_GUIDE.md"""
import asyncio
from pathlib import Path

from langchain_community.chat_models import ChatOllama

from src.agents.workflow import HedAnnotationWorkflow

# Test cases from FRONTEND_GUIDE.md
TEST_CASES = [
    {
        "name": "Example 1: Simple Stimulus",
        "input": "A red circle appears on the screen",
        "expected_tags": ["Sensory-event", "Visual-presentation", "Red", "Circle"],
    },
    {
        "name": "Example 2: Complex Event",
        "input": "A green triangle target appears on the left side of the computer screen and the participant presses the left mouse button",
        "expected_tags": ["Sensory-event", "Visual-presentation", "Green", "Triangle",
                         "Agent-action", "Participant-response", "Press", "Mouse-button"],
    },
    {
        "name": "Example 3: Simple Button Press",
        "input": "The participant pressed a button",
        "expected_tags": ["Participant-response", "Press"],
    },
]


async def test_workflow():
    """Test workflow with multiple examples."""
    print("=" * 80)
    print("TESTING WORKFLOW WITH FRONTEND_GUIDE.MD EXAMPLES")
    print("=" * 80)

    # Initialize LLM
    llm = ChatOllama(
        base_url="http://localhost:11434",
        model="llama3.2:1b",
        temperature=0.1,
    )

    # Initialize workflow
    workflow = HedAnnotationWorkflow(
        llm=llm,
        schema_dir=Path("/home/yahya/git/hed-schemas/schemas_latest_json"),
        validator_path=None,
        use_js_validator=False,
    )

    results = []
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"Input: {test_case['input']}")
        print()

        try:
            result = await asyncio.wait_for(
                workflow.run(
                    input_description=test_case["input"],
                    schema_version="8.4.0",
                    max_validation_attempts=3,
                    max_total_iterations=10,
                ),
                timeout=60.0,
            )

            annotation = result["current_annotation"]
            print(f"✓ SUCCESS")
            print(f"  Annotation: {annotation}")
            print(f"  Valid: {result['is_valid']}")
            print(f"  Faithful: {result['is_faithful']}")
            print(f"  Iterations: {result['total_iterations']}")
            print(f"  Validation attempts: {result['validation_attempts']}")

            if result['validation_warnings']:
                print(f"  Warnings: {len(result['validation_warnings'])}")
                for warning in result['validation_warnings'][:3]:
                    print(f"    - {warning[:100]}")

            if result['validation_errors']:
                print(f"  Errors: {len(result['validation_errors'])}")
                for error in result['validation_errors'][:3]:
                    print(f"    - {error[:100]}")

            # Check if expected tags are present
            missing_tags = [tag for tag in test_case['expected_tags']
                           if tag not in annotation]
            if missing_tags:
                print(f"  Missing expected tags: {missing_tags}")

            results.append({
                "name": test_case['name'],
                "success": True,
                "annotation": annotation,
                "iterations": result['total_iterations'],
                "is_valid": result['is_valid'],
            })

        except asyncio.TimeoutError:
            print(f"✗ TIMEOUT after 60 seconds")
            results.append({
                "name": test_case['name'],
                "success": False,
                "error": "Timeout",
            })
        except Exception as e:
            print(f"✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "name": test_case['name'],
                "success": False,
                "error": str(e),
            })

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    successful = sum(1 for r in results if r['success'])
    print(f"Passed: {successful}/{len(TEST_CASES)}")
    print()
    for r in results:
        status = "✓" if r['success'] else "✗"
        print(f"{status} {r['name']}")
        if r['success']:
            print(f"  Iterations: {r['iterations']}, Valid: {r['is_valid']}")
        else:
            print(f"  Error: {r.get('error', 'Unknown')}")


if __name__ == "__main__":
    asyncio.run(test_workflow())
