import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { AppState, User, Document, Task } from '../../types';
import { userStateService } from '../services/userStateService';

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // User state
      user: null,

      // UI state
      theme: 'dark',
      sidebarCollapsed: false,
      activeView: 'editor',

      // Document state
      openDocuments: [],
      activeDocument: null,
      documentCache: new Map(),

      // Agent state
      activeTasks: [],
      taskHistory: [],

      // WebSocket state
      connectionStatus: 'disconnected',

      // Actions
      setUser: (user: User | null) => {
        set({ user });
      },

      setTheme: (theme: 'light' | 'dark') => {
        set({ theme });
        // Apply theme to document root
        document.documentElement.classList.remove('light', 'dark');
        document.documentElement.classList.add(theme);
      },

      setSidebarCollapsed: (collapsed: boolean) => {
        set({ sidebarCollapsed: collapsed });
      },

      setActiveView: (view: 'editor' | 'chat' | 'tasks' | 'settings') => {
        set({ activeView: view });
      },

      addDocument: (doc: Document) => {
        set((state) => ({
          openDocuments: [...state.openDocuments, doc],
          documentCache: new Map(state.documentCache).set(doc.id, doc),
        }));
      },

      updateDocument: (id: string, updates: Partial<Document>) => {
        set((state) => {
          const updatedDocuments = state.openDocuments.map((doc) =>
            doc.id === id ? { ...doc, ...updates } : doc
          );
          const updatedCache = new Map(state.documentCache);
          const existingDoc = updatedCache.get(id);
          if (existingDoc) {
            updatedCache.set(id, { ...existingDoc, ...updates });
          }

          return {
            openDocuments: updatedDocuments,
            documentCache: updatedCache,
          };
        });
      },

      removeDocument: (id: string) => {
        set((state) => {
          const filteredDocuments = state.openDocuments.filter((doc) => doc.id !== id);
          const updatedCache = new Map(state.documentCache);
          updatedCache.delete(id);

          return {
            openDocuments: filteredDocuments,
            documentCache: updatedCache,
            activeDocument: state.activeDocument === id ? null : state.activeDocument,
          };
        });
      },

      setActiveDocument: (id: string | null) => {
        set({ activeDocument: id });
      },

      addTask: (task: Task) => {
        set((state) => ({
          activeTasks: [...state.activeTasks, task],
          taskHistory: [task, ...state.taskHistory.slice(0, 99)], // Keep last 100
        }));
      },

      updateTask: (id: string, updates: Partial<Task>) => {
        set((state) => {
          const updatedActiveTasks = state.activeTasks.map((task) =>
            task.id === id ? { ...task, ...updates } : task
          );

          const updatedTaskHistory = state.taskHistory.map((task) =>
            task.id === id ? { ...task, ...updates } : task
          );

          // Remove completed/failed tasks from active list
          const filteredActiveTasks = updatedActiveTasks.filter(
            (task) => task.status === 'pending' || task.status === 'running'
          );

          return {
            activeTasks: filteredActiveTasks,
            taskHistory: updatedTaskHistory,
          };
        });
      },

      setConnectionStatus: (status: 'connected' | 'disconnected' | 'reconnecting') => {
        set({ connectionStatus: status });
      },

      saveStateToBackend: async () => {
        const state = get();
        if (!state.user) return;

        try {
          const userState = {
            preferences: {
              theme: state.theme,
              sidebarWidth: state.sidebarCollapsed ? 64 : 250,
              editorFontSize: 14,
            },
            workspace: {
              openDocuments: state.openDocuments.map(doc => doc.id),
              activeDocument: state.activeDocument,
              recentFiles: [],
            },
            agentSettings: {},
          };

          await userStateService.saveUserState(userState);
        } catch (error) {
          console.error('Failed to save state:', error);
        }
      },

      loadStateFromBackend: async () => {
        const state = get();
        if (!state.user) return;

        try {
          const userState = await userStateService.getUserState();
          if (userState) {
            // Apply loaded preferences to current state
            if (userState.preferences) {
              if (userState.preferences.theme) {
                get().setTheme(userState.preferences.theme);
              }
              if (typeof userState.preferences.sidebarWidth === 'number') {
                get().setSidebarCollapsed(userState.preferences.sidebarWidth <= 64);
              }
            }
          }
        } catch (error) {
          console.error('Failed to load state:', error);
        }
      },
    }),
    {
      name: 'app-state',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist non-sensitive UI preferences locally
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        activeView: state.activeView,
      }),
    }
  )
);

// Initialize theme on store creation
const initializeTheme = () => {
  const state = useAppStore.getState();
  document.documentElement.classList.add(state.theme);
};

// Call initialization
if (typeof window !== 'undefined') {
  initializeTheme();
}