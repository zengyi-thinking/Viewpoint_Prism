"""
认证模块
提供用户注册、登录、会话管理等功能
"""

from app.modules.auth.models import User, ProjectMember, ProjectAccessHistory, UserSession
# Project 模型定义在 app.models.models 中，通过循环导入处理
# from app.models.models import Project  # 在需要时动态导入

__all__ = [
    "User",
    "ProjectMember",
    "ProjectAccessHistory",
    "UserSession",
]
