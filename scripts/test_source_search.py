"""
测试特定视频源的向量搜索
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "backend"))

from app.shared.storage import get_vector_store

def test_specific_source():
    """测试特定视频源"""
    source_id = "bb762472-522e-448b-8e98-b86574b022e4"

    print("=" * 60)
    print(f"测试视频源: {source_id}")
    print("=" * 60)

    vector_store = get_vector_store()

    # 获取该视频源的文档
    print(f"\n[1] 获取视频源文档...")
    docs = vector_store.get_source_documents(source_id)
    print(f"   找到 {len(docs)} 个文档")

    if docs:
        print(f"\n   前 3 个文档:")
        for i, doc in enumerate(docs[:3], 1):
            metadata = doc.get("metadata", {})
            print(f"   [{i}] type={metadata.get('type')}")
            print(f"       start={metadata.get('start')}s")
            print(f"       text={doc.get('text', '')[:100]}...")
            print()

    # 测试不同的搜索查询
    print(f"\n[2] 测试搜索查询...")
    test_queries = [
        "视频讲了什么",
        "你好，请你分析一下这个视频",
        "内容",
        "视频",
        "画面",
    ]

    for query in test_queries:
        print(f"\n   查询: '{query}'")
        results = vector_store.search(query=query, source_ids=[source_id], n_results=5)
        print(f"   结果: {len(results)} 个")

        if results:
            for i, r in enumerate(results[:2], 1):
                metadata = r.get("metadata", {})
                print(f"   [{i}] score={r.get('distance', 0):.3f}")
                print(f"       type={metadata.get('type')}")
                print(f"       text={r.get('text', '')[:80]}...")
        else:
            print("   [!] 没有结果")

    # 测试不带过滤的搜索
    print(f"\n[3] 测试不带 source_id 过滤的搜索...")
    query = "视频"
    results = vector_store.search(query=query, n_results=10)

    # 筛选出该视频源的结果
    filtered_results = [r for r in results if r.get("metadata", {}).get("source_id") == source_id]
    print(f"   查询: '{query}' (不过滤)")
    print(f"   总结果: {len(results)}")
    print(f"   该视频源的结果: {len(filtered_results)}")

    if filtered_results:
        print(f"\n   该视频源的结果:")
        for i, r in enumerate(filtered_results[:3], 1):
            print(f"   [{i}] score={r.get('distance', 0):.3f}")
            print(f"       text={r.get('text', '')[:80]}...")

if __name__ == "__main__":
    test_specific_source()
