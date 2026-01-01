import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from app.services.analysis_service import get_analysis_service

    service = get_analysis_service()
    source_id = "0db60f05-2855-4768-a18e-b7bfbb350b66"

    # First, let's test image generation directly
    print("=== Testing image generation ===")
    try:
        from app.services.sophnet_service import get_sophnet_service
        sophnet = get_sophnet_service()
        result = await sophnet.generate_image(prompt="游戏角色", size="1024*1024")
        print(f"Image generation SUCCESS: {result}")
    except Exception as e:
        print(f"Image generation FAILED: {e}")

    # Now test one-pager
    print("\n=== Testing one-pager ===")
    service.clear_cache([source_id])
    result = await service.generate_executive_summary(source_id, use_cache=False)

    print(f"Headline: {result.get('headline')}")
    print(f"Evidence Images: {len(result.get('evidence_images', []))} items")
    print(f"Conceptual Image: {result.get('conceptual_image') or 'NONE'}")

asyncio.run(test())
