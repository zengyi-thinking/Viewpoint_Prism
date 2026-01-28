"""
认证服务层
提供用户注册、登录、登出等业务逻辑
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dao import AuthDAO, ProjectDAO
from app.modules.auth.models import User
from app.models.models import Project
from app.modules.auth.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.core.config import get_settings

settings = get_settings()


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dao = AuthDAO(db)

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "user"
    ) -> User:
        """
        用户注册

        返回创建的用户对象
        """
        # 检查用户名是否已存在
        existing_user = await self.dao.get_user_by_username(username)
        if existing_user:
            raise ValueError("用户名已存在")

        # 检查邮箱是否已存在
        existing_email = await self.dao.get_user_by_email(email)
        if existing_email:
            raise ValueError("邮箱已被使用")

        # 验证密码强度
        self._validate_password(password)

        # 创建密码哈希
        password_hash = get_password_hash(password)

        # 创建用户
        user = await self.dao.create_user(username, email, password_hash, role)

        return user

    async def login(self, username: str, password: str) -> Tuple[User, str, str, str, str]:
        """
        用户登录

        返回: (user, access_token, refresh_token, access_jti, refresh_jti)
        """
        # 获取用户
        user = await self.dao.get_user_by_username(username)
        if not user:
            raise ValueError("用户名或密码错误")

        # 验证密码
        if not verify_password(password, user.password_hash):
            raise ValueError("用户名或密码错误")

        # 检查用户是否激活
        if not user.is_active:
            raise ValueError("用户已被禁用")

        # 生成 Token
        access_token, access_jti = create_access_token(
            data={"sub": user.id, "username": user.username},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )

        refresh_token, refresh_jti = create_refresh_token(
            data={"sub": user.id},
            expires_delta=timedelta(days=7)
        )

        # 保存会话到数据库
        access_expires_at = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        refresh_expires_at = datetime.utcnow() + timedelta(days=7)

        await self.dao.create_session(
            user_id=user.id,
            token_jti=access_jti,
            expires_at=access_expires_at,
            refresh_token_jti=refresh_jti,
            refresh_expires_at=refresh_expires_at
        )

        # 更新最后登录时间
        await self.dao.update_last_login(user.id)

        return user, access_token, refresh_token, access_jti, refresh_jti

    async def logout(self, token_jti: str) -> bool:
        """
        用户登出

        吊销当前会话
        """
        return await self.dao.revoke_session(token_jti)

    async def logout_all(self, user_id: str) -> int:
        """
        登出所有设备

        吊销用户所有会话，返回吊销的会话数
        """
        return await self.dao.revoke_all_user_sessions(user_id)

    async def refresh_token(self, refresh_jti: str) -> Optional[Tuple[str, str]]:
        """
        刷新访问令牌

        返回: (new_access_token, new_access_jti) 或 None
        """
        # 获取刷新令牌对应的会话
        session = await self.dao.session_dao.get_by(refresh_token_jti=refresh_jti)
        if not session or session.is_revoked:
            return None

        # 检查是否过期
        if session.refresh_expires_at and session.refresh_expires_at < datetime.utcnow():
            return None

        # 吊销旧的访问令牌
        await self.dao.revoke_session(session.token_jti)

        # 生成新的访问令牌
        access_token, access_jti = create_access_token(
            data={"sub": session.user_id},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )

        # 更新会话
        access_expires_at = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

        await self.dao.session_dao.update(
            session.id,
            token_jti=access_jti,
            expires_at=access_expires_at
        )

        return access_token, access_jti

    async def change_password(self, user: User, old_password: str, new_password: str) -> bool:
        """
        修改密码
        """
        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            raise ValueError("原密码错误")

        # 验证新密码强度
        self._validate_password(new_password)

        # 更新密码
        new_password_hash = get_password_hash(new_password)
        await self.dao.user_dao.update(user.id, password_hash=new_password_hash)

        # 吊销所有会话（强制重新登录）
        await self.dao.revoke_all_user_sessions(user.id)

        return True

    def _validate_password(self, password: str) -> None:
        """验证密码强度"""
        if len(password) < 8:
            raise ValueError("密码长度至少8位")

        # 可以添加更多密码强度规则
        # 例如：必须包含大小写字母、数字、特殊字符等


class ProjectService:
    """工程管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dao = ProjectDAO(db)
        self.auth_dao = AuthDAO(db)

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str = ""
    ) -> Project:
        """创建新工程"""
        if len(name) > 100:
            raise ValueError("工程名称不能超过100个字符")

        project = await self.dao.create_project(name, description, user_id)

        # 记录访问历史
        await self.auth_dao.record_access_history(user_id, project.id)

        return project

    async def get_user_projects(self, user_id: str) -> list[Project]:
        """获取用户的所有工程"""
        return await self.dao.get_user_projects(user_id)

    async def get_project(self, project_id: str) -> Optional[Project]:
        """获取工程详情"""
        return await self.dao.project_dao.get(project_id)

    async def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Project]:
        """更新工程信息"""
        update_data = {}
        if name is not None:
            if len(name) > 100:
                raise ValueError("工程名称不能超过100个字符")
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description

        return await self.dao.update_project(project_id, **update_data)

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """删除工程（只能删除自己拥有的）"""
        project = await self.dao.project_dao.get(project_id)
        if not project:
            raise ValueError("工程不存在")

        if project.owner_id != user_id:
            raise ValueError("只能删除自己拥有的工程")

        return await self.dao.delete_project(project_id)

    async def switch_project(self, user_id: str, project_id: str) -> Project:
        """切换当前工程"""
        # 验证工程存在且用户有权限
        project = await self.dao.project_dao.get(project_id)
        if not project:
            raise ValueError("工程不存在")

        if not await self.dao.is_member(project_id, user_id):
            raise ValueError("无权访问此工程")

        # 记录访问历史
        await self.auth_dao.record_access_history(user_id, project_id)

        return project

    async def add_project_member(
        self,
        project_id: str,
        user_id: str,
        new_member_id: str,
        requester_id: str,
        role: str = "member"
    ) -> None:
        """添加工程成员"""
        # 验证请求者权限
        requester_role = await self.dao.get_member_role(project_id, requester_id)
        if requester_role not in ["owner", "admin"]:
            raise ValueError("只有管理员可以添加成员")

        # 检查是否已经是成员
        if await self.dao.is_member(project_id, new_member_id):
            raise ValueError("用户已经是工程成员")

        await self.dao.add_member(project_id, new_member_id, role)

    async def remove_project_member(
        self,
        project_id: str,
        member_id: str,
        requester_id: str
    ) -> None:
        """移除工程成员"""
        # 验证请求者权限
        requester_role = await self.dao.get_member_role(project_id, requester_id)
        if requester_role not in ["owner", "admin"]:
            raise ValueError("只有管理员可以移除成员")

        # 不能移除工程拥有者
        project = await self.dao.project_dao.get(project_id)
        if project.owner_id == member_id:
            raise ValueError("不能移除工程拥有者")

        await self.dao.remove_member(project_id, member_id)

    async def get_recent_projects(self, user_id: str, limit: int = 10) -> list[Project]:
        """获取最近访问的工程"""
        project_ids = await self.auth_dao.get_recent_projects(user_id, limit)

        projects = []
        for pid in project_ids:
            project = await self.dao.project_dao.get(pid)
            if project:
                projects.append(project)

        return projects
