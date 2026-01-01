#!/usr/bin/env python3
"""
SophNet Integration Test Script
================================

Tests all SophNet AI services to ensure proper connectivity and functionality.

Usage:
    cd packages/backend
    python ../scripts/verify_sophnet_stack.py

Tests:
    1. LLM (DeepSeek-V3.2) - Chat completion
    2. VLM (Qwen2.5-VL) - Image understanding
    3. TTS (CosyVoice) - Text-to-speech
    4. Image (Qwen-Image) - Image generation
    5. Embedding (BGE-M3) - Text embeddings
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "backend"))

from app.services.sophnet_service import get_sophnet_service
from app.core import get_settings


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}[+] PASS: {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}[-] FAIL: {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.YELLOW}[*] {text}{Colors.RESET}")


def print_test_result(test_name: str, success: bool, details: str = ""):
    """Print formatted test result."""
    if success:
        print_success(f"{test_name}")
        if details:
            print(f"    {details}")
    else:
        print_error(f"{test_name}")
        if details:
            print(f"    {details}")


class SophNetTester:
    """Test suite for SophNet integration."""

    def __init__(self):
        """Initialize tester with SophNet service."""
        self.service = get_sophnet_service()
        self.results: Dict[str, bool] = {}
        self.start_time = time.time()

    async def test_llm(self) -> bool:
        """Test LLM (DeepSeek-V3.2) chat completion."""
        print_header("Test 1: LLM (DeepSeek-V3.2)")
        print_info("Sending test message to DeepSeek-V3.2...")

        try:
            messages = [
                {"role": "system", "content": "你是一个helpful的AI助手。"},
                {"role": "user", "content": "请用一句话介绍你自己。"}
            ]

            response = await self.service.chat(
                messages=messages,
                model="DeepSeek-V3.2",
                max_tokens=100,
            )

            success = bool(response) and not response.startswith("Error:")

            # Safely print response (handle encoding issues)
            try:
                response_preview = response[:100] + "..." if len(response) > 100 else response
            except Exception:
                response_preview = f"[Response length: {len(response)} chars]"

            print_test_result(
                "LLM Chat",
                success,
                response_preview if success else f"Error: {response}"
            )
            return success

        except Exception as e:
            print_test_result("LLM Chat", False, str(e))
            return False

    async def test_vlm(self) -> bool:
        """Test VLM (Qwen2.5-VL) image understanding."""
        print_header("Test 2: VLM (Qwen2.5-VL)")
        print_info("Sending test image to Qwen2.5-VL...")

        try:
            # Use a public image URL for testing
            test_image_url = "https://i.ibb.co/nQNGqL0/1beach1.jpg"

            response = await self.service.analyze_video_frame(
                prompt="请描述这张图片的内容。",
                image_url=test_image_url,
            )

            success = bool(response) and not response.startswith("Error:")
            print_test_result(
                "VLM Analysis",
                success,
                f"Response: {response[:100]}..." if success else f"Error: {response}"
            )
            return success

        except Exception as e:
            print_test_result("VLM Analysis", False, str(e))
            return False

    async def test_tts(self) -> bool:
        """Test TTS (CosyVoice) text-to-speech."""
        print_header("Test 3: TTS (CosyVoice)")
        print_info("Generating speech audio...")

        try:
            audio_data = await self.service.generate_speech(
                text="这是一个测试语音。",
                voice="longxiaochun",
            )

            # Verify audio data
            success = len(audio_data) > 1000  # At least 1KB of audio
            print_test_result(
                "TTS Generation",
                success,
                f"Generated {len(audio_data)} bytes of audio"
            )
            return success

        except Exception as e:
            print_test_result("TTS Generation", False, str(e))
            return False

    async def test_tts_to_file(self) -> bool:
        """Test TTS file output."""
        print_info("Testing TTS file save...")

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                output_path = Path(f.name)

            result_path = await self.service.generate_speech_to_file(
                text="测试保存到文件功能。",
                output_path=output_path,
            )

            success = result_path.exists() and result_path.stat().st_size > 1000
            print_test_result(
                "TTS to File",
                success,
                f"Saved to: {result_path} ({result_path.stat().st_size} bytes)"
            )

            # Cleanup
            result_path.unlink(missing_ok=True)
            return success

        except Exception as e:
            print_test_result("TTS to File", False, str(e))
            return False

    async def test_image(self) -> bool:
        """Test Image Generation (Qwen-Image)."""
        print_header("Test 4: Image Generation (Qwen-Image)")
        print_info("Generating test image...")
        print_info("[Note: Image generation requires additional EasyLLM configuration]")

        try:
            image_path = await self.service.generate_image(
                prompt="一只可爱的小猫",
                size="1024*1024",
            )

            # Verify image file
            path = Path(image_path)
            success = path.exists() and path.stat().st_size > 10000  # At least 10KB
            print_test_result(
                "Image Generation",
                success,
                f"Generated: {path.name} ({path.stat().st_size} bytes)"
            )

            # Cleanup
            if success:
                path.unlink(missing_ok=True)
            return success

        except NotImplementedError as e:
            # Async polling not implemented
            print_test_result("Image Generation", False, f"Async polling needed: {e}")
            return False
        except Exception as e:
            error_msg = str(e)
            # Check for known server error codes
            if "20031" in error_msg or "status:20031" in error_msg:
                print_test_result("Image Generation", False,
                    "Service not configured (EasyLLM image generator may need separate setup)")
            elif "500" in error_msg:
                print_test_result("Image Generation", False,
                    "Server error - image generation service may not be enabled")
            else:
                print_test_result("Image Generation", False, error_msg)
            return False

    async def test_embedding(self) -> bool:
        """Test Embedding (BGE-M3)."""
        print_header("Test 5: Embedding (BGE-M3)")
        print_info("Generating text embedding...")

        try:
            embedding = await self.service.get_embedding(
                text="这是一个测试文本，用于生成向量嵌入。"
            )

            success = len(embedding) > 500  # BGE-M3 should return 1024 dims
            print_test_result(
                "Embedding Generation",
                success,
                f"Generated {len(embedding)} dimensions"
            )
            return success

        except Exception as e:
            print_test_result("Embedding Generation", False, str(e))
            return False

    async def test_embedding_batch(self) -> bool:
        """Test batch embedding."""
        print_info("Testing batch embedding...")

        try:
            embeddings = await self.service.get_embeddings_batch([
                "第一个文本。",
                "第二个文本。",
                "第三个文本。",
            ])

            success = len(embeddings) == 3 and all(len(e) > 500 for e in embeddings)
            print_test_result(
                "Batch Embedding",
                success,
                f"Generated {len(embeddings)} embeddings"
            )
            return success

        except Exception as e:
            print_test_result("Batch Embedding", False, str(e))
            return False

    async def run_all_tests(self):
        """Run all integration tests."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║     SophNet Integration Test Suite                          ║")
        print("║     Testing all AI services connectivity                    ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}\n")

        settings = get_settings()
        print_info(f"API Key: {settings.sophnet_api_key[:20]}...")
        print_info(f"Project ID: {settings.sophnet_project_id}")
        print_info(f"TTS EasyLLM ID: {settings.sophnet_tts_easyllm_id}")
        print_info(f"Embedding EasyLLM ID: {settings.sophnet_embedding_easyllm_id}")

        # Run tests
        self.results["llm"] = await self.test_llm()
        self.results["vlm"] = await self.test_vlm()
        self.results["tts"] = await self.test_tts()
        self.results["tts_file"] = await self.test_tts_to_file()
        self.results["image"] = await self.test_image()
        self.results["embedding"] = await self.test_embedding()
        self.results["embedding_batch"] = await self.test_embedding_batch()

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print test summary."""
        elapsed = time.time() - self.start_time

        print_header("Test Summary")
        print(f"Total tests: {len(self.results)}")
        print(f"Passed: {sum(self.results.values())}")
        print(f"Failed: {sum(1 for v in self.results.values() if not v)}")
        print(f"Duration: {elapsed:.2f}s\n")

        for test_name, passed in self.results.items():
            status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
            print(f"  {test_name:20s}: {status}")

        all_passed = all(self.results.values())
        if all_passed:
            print(f"\n{Colors.GREEN}{Colors.BOLD}[+] All tests PASSED!{Colors.RESET}")
            print(f"{Colors.GREEN}SophNet integration is fully functional.{Colors.RESET}\n")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}[-] Some tests FAILED{Colors.RESET}")
            print(f"{Colors.RED}Please check the errors above.{Colors.RESET}\n")


async def main():
    """Main entry point."""
    tester = SophNetTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user.{Colors.RESET}")
        sys.exit(1)
