"""
Entity DAO - Data access objects for entity models.
遵循BaseDAO模式，提供实体相关的数据访问操作。
"""

from typing import List, Optional
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.base_dao import BaseDAO
from app.models.models import Entity, EntityMention, GraphRelation


class EntityDAO(BaseDAO[Entity]):
    """Entity数据访问对象"""

    def __init__(self, session: AsyncSession):
        super().__init__(Entity, session)

    async def find_by_name(self, name: str, fuzzy: bool = False) -> List[Entity]:
        """按名称查找实体

        Args:
            name: 实体名称
            fuzzy: 是否模糊匹配

        Returns:
            匹配的实体列表
        """
        if fuzzy:
            # 模糊搜索：使用原始SQL
            query_sql = "SELECT * FROM entities WHERE LOWER(name) LIKE LOWER(:name) ORDER BY mention_count DESC"
            result = await self.session.execute(text(query_sql), {"name": f"%{name}%"})
            rows = result.fetchall()

            # 将Row对象转换为Entity对象
            entities = []
            for row in rows:
                entity = Entity(
                    id=row[0],
                    name=row[1],
                    type=row[2],
                    canonical_name=row[3],
                    description=row[4],
                    embedding_id=row[5],
                    mention_count=row[6],
                    first_seen_at=row[7],
                    last_seen_at=row[8],
                    created_at=row[9],
                    updated_at=row[10]
                )
                entities.append(entity)
            return entities
        else:
            # 精确匹配：使用get_by
            entity = await self.get_by(name=name)
            return [entity] if entity else []

    async def find_similar(self, name: str, limit: int = 10) -> List[Entity]:
        """查找相似名称的实体

        Args:
            name: 查询名称
            limit: 返回数量限制

        Returns:
            相似实体列表，按提及次数排序
        """
        # 使用名称的第一个词进行搜索
        search_term = name.split()[0] if name else ""

        # 使用原始SQL进行模糊匹配
        query_sql = """
            SELECT * FROM entities
            WHERE LOWER(name) LIKE LOWER(:search_term)
            ORDER BY mention_count DESC
            LIMIT :limit
        """
        result = await self.session.execute(
            text(query_sql),
            {"search_term": f"%{search_term}%", "limit": limit}
        )
        rows = result.fetchall()

        # 将Row对象转换为Entity对象
        entities = []
        for row in rows:
            entity = Entity(
                id=row[0],
                name=row[1],
                type=row[2],
                canonical_name=row[3],
                description=row[4],
                embedding_id=row[5],
                mention_count=row[6],
                first_seen_at=row[7],
                last_seen_at=row[8],
                created_at=row[9],
                updated_at=row[10]
            )
            entities.append(entity)
        return entities

    async def get_top_entities(self, limit: int = 20, entity_type: str = None) -> List[Entity]:
        """获取提及最多的实体

        Args:
            limit: 返回数量限制
            entity_type: 实体类型过滤（可选）

        Returns:
            热门实体列表
        """
        if entity_type:
            query_sql = """
                SELECT * FROM entities
                WHERE type = :entity_type
                ORDER BY mention_count DESC
                LIMIT :limit
            """
            result = await self.session.execute(
                text(query_sql),
                {"entity_type": entity_type, "limit": limit}
            )
        else:
            query_sql = """
                SELECT * FROM entities
                ORDER BY mention_count DESC
                LIMIT :limit
            """
            result = await self.session.execute(
                text(query_sql),
                {"limit": limit}
            )

        rows = result.fetchall()
        entities = []
        for row in rows:
            entity = Entity(
                id=row[0],
                name=row[1],
                type=row[2],
                canonical_name=row[3],
                description=row[4],
                embedding_id=row[5],
                mention_count=row[6],
                first_seen_at=row[7],
                last_seen_at=row[8],
                created_at=row[9],
                updated_at=row[10]
            )
            entities.append(entity)
        return entities


class EntityMentionDAO(BaseDAO[EntityMention]):
    """EntityMention数据访问对象"""

    def __init__(self, session: AsyncSession):
        super().__init__(EntityMention, session)

    async def get_entity_mentions(
        self,
        entity_id: str,
        source_id: str = None
    ) -> List[EntityMention]:
        """获取实体的所有提及

        Args:
            entity_id: 实体ID
            source_id: 视频源ID过滤（可选）

        Returns:
            提及列表，按时间戳排序
        """
        # 使用原始SQL查询，兼容aiosqlite
        if source_id:
            query_sql = """
                SELECT * FROM entity_mentions
                WHERE entity_id = :entity_id AND source_id = :source_id
                ORDER BY timestamp ASC
            """
            result = await self.session.execute(
                text(query_sql),
                {"entity_id": entity_id, "source_id": source_id}
            )
        else:
            query_sql = """
                SELECT * FROM entity_mentions
                WHERE entity_id = :entity_id
                ORDER BY timestamp ASC
            """
            result = await self.session.execute(
                text(query_sql),
                {"entity_id": entity_id}
            )

        rows = result.fetchall()

        # 将Row对象转换为EntityMention对象
        mentions = []
        for row in rows:
            mention = EntityMention(
                id=row[0],
                entity_id=row[1],
                source_id=row[2],
                timestamp=row[3],
                context=row[4],
                confidence=row[5],
                created_at=row[6]
            )
            mentions.append(mention)
        return mentions

    async def get_mentions_by_source(
        self,
        source_id: str
    ) -> List[EntityMention]:
        """获取视频源的所有提及

        Args:
            source_id: 视频源ID

        Returns:
            该视频的所有实体提及
        """
        # 使用原始SQL查询，兼容aiosqlite
        query_sql = """
            SELECT * FROM entity_mentions
            WHERE source_id = :source_id
            ORDER BY timestamp ASC
        """
        result = await self.session.execute(
            text(query_sql),
            {"source_id": source_id}
        )
        rows = result.fetchall()

        # 将Row对象转换为EntityMention对象
        mentions = []
        for row in rows:
            mention = EntityMention(
                id=row[0],
                entity_id=row[1],
                source_id=row[2],
                timestamp=row[3],
                context=row[4],
                confidence=row[5],
                created_at=row[6]
            )
            mentions.append(mention)
        return mentions


class GraphRelationDAO(BaseDAO[GraphRelation]):
    """GraphRelation数据访问对象"""

    def __init__(self, session: AsyncSession):
        super().__init__(GraphRelation, session)

    async def get_entity_network(self, entity_id: str) -> List[GraphRelation]:
        """获取实体的关系网络

        Args:
            entity_id: 实体ID

        Returns:
            关系列表
        """
        # 使用原始SQL查询，兼容aiosqlite
        query_sql = """
            SELECT * FROM graph_relations
            WHERE source_entity_id = :entity_id OR target_entity_id = :entity_id
            ORDER BY created_at DESC
        """
        result = await self.session.execute(
            text(query_sql),
            {"entity_id": entity_id}
        )
        rows = result.fetchall()

        # 将Row对象转换为GraphRelation对象
        relations = []
        for row in rows:
            relation = GraphRelation(
                id=row[0],
                source_entity_id=row[1],
                target_entity_id=row[2],
                relation_type=row[3],
                confidence=row[4],
                source_id=row[5],
                evidence=row[6],
                created_at=row[7]
            )
            relations.append(relation)
        return relations

    async def find_relation(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: str
    ) -> Optional[GraphRelation]:
        """查找特定关系

        Args:
            source_entity_id: 源实体ID
            target_entity_id: 目标实体ID
            relation_type: 关系类型

        Returns:
            关系对象或None
        """
        return await self.get_by(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type
        )

    async def get_relations_by_source(self, source_id: str) -> List[GraphRelation]:
        """获取视频源的所有关系

        Args:
            source_id: 视频源ID

        Returns:
            关系列表
        """
        # 使用原始SQL查询，兼容aiosqlite
        query_sql = """
            SELECT * FROM graph_relations
            WHERE source_id = :source_id
            ORDER BY created_at DESC
        """
        result = await self.session.execute(
            text(query_sql),
            {"source_id": source_id}
        )
        rows = result.fetchall()

        # 将Row对象转换为GraphRelation对象
        relations = []
        for row in rows:
            relation = GraphRelation(
                id=row[0],
                source_entity_id=row[1],
                target_entity_id=row[2],
                relation_type=row[3],
                confidence=row[4],
                source_id=row[5],
                evidence=row[6],
                created_at=row[7]
            )
            relations.append(relation)
        return relations
