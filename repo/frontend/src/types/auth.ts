export type AppRole =
  | 'student'
  | 'employer_manager'
  | 'content_author'
  | 'reviewer'
  | 'system_administrator'

export interface AuthUser {
  id: string
  email: string
  first_name: string | null
  last_name: string | null
  display_name: string | null
  role: AppRole | null
  created_at: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  username: string
  password: string
}

export interface AuthResponse {
  user: AuthUser
  access_token_expires_at: string
  refresh_token_expires_at: string
  token_type: string
}
