import { AuthResponse, LoginRequest, RegisterRequest, User } from '../../types';
import { api } from '../utils/api';

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
  private baseURL = '/api';  // Let the proxy handle the backend URL
  private tokenKey = 'auth_token';

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    console.log('Login attempt - API URL:', api.defaults.baseURL);
    console.log('Login attempt - Credentials:', { email: credentials.email, password: '***' });

    const response = await api.post<AuthResponse>('/auth/login', credentials);
    const { access_token, user } = response.data;

    // Store token
    localStorage.setItem(this.tokenKey, access_token);

    console.log('Login successful, token stored:', access_token.substring(0, 20) + '...');

    return response.data;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/register', userData);
    const { access_token, user } = response.data;

    // Store token
    localStorage.setItem(this.tokenKey, access_token);

    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
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
      const response = await api.get<UserMeResponse>('/auth/me');
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
        const stateResponse = await api.get<{ state: any }>('/auth/state');
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
      const response = await api.post<{ access_token: string }>('/auth/refresh');
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
    await api.put('/auth/preferences', { preferences });
  }

  async updateUserState(state: Record<string, any>): Promise<void> {
    await api.put('/auth/state', { state });
  }
}

export const authService = new AuthService();