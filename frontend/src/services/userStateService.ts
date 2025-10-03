import { api } from '../utils/api';

export interface UserState {
  preferences: {
    theme: 'light' | 'dark';
    sidebarWidth: number;
    editorFontSize: number;
    [key: string]: any;
  };
  workspace: {
    openDocuments: string[];
    activeDocument: string | null;
    recentFiles: string[];
    [key: string]: any;
  };
  agentSettings: {
    [key: string]: any;
  };
  ui?: {
    [key: string]: any;
  };
}

class UserStateService {
  async getUserState(): Promise<UserState | null> {
    try {
      const response = await api.get<{ state: UserState }>('/auth/state');
      return response.data.state;
    } catch (error) {
      console.error('Failed to load user state:', error);
      return null;
    }
  }

  async saveUserState(state: UserState): Promise<boolean> {
    try {
      await api.put('/auth/state', { state });
      return true;
    } catch (error) {
      console.error('Failed to save user state:', error);
      return false;
    }
  }

  async updateUserPreference(key: string, value: any): Promise<boolean> {
    try {
      await api.put('/auth/preferences', { key, value });
      return true;
    } catch (error) {
      console.error('Failed to update user preference:', error);
      return false;
    }
  }
}

export const userStateService = new UserStateService();