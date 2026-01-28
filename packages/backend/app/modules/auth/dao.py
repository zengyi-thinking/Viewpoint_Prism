"""
认证模块数据访问层
提供用户、工程、会话的数据库操作
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.base_dao import BaseDAO
from app.modules.auth.models import User, ProjectMember, ProjectAccessHistory, UserSession
from app.models.models import Project


class AuthDAO:
    """认证相关数据访问对象"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_dao = BaseDAO(User, db)
        self.session_dao = BaseDAO(UserSession, db)
        self.access_history_dao = BaseDAO(ProjectAccessHistory, db)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return await self.user_dao.get_by(username=username)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return await self.user_dao.get_by(email=email)

    async def create_user(self, username: str, email: str, password_hash: str, role: str = "user") -> User:
        """创建新用户"""
        return await self.user_dao.create(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True
        )

    async def update_last_login(self, user_id: str) -> None:
        """更新用户最后登录时间"""
        await self.user_dao.update(user_id, last_login_at=datetime.utcnow())

    async def create_session(
        self,
        user_id: str,
        token_jti: str,
        expires_at: datetime,
        refresh_token_jti: Optional[str] = None,
        refresh_expires_at: Optional[datetime] = None
    ) -> UserSession:
        """创建用户会话"""
        return await self.session_dao.create(
            user_id=user_id,
            token_jti=token_jti,
            refresh_token_jti=refresh_token_jti,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at
        )

    async def revoke_session(self, token_jti: str) -> bool:
        """吊销会话"""
        session = await self.session_dao.get_by(token_jti=token_jti)
        if session:
            await self.session_dao.update(session.id, is_revoked=True)
            return True
        return False

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        """吊销用户所有会话"""
        return await self.session_dao.update_by(
            filters={"user_id": user_id, "is_revoked": False},
            is_revoked=True
        )

    async def get_active_session(self, token_jti: str) -> Optional[UserSession]:
        """获取活跃会话"""
        return await self.session_dao.get_by(token_jti=token_jti, is_revoked=False)

    async def record_access_history(self, user_id: str, project_id: str) -> ProjectAccessHistory:
        """记录工程访问历史"""
        return await self.access_history_dao.create(
            user_id=user_id,
            project_id=project_id
        )

    async def get_recent_projects(self, user_id: str, limit: int = 10) -> List[str]:
        """获取用户最近访问的工程ID列表"""
        from sqlalchemy import select, desc

        stmt = (
            select(ProjectAccessHistory.project_id)
            .where(ProjectAccessHistory.user_id == user_id)
            .order_by(desc(ProjectAccessHistory.accessed_at))
            .distinct()
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        project_ids = [row[0] for row in result.fetchall()]
        return project_ids


class ProjectDAO:
    """工程数据访问对象"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_dao = BaseDAO(Project, db)
        self.member_dao = BaseDAO(ProjectMember, db)

    async def get_user_projects(self, user_id: str) -> List[Project]:
        """获取用户的所有工程（包括拥有的和加入的）"""
        from sqlalchemy import select

        # 获取用户拥有的工程
        stmt_owned = select(Project).where(Project.owner_id == user_id)
        result_owned = await self.db.execute(stmt_owned)
        owned_projects = result_owned.scalars().all()

        # 获取用户加入的工程
        stmt_membered = (
            select(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .where(Project.owner_id != user_id)  # 排除拥有的
        )
        result_membered = await self.db.execute(stmt_membered)
        membered_projects = result_membered.scalars().all()

        return list(owned_projects) + list(membered_projects)

    async def create_project(self, name: str, description: str, owner_id: str) -> Project:
        """创建新工程"""
        project = await self.project_dao.create(
            name=name,
            description=description,
            owner_id=owner_id
        )

        # 创建者自动成为 owner 成员
        await self.add_member(project.id, owner_id, "owner")

        return project

    async def update_project(self, project_id: str, **kwargs) -> Optional[Project]:
        """更新工程信息"""
        return await self.project_dao.update(project_id, **kwargs)

    async def delete_project(self, project_id: str) -> bool:
        """删除工程"""
        return await self.project_dao.delete(project_id)

    async def add_member(self, project_id: str, user_id: str, role: str = "member") -> ProjectMember:
        """添加工程成员"""
        return await self.member_dao.create(
            project_id=project_id,
            user_id=user_id,
            role=role
        )

    async def remove_member(self, project_id: str, user_id: str) -> bool:
        """移除工程成员"""
        return await self.member_dao.delete_by(project_id=project_id, user_id=user_id) > 0

    async def get_members(self, project_id: str) -> List[ProjectMember]:
        """获取工程成员列表"""
        return await self.member_dao.list(project_id=project_id)

    async def is_member(self, project_id: str, user_id: str) -> bool:
        """检查用户是否是工程成员"""
        member = await self.member_dao.get_by(project_id=project_id, user_id=user_id)
        return member is not None

    async def get_member_role(self, project_id: str, user_id: str) -> Optional[str]:
        """获取用户在工程中的角色"""
        member = await self.member_dao.get_by(project_id=project_id, user_id=user_id)
        return member.role if member else None
