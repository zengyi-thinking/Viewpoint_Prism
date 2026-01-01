import asyncio
import sys
sys.path.insert(0, '.')

async def test_image_generation():
    from app.services.sophnet_service import get_sophnet_service

    sophnet = get_sophnet_service()

    # Test with same prompt as example
    prompt = "奔跑小猫"
    print(f"Testing image generation with prompt: {prompt}")

    try:
        result = await sophnet.generate_image(prompt=prompt, size="1328*1328")
        print(f"SUCCESS! Image saved to: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_image_generation())
