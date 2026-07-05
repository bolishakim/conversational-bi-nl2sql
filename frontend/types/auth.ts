// Auth and User types
export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin?: boolean;
  role: 'admin' | 'participant_control' | 'participant_experimental';
  can_access_chatbot: boolean;
  can_access_dashboards: boolean;
  can_access_admin: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
