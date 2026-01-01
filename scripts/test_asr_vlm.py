#!/usr/bin/env python3
"""
Test ASR (Whisper) and VLM (SophNet Qwen2.5-VL) integration.

Usage:
    cd packages/backend
    python ../scripts/test_asr_vlm.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "backend"))

from app.services.intelligence import IntelligenceService, _WHISPER_AVAILABLE
from app.services.sophnet_service import get_sophnet_service


def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(f" {text}")
    print(f"{'=' * 60}\n")


def print_success(text: str):
    print(f"[+] PASS: {text}")


def print_error(text: str):
    print(f"[-] FAIL: {text}")


def print_info(text: str):
    print(f"[*] {text}")


async def test_whisper_asr():
    """Test Whisper ASR with a sample audio file if available."""
    print_header("Test 1: Whisper ASR")

    if not _WHISPER_AVAILABLE:
        print_error("Whisper not installed")
        print_info("Install with: pip install openai-whisper")
        return False

    print_info("Whisper is installed, checking for test audio...")

    # Check for test audio file
    test_audio = Path(__file__).parent.parent / "packages" / "backend" / "vedios" / "test_audio.wav"
    if not test_audio.exists():
        # Look for any audio in temp directory
        temp_dir = Path(__file__).parent.parent / "packages" / "backend" / "data" / "temp"
        for audio_file in temp_dir.rglob("*.wav"):
            test_audio = audio_file
            break

    if not test_audio.exists():
        print_error("No test audio file found")
        print_info("Skipping ASR test - upload a video first to generate audio")
        return None  # Not a failure, just skipped

    print_info(f"Using audio file: {test_audio}")

    try:
        intelligence = IntelligenceService()
        transcripts = await intelligence.transcribe_audio(test_audio)

        if transcripts:
            print_success(f"ASR transcribed {len(transcripts)} segments")
            for i, seg in enumerate(transcripts[:3]):
                print(f"    [{i+1}] {seg['timestamp']:.2f}s: {seg['text'][:50]}...")
            if len(transcripts) > 3:
                print(f"    ... and {len(transcripts) - 3} more segments")
            return True
        else:
            print_error("No transcripts generated")
            return False

    except Exception as e:
        print_error(f"ASR test failed: {e}")
        return False


async def test_sophnet_vlm():
    """Test SophNet VLM with a sample image if available."""
    print_header("Test 2: SophNet VLM (Qwen2.5-VL)")

    print_info("Checking SophNet service...")

    try:
        sophnet = get_sophnet_service()

        if not sophnet.api_key:
            print_error("SophNet API key not configured")
            return False

        print_info(f"SophNet API key configured: {sophnet.api_key[:20]}...")

        # Look for test image
        test_image = None
        temp_dir = Path(__file__).parent.parent / "packages" / "backend" / "data" / "temp"
        for img_file in temp_dir.rglob("*.jpg"):
            test_image = img_file
            break

        if not test_image:
            print_error("No test image found")
            print_info("Skipping VLM test - upload a video first to generate frames")
            return None  # Not a failure, just skipped

        print_info(f"Using image file: {test_image}")

        # Test VLM
        result = await sophnet.analyze_video_frame(
            prompt="请用中文简要描述这张图片的内容。",
            image_path=test_image,
        )

        if result and not result.startswith("Error:"):
            print_success("VLM analysis completed")
            print(f"    Result: {result[:100]}...")
            return True
        else:
            print_error(f"VLM analysis failed: {result}")
            return False

    except Exception as e:
        print_error(f"VLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "=" * 60)
    print("  ASR + VLM Integration Test")
    print("=" * 60)

    results = {}

    # Test ASR
    results["whisper_asr"] = await test_whisper_asr()

    # Test VLM
    results["sophnet_vlm"] = await test_sophnet_vlm()

    # Summary
    print_header("Test Summary")

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")

    for name, result in results.items():
        if result is True:
            status = "PASS"
        elif result is False:
            status = "FAIL"
        else:
            status = "SKIP"
        print(f"  {name}: {status}")

    if failed > 0:
        print("\n[!] Some tests failed. Please check the errors above.")
        sys.exit(1)
    elif skipped > 0:
        print("\n[*] Some tests were skipped. Upload a video to enable full testing.")
    else:
        print("\n[+] All tests passed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Test interrupted by user")
        sys.exit(1)
