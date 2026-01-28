"""
认证模块 Pydantic 模型
定义请求和响应的数据结构
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


# ========== 用户相关 Schema ==========

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """用户注册请求"""
    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """用户更新请求"""
    email: Optional[EmailStr] = None


class ChangePassword(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Token 相关 Schema ==========

class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒
    user: UserResponse


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    current_project: Optional['ProjectResponse'] = None


# ========== 工程相关 Schema ==========

class ProjectBase(BaseModel):
    """工程基础模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """创建工程请求"""
    pass


class ProjectUpdate(BaseModel):
    """更新工程请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectMemberInfo(BaseModel):
    """工程成员信息"""
    id: str
    username: str
    email: str
    role: str  # 在工程中的角色

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    """工程响应"""
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """工程详情响应"""
    members: List[ProjectMemberInfo] = []


class ProjectListResponse(BaseModel):
    """工程列表响应"""
    projects: List[ProjectResponse]
    total: int


class SwitchProjectResponse(BaseModel):
    """切换工程响应"""
    current_project: ProjectResponse


# ========== 通用响应 Schema ==========

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True
