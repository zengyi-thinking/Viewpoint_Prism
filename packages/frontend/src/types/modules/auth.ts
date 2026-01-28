/**
 * 认证模块类型定义
 * 包含用户、工程、认证相关类型
 */

/**
 * 用户角色
 */
export type UserRole = 'user' | 'admin';

/**
 * 工程成员角色
 */
export type ProjectMemberRole = 'owner' | 'admin' | 'member' | 'viewer';

/**
 * 用户信息
 */
export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

/**
 * 用户创建请求
 */
export interface UserCreate {
  username: string;
  email: string;
  password: string;
}

/**
 * 用户登录请求
 */
export interface UserLogin {
  username: string;
  password: string;
}

/**
 * 用户更新请求
 */
export interface UserUpdate {
  email?: string;
}

/**
 * 修改密码请求
 */
export interface ChangePassword {
  old_password: string;
  new_password: string;
}

/**
 * Token 响应
 */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: User;
}

/**
 * 登录响应
 */
export interface LoginResponse extends TokenResponse {
  current_project: Project | null;
}

/**
 * 工程信息
 */
export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  member_count: number;
}

/**
 * 工程创建请求
 */
export interface ProjectCreate {
  name: string;
  description?: string;
}

/**
 * 工程更新请求
 */
export interface ProjectUpdate {
  name?: string;
  description?: string;
}

/**
 * 工程成员信息
 */
export interface ProjectMember {
  id: string;
  username: string;
  email: string;
  role: ProjectMemberRole;
}

/**
 * 工程详情（包含成员列表）
 */
export interface ProjectDetail extends Project {
  members: ProjectMember[];
}

/**
 * 工程列表响应
 */
export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

/**
 * 切换工程响应
 */
export interface SwitchProjectResponse {
  current_project: Project;
}

/**
 * 认证状态
 */
export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  currentProject: Project | null;
  projects: Project[];
}

/**
 * 认证动作
 */
export interface AuthActions {
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setRefreshToken: (token: string | null) => void;
  setCurrentProject: (project: Project | null) => void;
  setProjects: (projects: Project[]) => void;
  login: (credentials: UserLogin) => Promise<LoginResponse>;
  register: (userData: UserCreate) => Promise<User>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  loadProjects: () => Promise<void>;
  switchProject: (projectId: string) => Promise<void>;
}
