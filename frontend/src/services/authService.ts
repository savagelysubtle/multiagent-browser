import { api } from '../utils/api';
import { User, LoginRequest, RegisterRequest, AuthResponse } from '../../types';

// Backend user response format (without state)
interface UserMeResponse {
  id: string;
  email: string;
  name?: string;
  picture?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

class AuthService {
  private tokenKey = 'auth_token';

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/api/auth/login', credentials);
    const { access_token, user } = response.data;

    // Store token
    localStorage.setItem(this.tokenKey, access_token);

    return response.data;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/api/auth/register', userData);
    const { access_token, user } = response.data;

    // Store token
    localStorage.setItem(this.tokenKey, access_token);

    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await api.post('/api/auth/logout');
    } catch (error) {
      // Continue with logout even if server request fails
      console.warn('Logout request failed:', error);
    } finally {
      // Always clear local storage
      localStorage.removeItem(this.tokenKey);
    }
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await api.get<UserMeResponse>('/api/auth/me');
      const userData = response.data;

      // Convert to our User type format (without state initially)
      const user: User = {
        id: userData.id,
        email: userData.email,
        name: userData.name,
        picture: userData.picture,
        is_active: userData.is_active,
        created_at: userData.created_at,
      };

      return user;
    } catch (error) {
      // Clear invalid token
      localStorage.removeItem(this.tokenKey);
      return null;
    }
  }

  async getCurrentUserWithState(): Promise<User | null> {
    try {
      // Get basic user data
      const user = await this.getCurrentUser();
      if (!user) return null;

      // Get user state separately
      try {
        const stateResponse = await api.get<{ state: any }>('/api/auth/state');
        user.state = stateResponse.data.state;
      } catch (stateError) {
        // State is optional, continue without it
        console.warn('Failed to load user state:', stateError);
      }

      return user;
    } catch (error) {
      return null;
    }
  }

  async verifyToken(token: string): Promise<User | null> {
    try {
      // Temporarily set token for verification
      const originalToken = localStorage.getItem(this.tokenKey);
      localStorage.setItem(this.tokenKey, token);

      const user = await this.getCurrentUser();

      // Restore original token if verification failed
      if (!user && originalToken) {
        localStorage.setItem(this.tokenKey, originalToken);
      }

      return user;
    } catch (error) {
      return null;
    }
  }

  async refreshToken(): Promise<string | null> {
    try {
      const response = await api.post<{ access_token: string }>('/api/auth/refresh');
      const { access_token } = response.data;

      localStorage.setItem(this.tokenKey, access_token);
      return access_token;
    } catch (error) {
      localStorage.removeItem(this.tokenKey);
      return null;
    }
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  async updateUserPreferences(preferences: Record<string, any>): Promise<void> {
    await api.put('/api/auth/preferences', { preferences });
  }

  async updateUserState(state: Record<string, any>): Promise<void> {
    await api.put('/api/auth/state', { state });
  }
}

export const authService = new AuthService();