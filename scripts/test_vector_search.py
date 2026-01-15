"""
测试向量存储搜索功能
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "backend"))

from app.shared.storage import get_vector_store

def test_vector_search():
    """测试向量搜索"""
    print("=" * 60)
    print("测试向量存储搜索功能")
    print("=" * 60)

    # 初始化向量存储
    vector_store = get_vector_store()

    # 获取统计信息
    stats = vector_store.get_stats()
    print(f"\n[统计] 向量存储统计:")
    print(f"   - 总文档数: {stats['total_documents']}")
    print(f"   - 集合名称: {stats['collection_name']}")
    print(f"   - 地址: {stats['host']}:{stats['port']}")

    # 获取所有文档
    print(f"\n[文档] 获取所有文档...")
    all_docs = vector_store.get_all_documents()
    print(f"   - 总共 {len(all_docs)} 个文档")

    if all_docs:
        print(f"\n   示例文档（前 3 个）:")
        for i, doc in enumerate(all_docs[:3], 1):
            metadata = doc.get("metadata", {})
            print(f"   [{i}] source_id={metadata.get('source_id', 'N/A')}")
            print(f"       type={metadata.get('type', 'N/A')}")
            print(f"       start={metadata.get('start', 'N/A')}s")
            print(f"       text={doc.get('text', '')[:100]}...")
            print()

    # 获取特定 source 的文档
    print(f"\n[源文档] 搜索特定 source 的文档...")
    source_id = all_docs[0].get("metadata", {}).get("source_id") if all_docs else None
    if source_id:
        source_docs = vector_store.get_source_documents(source_id)
        print(f"   - Source {source_id} 有 {len(source_docs)} 个文档")

    # 测试搜索功能
    print(f"\n[搜索] 测试搜索功能...")
    test_queries = [
        "视频讲了什么",
        "你好",
        "内容",
        "视频",
    ]

    for query in test_queries:
        print(f"\n   搜索: '{query}'")
        results = vector_store.search(query=query, n_results=5)
        print(f"   结果: {len(results)} 个")

        if results:
            for i, r in enumerate(results[:2], 1):
                metadata = r.get("metadata", {})
                print(f"   [{i}] score={r.get('distance', 0):.3f}")
                print(f"       source={metadata.get('source_id', 'N/A')}")
                print(f"       text={r.get('text', '')[:80]}...")
        else:
            print("   [警告] 没有找到结果！")

    # 测试带 source_id 过滤的搜索
    if source_id:
        print(f"\n[过滤搜索] 测试带 source_id 过滤的搜索...")
        query = "视频"
        print(f"   搜索: '{query}' (source_id={source_id})")
        results = vector_store.search(query=query, source_ids=[source_id], n_results=5)
        print(f"   结果: {len(results)} 个")

        if results:
            for i, r in enumerate(results[:2], 1):
                metadata = r.get("metadata", {})
                print(f"   [{i}] score={r.get('distance', 0):.3f}")
                print(f"       text={r.get('text', '')[:80]}...")
        else:
            print("   [警告] 没有找到结果！")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_vector_search()

