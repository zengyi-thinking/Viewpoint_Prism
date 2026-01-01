import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from app.services.analysis_service import get_analysis_service

    service = get_analysis_service()
    source_id = "0db60f05-2855-4768-a18e-b7bfbb350b66"

    # Clear cache first
    service.clear_cache([source_id])
    print("Cache cleared")

    print(f"Generating one-pager for {source_id}...")
    result = await service.generate_executive_summary(source_id, use_cache=False)

    print(f"\n=== API Result ===")
    print(f"Headline: {result.get('headline')}")
    print(f"Evidence Images: {len(result.get('evidence_images', []))} items")
    for img in result.get('evidence_images', []):
        print(f"  - {img}")

asyncio.run(test())
