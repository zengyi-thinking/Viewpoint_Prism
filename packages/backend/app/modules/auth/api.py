"""
认证模块 API 路由
提供用户注册、登录、登出等 API 端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.modules.auth.service import AuthService, ProjectService
from app.modules.auth.schemas import (
    UserCreate, UserLogin, UserUpdate, UserResponse, TokenResponse, LoginResponse,
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDetailResponse,
    ProjectListResponse, SwitchProjectResponse, ProjectMemberInfo, ChangePassword, MessageResponse
)
from app.modules.auth.dependencies import get_current_user, get_current_user_optional
from app.modules.auth.models import User
from app.models.models import Project

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["认证"])

# 额外的路由器（工程管理）
project_router = APIRouter(prefix="/projects", tags=["工程管理"])

# 导出额外路由器供 RouterRegistry 使用
extra_routers = [project_router]


# ========== 认证相关端点 ==========

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册

    - **username**: 用户名（3-50字符）
    - **email**: 邮箱地址
    - **password**: 密码（至少8位）
    """
    service = AuthService(db)

    try:
        user = await service.register(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码

    返回访问令牌和刷新令牌
    """
    service = AuthService(db)
    project_service = ProjectService(db)

    try:
        user, access_token, refresh_token, access_jti, refresh_jti = await service.login(
            username=user_data.username,
            password=user_data.password
        )

        # 获取用户的默认工程（第一个工程）
        user_projects = await project_service.get_user_projects(user.id)
        current_project = None
        if user_projects:
            # 获取最近访问的工程
            from app.modules.auth.dao import AuthDAO
            auth_dao = AuthDAO(db)
            recent_project_ids = await auth_dao.get_recent_projects(user.id, limit=1)

            if recent_project_ids:
                current_project = await project_service.get_project(recent_project_ids[0])
            else:
                current_project = user_projects[0]

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
            current_project=ProjectResponse.model_validate(current_project) if current_project else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登出

    吊销当前访问令牌
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据"
        )

    from app.modules.auth.security import decode_token
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

    service = AuthService(db)
    jti = payload.get("jti")
    await service.logout(jti)

    return MessageResponse(message="登出成功")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    登出所有设备

    吊销用户的所有会话
    """
    service = AuthService(db)
    count = await service.logout_all(current_user.id)

    return MessageResponse(message=f"已登出 {count} 个设备")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新当前用户信息
    """
    from app.core.base_dao import BaseDAO

    user_dao = BaseDAO(User, db)

    if update_data.email is not None:
        # 检查邮箱是否被其他用户使用
        existing = await user_dao.get_by(email=update_data.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用"
            )

        user = await user_dao.update(current_user.id, email=update_data.email)
        return UserResponse.model_validate(user)

    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改密码

    - **old_password**: 原密码
    - **new_password**: 新密码（至少8位）
    """
    service = AuthService(db)

    try:
        await service.change_password(current_user, password_data.old_password, password_data.new_password)
        return MessageResponse(message="密码修改成功，请重新登录")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌
    """
    from app.modules.auth.security import decode_token

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    service = AuthService(db)
    result = await service.refresh_token(payload.get("jti"))

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已失效或过期"
        )

    access_token, access_jti = result

    # 获取用户信息
    from app.core.base_dao import BaseDAO
    user_dao = BaseDAO(User, db)
    user = await user_dao.get(payload.get("sub"))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user)
    )


# ========== 工程管理端点 ==========

# 注意：project_router 已在文件开头定义，prefix="/projects"
# RouterRegistry 会自动添加 /api 前缀，最终路径为 /api/projects


@project_router.get("", response_model=ProjectListResponse)
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的所有工程
    """
    service = ProjectService(db)
    projects = await service.get_user_projects(current_user.id)

    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=len(projects)
    )


@project_router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新工程

    - **name**: 工程名称（1-100字符）
    - **description**: 工程描述（可选）
    """
    service = ProjectService(db)

    try:
        project = await service.create_project(
            user_id=current_user.id,
            name=project_data.name,
            description=project_data.description or ""
        )
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@project_router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取工程详情
    """
    service = ProjectService(db)

    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工程不存在"
        )

    # 检查权限
    if not await service.dao.is_member(project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此工程"
        )

    # 获取成员列表
    members = await service.dao.get_members(project_id)

    # 获取成员详细信息
    from app.core.base_dao import BaseDAO
    user_dao = BaseDAO(User, db)

    member_infos = []
    for member in members:
        user = await user_dao.get(member.user_id)
        if user:
            member_infos.append(ProjectMemberInfo(
                id=user.id,
                username=user.username,
                email=user.email,
                role=member.role
            ))

    return ProjectDetailResponse(
        **ProjectResponse.model_validate(project).model_dump(),
        members=member_infos
    )


@project_router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新工程信息

    只能更新自己拥有的工程
    """
    service = ProjectService(db)

    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工程不存在"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己拥有的工程"
        )

    try:
        updated = await service.update_project(
            project_id,
            name=project_data.name,
            description=project_data.description
        )
        return ProjectResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@project_router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除工程

    只能删除自己拥有的工程
    """
    service = ProjectService(db)

    try:
        await service.delete_project(project_id, current_user.id)
        return MessageResponse(message="工程已删除")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@project_router.post("/{project_id}/switch", response_model=SwitchProjectResponse)
async def switch_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    切换当前工程

    记录访问历史并返回工程信息
    """
    service = ProjectService(db)

    try:
        project = await service.switch_project(current_user.id, project_id)
        return SwitchProjectResponse(
            current_project=ProjectResponse.model_validate(project)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@project_router.get("/{project_id}/members", response_model=list[ProjectMemberInfo])
async def get_project_members(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取工程成员列表
    """
    service = ProjectService(db)

    # 检查权限
    if not await service.dao.is_member(project_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此工程"
        )

    members = await service.dao.get_members(project_id)

    from app.core.base_dao import BaseDAO
    user_dao = BaseDAO(User, db)

    member_infos = []
    for member in members:
        user = await user_dao.get(member.user_id)
        if user:
            member_infos.append(ProjectMemberInfo(
                id=user.id,
                username=user.username,
                email=user.email,
                role=member.role
            ))

    return member_infos


@project_router.get("/recent/list", response_model=ProjectListResponse)
async def get_recent_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 10
):
    """
    获取最近访问的工程
    """
    service = ProjectService(db)
    projects = await service.get_recent_projects(current_user.id, limit)

    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=len(projects)
    )
