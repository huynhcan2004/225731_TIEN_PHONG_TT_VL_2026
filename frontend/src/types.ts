// frontend/src/types.ts

export interface User {
  id: string;
  username: string;
  email: string;
  avatar_url: string;
  token_balance: number;
  is_premium: boolean;
  role: 'admin' | 'user' | string; 
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}