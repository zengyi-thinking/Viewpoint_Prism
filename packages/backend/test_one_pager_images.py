import asyncio
import sys
sys.path.insert(0, '.')

from app.services.analysis_service import get_analysis_service

async def test_one_pager():
    service = get_analysis_service()
    source_id = "0db60f05-2855-4768-a18e-b7bfbb350b66"

    print(f"Testing one-pager generation for {source_id}...")
    result = await service.generate_executive_summary(source_id, use_cache=False)

    print(f"\n=== Result ===")
    print(f"Headline: {result.get('headline')}")
    print(f"TL;DR: {result.get('tldr')[:80]}...")
    print(f"Insights: {len(result.get('insights', []))} items")
    print(f"Conceptual Image: {result.get('conceptual_image') or 'NONE'}")
    print(f"Evidence Images: {result.get('evidence_images') or ['NONE']}")

if __name__ == "__main__":
    asyncio.run(test_one_pager())
