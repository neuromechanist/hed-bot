"""Test script for vision model integration.

This script tests the image annotation pipeline by:
1. Loading a sample image
2. Converting it to base64
3. Sending it to the /annotate-from-image endpoint
4. Verifying the response

Usage:
    python test_vision_integration.py [image_path]
"""

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path

import httpx
from PIL import Image


def image_to_base64(image_path: str) -> str:
    """Convert an image file to base64 data URI.

    Args:
        image_path: Path to image file

    Returns:
        Data URI string
    """
    # Open and validate image
    img = Image.open(image_path)
    print(f"Loaded image: {img.format} {img.size} {img.mode}")

    # Convert to base64
    from io import BytesIO

    buffer = BytesIO()
    img_format = img.format or "PNG"
    img.save(buffer, format=img_format)
    buffer.seek(0)

    base64_bytes = base64.b64encode(buffer.read())
    base64_str = base64_bytes.decode("utf-8")

    # Create data URI
    mime_type = f"image/{img_format.lower()}"
    data_uri = f"data:{mime_type};base64,{base64_str}"

    print(f"Converted to base64 (length: {len(base64_str)} bytes)")
    return data_uri


async def test_annotate_from_image(
    image_path: str,
    api_url: str = "http://localhost:38427",
    custom_prompt: str | None = None,
):
    """Test the /annotate-from-image endpoint.

    Args:
        image_path: Path to test image
        api_url: API base URL
        custom_prompt: Optional custom vision prompt
    """
    print(f"\n{'='*60}")
    print(f"Testing Image Annotation Pipeline")
    print(f"{'='*60}\n")

    # Convert image to base64
    print(f"1. Loading image: {image_path}")
    data_uri = image_to_base64(image_path)

    # Prepare request
    request_data = {
        "image": data_uri,
        "schema_version": "8.4.0",
        "max_validation_attempts": 5,
        "run_assessment": True,
    }

    if custom_prompt:
        request_data["prompt"] = custom_prompt
        print(f"2. Custom prompt: {custom_prompt}")
    else:
        print(f"2. Using default vision prompt")

    # Send request
    print(f"\n3. Sending request to {api_url}/annotate-from-image...")
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{api_url}/annotate-from-image",
                json=request_data,
            )
            response.raise_for_status()

            result = response.json()

            # Display results
            print(f"\n{'='*60}")
            print(f"Results")
            print(f"{'='*60}\n")

            print(f"Image Description:")
            print(f"  {result['image_description']}\n")

            print(f"HED Annotation:")
            print(f"  {result['annotation']}\n")

            print(f"Status:")
            print(f"  Valid: {result['is_valid']}")
            print(f"  Faithful: {result['is_faithful']}")
            print(f"  Complete: {result['is_complete']}")
            print(f"  Attempts: {result['validation_attempts']}")
            print(f"  Overall: {result['status']}\n")

            if result["validation_errors"]:
                print(f"Validation Errors:")
                for error in result["validation_errors"]:
                    print(f"  - {error}")
                print()

            if result["validation_warnings"]:
                print(f"Validation Warnings:")
                for warning in result["validation_warnings"]:
                    print(f"  - {warning}")
                print()

            print(f"Evaluation Feedback:")
            print(f"  {result['evaluation_feedback']}\n")

            if result["assessment_feedback"]:
                print(f"Assessment Feedback:")
                print(f"  {result['assessment_feedback']}\n")

            print(f"Image Metadata:")
            metadata = result["image_metadata"]
            print(f"  Format: {metadata.get('format')}")
            print(f"  Size: {metadata.get('width')}x{metadata.get('height')}")
            print(f"  Size (MB): {metadata.get('size_mb', 0):.2f}")

            print(f"\n{'='*60}")
            print(f"Test completed successfully!")
            print(f"{'='*60}\n")

            return result

        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error {e.response.status_code}")
            print(f"Response: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test vision model integration for HED-BOT"
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        help="Path to test image (PNG, JPG, or WebP)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:38427",
        help="API base URL (default: http://localhost:38427)",
    )
    parser.add_argument(
        "--prompt",
        help="Custom vision prompt (optional)",
    )

    args = parser.parse_args()

    # Use default test image if none provided
    if not args.image_path:
        print("No image path provided. Please provide a test image.")
        print("Usage: python test_vision_integration.py <image_path>")
        sys.exit(1)

    # Verify image exists
    if not Path(args.image_path).exists():
        print(f"Error: Image not found: {args.image_path}")
        sys.exit(1)

    # Run test
    asyncio.run(
        test_annotate_from_image(
            image_path=args.image_path,
            api_url=args.url,
            custom_prompt=args.prompt,
        )
    )


if __name__ == "__main__":
    main()
