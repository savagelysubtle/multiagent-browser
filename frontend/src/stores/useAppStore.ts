import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { AppState, Document, Task, User } from '../../types';
import { userStateService } from '../services/userStateService';

// Enhanced document types
export type DocumentType = 'markdown' | 'richtext' | 'plaintext' | 'code' | 'json' | 'pdf';
export type EditorMode = 'visual' | 'source' | 'split';

// Enhanced document interface
export interface EnhancedDocument extends Document {
  documentType: DocumentType;
  editorMode?: EditorMode;
  language?: string; // For code files
  version?: number;
  lastSaved?: string;
  isDirty?: boolean; // Has unsaved changes
  collaborators?: string[]; // User IDs of active collaborators
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // User state
      user: null,

      // UI state
      theme: 'dark',
      sidebarCollapsed: false,
      activeView: 'editor',

      // Enhanced document state
      openDocuments: [],
      activeDocument: null,
      documentCache: new Map(),
      documentTypes: ['markdown', 'richtext', 'plaintext', 'code', 'json'] as DocumentType[],
      supportedLanguages: ['javascript', 'typescript', 'python', 'html', 'css', 'json', 'yaml', 'xml'],

      // Enhanced editor settings
      editorSettings: {
        fontSize: 14,
        fontFamily: 'JetBrains Mono, Consolas, monospace',
        lineHeight: 1.6,
        wordWrap: true,
        minimap: true,
        autoSave: true,
        autoSaveDelay: 1000,
        showLineNumbers: true,
        highlightCurrentLine: true,
        theme: 'vs-dark',
      },

      // Agent state
      activeTasks: [],
      taskHistory: [],
      selectedAgent: 'document_editor',

      // WebSocket state
      connectionStatus: 'disconnected',

      // Actions
      setUser: (user: User | null) => {
        set({ user });
      },

      // Enhanced document actions
      createDocument: (type: DocumentType, name: string, content: string = '') => {
        const doc: EnhancedDocument = {
          id: `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name,
          title: name,
          content,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          user_id: get().user?.id || 'anonymous',
          url: '',
          file: new File([content], name, { type: getFileTypeFromDocumentType(type) }),
          documentType: type,
          version: 1,
          isDirty: false,
          collaborators: [],
        };

        set((state) => ({
          openDocuments: [...state.openDocuments, doc],
          documentCache: new Map(state.documentCache).set(doc.id, doc),
          activeDocument: doc.id,
        }));

        return doc;
      },

      updateEditorSettings: (settings: Partial<AppState['editorSettings']>) => {
        set((state) => ({
          editorSettings: { ...state.editorSettings, ...settings }
        }));
      },

      markDocumentDirty: (id: string, isDirty: boolean = true) => {
        set((state) => {
          const updatedDocuments = state.openDocuments.map((doc) =>
            doc.id === id ? { ...doc, isDirty } as EnhancedDocument : doc
          );
          const updatedCache = new Map(state.documentCache);
          const existingDoc = updatedCache.get(id) as EnhancedDocument;
          if (existingDoc) {
            updatedCache.set(id, { ...existingDoc, isDirty });
          }

          return {
            openDocuments: updatedDocuments,
            documentCache: updatedCache,
          };
        });
      },

      setDocumentEditorMode: (id: string, mode: EditorMode) => {
        set((state) => {
          const updatedDocuments = state.openDocuments.map((doc) =>
            doc.id === id ? { ...doc, editorMode: mode } as EnhancedDocument : doc
          );
          return { openDocuments: updatedDocuments };
        });
      },

      setSelectedAgent: (agentType: string) => {
        set({ selectedAgent: agentType });
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
        const enhancedDoc: EnhancedDocument = {
          ...doc,
          documentType: detectDocumentType(doc.name),
          isDirty: false,
          version: 1,
          collaborators: [],
        };

        set((state) => ({
          openDocuments: [...state.openDocuments, enhancedDoc],
          documentCache: new Map(state.documentCache).set(enhancedDoc.id, enhancedDoc),
        }));
      },

      updateDocument: (id: string, updates: Partial<Document>) => {
        const enhancedUpdates = {
          ...updates,
          updated_at: new Date().toISOString(),
        };

        set((state) => {
          const updatedDocuments = state.openDocuments.map((doc) =>
            doc.id === id ? { ...doc, ...enhancedUpdates } : doc
          );
          const updatedCache = new Map(state.documentCache);
          const existingDoc = updatedCache.get(id);
          if (existingDoc) {
            updatedCache.set(id, { ...existingDoc, ...enhancedUpdates });
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
        editorSettings: state.editorSettings,
      }),
    }
  )
);

// Helper functions
function getFileTypeFromDocumentType(type: DocumentType): string {
  const typeMap: Record<DocumentType, string> = {
    markdown: 'text/markdown',
    richtext: 'text/html',
    plaintext: 'text/plain',
    code: 'text/plain',
    json: 'application/json',
    pdf: 'application/pdf',
  };
  return typeMap[type] || 'text/plain';
}

function detectDocumentType(filename: string): DocumentType {
  const ext = filename.split('.').pop()?.toLowerCase();
  const extMap: Record<string, DocumentType> = {
    md: 'markdown',
    markdown: 'markdown',
    html: 'richtext',
    htm: 'richtext',
    txt: 'plaintext',
    js: 'code',
    ts: 'code',
    jsx: 'code',
    tsx: 'code',
    py: 'code',
    css: 'code',
    scss: 'code',
    json: 'json',
    yaml: 'code',
    yml: 'code',
    xml: 'code',
    pdf: 'pdf',
  };
  return extMap[ext || ''] || 'plaintext';
}

// Initialize theme on store creation
const initializeTheme = () => {
  const state = useAppStore.getState();
  document.documentElement.classList.add(state.theme);
};

// Call initialization
if (typeof window !== 'undefined') {
  initializeTheme();
}