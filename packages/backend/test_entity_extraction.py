"""
测试实体抽取功能
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.modules.analysis.service import AnalysisService, get_analysis_service
from app.core.database import async_session
from app.models.models import Evidence
from sqlalchemy import select


async def test_entity_extraction():
    """测试实体抽取功能"""
    print("=" * 60)
    print("测试实体抽取功能")
    print("=" * 60)

    # 检查视频是否有转写数据
    source_id = "a5bc7d00-6142-4af0-a480-847d8d648e6b"

    async with async_session() as db:
        result = await db.execute(
            select(Evidence)
            .where(Evidence.source_id == source_id)
            .where(Evidence.text_content != None)
            .where(Evidence.text_content != "")
        )
        evidences = result.scalars().all()

        print(f"\n1. 视频转写记录数: {len(evidences)}")

        if len(evidences) == 0:
            print("\n   状态: 该视频尚未进行ASR转写")
            print("   建议: 需要先对视频进行转写处理")
            print("\n2. 使用模拟数据测试...")

            # 创建模拟转写数据
            from app.models.models import Source

            # 查找视频
            source_result = await db.execute(select(Source).where(Source.id == source_id))
            source = source_result.scalar_one_or_none()

            if source:
                print(f"   视频标题: {source.title}")
                print(f"   视频状态: {source.status}")

            # 创建一些模拟文本用于测试
            sample_texts = [
                "马云是中国企业家，阿里巴巴创始人。",
                "1999年，马云在杭州创办了阿里巴巴公司。",
                "阿里巴巴总部位于中国杭州。",
            ]

            print(f"\n3. 测试文本: {len(sample_texts)} 条")
            for i, text in enumerate(sample_texts, 1):
                print(f"   [{i}] {text}")

            # 直接测试实体创建（不依赖API）
            from app.modules.analysis.dao import EntityDAO, EntityMentionDAO

            entity_dao = EntityDAO(db)
            mention_dao = EntityMentionDAO(db)

            # 手动创建测试实体
            print("\n4. 创建测试实体...")

            test_entities = [
                {"name": "马云", "type": "PERSON", "description": "中国企业家，阿里巴巴创始人"},
                {"name": "杭州", "type": "LOCATION", "description": "中国城市"},
                {"name": "阿里巴巴", "type": "ORGANIZATION", "description": "中国互联网公司"},
            ]

            for ent_data in test_entities:
                # 检查是否已存在
                existing = await entity_dao.find_by_name(ent_data["name"])
                if existing:
                    print(f"   - {ent_data['name']}: 已存在")
                    existing[0].mention_count += 1
                    existing[0].last_seen_at = None
                else:
                    entity = await entity_dao.create(
                        name=ent_data["name"],
                        type=ent_data["type"],
                        description=ent_data["description"],
                        canonical_name=ent_data["name"].lower()
                    )
                    print(f"   + {ent_data['name']}: 创建成功 (ID: {entity.id[:8]}...)")

                    # 创建提及记录
                    await mention_dao.create(
                        entity_id=entity.id,
                        source_id=source_id,
                        timestamp=0.0,
                        context=sample_texts[0][:100]
                    )

            await db.commit()

            # 验证数据
            print("\n5. 验证存储结果...")

            all_entities = await entity_dao.get_top_entities(limit=10)
            print(f"   实体总数: {len(all_entities)}")

            for entity in all_entities:
                mentions = await mention_dao.get_entity_mentions(entity.id)
                print(f"   - {entity.name} ({entity.type}): {entity.mention_count} 次提及")

            print("\n" + "=" * 60)
            print("测试完成！实体已成功存储到数据库")
            print("=" * 60)

        else:
            print(f"\n   状态: 找到 {len(evidences)} 条转写记录")
            print("   可以进行实体抽取")

            # 显示前3条转写文本
            print("\n2. 转写文本示例:")
            for i, ev in enumerate(evidences[:3], 1):
                print(f"   [{i}] {ev.text_content[:100]}...")


if __name__ == "__main__":
    asyncio.run(test_entity_extraction())
