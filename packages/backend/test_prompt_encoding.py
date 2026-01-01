import asyncio
import sys
sys.path.insert(0, '.')

async def test_prompts():
    from app.services.sophnet_service import get_sophnet_service

    sophnet = get_sophnet_service()

    # Test 1: Simple Chinese prompt
    print("=== Test 1: Simple Chinese ===")
    try:
        result1 = await sophnet.generate_image(prompt="奔跑小猫", size="1024*1024")
        print(f"SUCCESS: {result1}")
    except Exception as e:
        print(f"FAILED: {e}")

    # Test 2: English prompt
    print("\n=== Test 2: English ===")
    try:
        result2 = await sophnet.generate_image(prompt="Running cat, flat illustration style", size="1024*1024")
        print(f"SUCCESS: {result2}")
    except Exception as e:
        print(f"FAILED: {e}")

asyncio.run(test_prompts())
