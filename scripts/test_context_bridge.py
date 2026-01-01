"""
Context Bridge Feature Test Script

Tests the Context Bridge API endpoint for generating bridging summaries
when users seek to different timestamps in a video.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
API_BASE = "http://localhost:8000"


async def test_context_bridge(source_id: str, timestamp: float, previous_timestamp: float | None = None):
    """
    Test the Context Bridge API endpoint.

    Args:
        source_id: Video source ID to test
        timestamp: Target timestamp to seek to (in seconds)
        previous_timestamp: Optional - where user was before seeking
    """
    url = f"{API_BASE}/api/chat/context-bridge"

    payload = {
        "source_id": source_id,
        "timestamp": timestamp,
    }

    if previous_timestamp is not None:
        payload["previous_timestamp"] = previous_timestamp

    print(f"\n{'='*60}")
    print(f"Testing Context Bridge API")
    print(f"{'='*60}")
    print(f"Source ID: {source_id}")
    mins = int(timestamp // 60)
    secs = int(timestamp % 60)
    print(f"Target Timestamp: {timestamp}s ({mins:02d}:{secs:02d})")
    if previous_timestamp is not None:
        prev_mins = int(previous_timestamp // 60)
        prev_secs = int(previous_timestamp % 60)
        print(f"Previous Timestamp: {previous_timestamp}s ({prev_mins:02d}:{prev_secs:02d})")
        print(f"Jump Distance: {abs(timestamp - previous_timestamp):.1f}s")
    print(f"{'='*60}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()

                print("[OK] API Response Successful\n")
                print(f"Timestamp: {data.get('timestamp_str')}")
                print(f"Previous Context: {data.get('previous_context')}")
                print(f"Current Context: {data.get('current_context')}")
                print(f"\n[*] Bridging Summary:")
                print(f"  {data.get('summary')}")

                # Validate response structure
                required_fields = ["summary", "previous_context", "current_context", "timestamp_str"]
                missing = [f for f in required_fields if f not in data]
                if missing:
                    print(f"\n[!] Missing fields: {missing}")
                else:
                    print("\n[OK] All required fields present")

                return data
            else:
                print(f"[ERROR] API Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None

    except httpx.ConnectError:
        print("[ERROR] Connection Error: Could not connect to the API server.")
        print(f"   Make sure the backend is running at {API_BASE}")
        return None
    except httpx.TimeoutException:
        print("[ERROR] Timeout Error: Request took too long.")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected Error: {e}")
        return None


async def list_available_sources():
    """Get list of available video sources."""
    url = f"{API_BASE}/api/sources/"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                sources = data.get("sources", [])

                print(f"\n{'='*60}")
                print(f"Available Video Sources ({len(sources)})")
                print(f"{'='*60}")

                for source in sources:
                    duration = source.get("duration")
                    if duration is not None:
                        mins = int(duration // 60)
                        secs = int(duration % 60)
                        duration_str = f"{mins:02d}:{secs:02d}"
                    else:
                        duration_str = "N/A"
                    status = source.get("status")

                    status_icon = "[OK]" if status == "done" else "[..]"
                    print(f"{status_icon} [{source['id'][:8]}...] {source['title'][:40]}")
                    print(f"   Duration: {duration_str} | Status: {status}")

                print(f"{'='*60}\n")

                return sources
            else:
                print(f"[ERROR] Failed to get sources: HTTP {response.status_code}")
                return []

    except Exception as e:
        print(f"[ERROR] Error getting sources: {e}")
        return []


async def main():
    """Main test function."""
    print("\n" + "="*60)
    print("Context Bridge Feature Test")
    print("="*60)

    # Step 1: Get available sources
    sources = await list_available_sources()

    # Filter for completed sources
    done_sources = [s for s in sources if s.get("status") == "done"]

    if not done_sources:
        print("[ERROR] No completed sources found. Please wait for video processing to complete.")
        return

    # Use the first completed source for testing
    test_source = done_sources[0]
    source_id = test_source["id"]
    duration = test_source.get("duration", 0)

    if duration < 120:
        print("[!] Video is too short for meaningful context bridge testing.")
        print(f"   Duration: {duration}s (need at least 120s)")

    # Step 2: Test scenarios
    print("\n" + "="*60)
    print("Running Test Scenarios")
    print("="*60)

    scenarios = []

    if duration > 0:
        # Scenario 1: Jump to middle from beginning
        if duration > 120:
            scenarios.append({
                "name": "Jump from start to middle",
                "timestamp": duration / 2,
                "previous": 0,
            })

        # Scenario 2: Jump to near end
        if duration > 180:
            scenarios.append({
                "name": "Jump from middle to near end",
                "timestamp": duration * 0.8,
                "previous": duration / 2,
            })

        # Scenario 3: Jump to specific point (30 seconds)
        if duration > 60:
            scenarios.append({
                "name": "Jump to 30s mark",
                "timestamp": 30,
                "previous": None,  # No previous timestamp
            })
    else:
        # Fallback scenarios for videos without duration info
        scenarios = [
            {"name": "Test at 30s", "timestamp": 30, "previous": 0},
            {"name": "Test at 60s", "timestamp": 60, "previous": 30},
            {"name": "Test at 120s", "timestamp": 120, "previous": 60},
        ]

    # Run each scenario
    results = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")

        result = await test_context_bridge(
            source_id=source_id,
            timestamp=scenario["timestamp"],
            previous_timestamp=scenario.get("previous")
        )

        if result:
            results.append({
                "scenario": scenario["name"],
                "summary": result.get("summary"),
                "success": True
            })
        else:
            results.append({
                "scenario": scenario["name"],
                "summary": None,
                "success": False
            })

    # Step 3: Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    success_count = sum(1 for r in results if r["success"])
    print(f"Scenarios Tested: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(results) - success_count}")

    if success_count == len(results):
        print("\n[OK] All tests passed!")
    else:
        print("\n[!] Some tests failed. Check the logs above.")

    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())
