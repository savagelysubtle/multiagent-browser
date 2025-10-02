import { CopilotChat } from '@copilotkit/react-ui';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, FileText, Plus, RefreshCw, Search, Upload } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { EditorPanel } from '../components/EditorPanel';
import { DocumentType, EnhancedDocument, useAppStore } from '../stores/useAppStore';
import { Document } from '../types';

interface SupportedDocumentType {
  type: string;
  extensions: string[];
}

export default function EditorView() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [documentContent, setDocumentContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [newDocumentTitle, setNewDocumentTitle] = useState('');
  const [newDocumentType, setNewDocumentType] = useState<DocumentType>('markdown');
  const [isChatPanelOpen, setIsChatPanelOpen] = useState(true);
  const [explorerWidth, setExplorerWidth] = useState(256);
  const [chatWidth, setChatWidth] = useState(320);
  const [isResizingExplorer, setIsResizingExplorer] = useState(false);
  const [isResizingChat, setIsResizingChat] = useState(false);
  const [supportedTypes, setSupportedTypes] = useState<SupportedDocumentType[]>([]);

  const containerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { editorSettings } = useAppStore();
  const queryClient = useQueryClient();

  // Fetch supported document types
  useEffect(() => {
    // Add default types as fallback
    const defaultTypes: SupportedDocumentType[] = [
      { type: 'markdown', extensions: ['.md', '.markdown'] },
      { type: 'plaintext', extensions: ['.txt'] },
      { type: 'richtext', extensions: ['.html', '.htm'] },
      { type: 'code', extensions: ['.js', '.ts', '.py', '.css'] },
      { type: 'json', extensions: ['.json'] }
    ];
    setSupportedTypes(defaultTypes);

    // Try to fetch from backend (update port to match your backend)
    fetch('http://127.0.0.1:8000/api/documents/types')
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data: { document_types?: SupportedDocumentType[] }) => {
        if (data.document_types && data.document_types.length > 0) {
          setSupportedTypes(data.document_types);
        }
      })
      .catch(error => {
        console.warn('Could not fetch document types from backend:', error);
        // Keep default types on error
      });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // Handle mouse move for resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingExplorer && containerRef.current) {
        const newWidth = e.clientX - containerRef.current.getBoundingClientRect().left;
        setExplorerWidth(Math.max(200, Math.min(400, newWidth)));
      } else if (isResizingChat && containerRef.current) {
        const containerRight = containerRef.current.getBoundingClientRect().right;
        const newWidth = containerRight - e.clientX;
        setChatWidth(Math.max(280, Math.min(600, newWidth)));
      }
    };

    const handleMouseUp = () => {
      setIsResizingExplorer(false);
      setIsResizingChat(false);
    };

    if (isResizingExplorer || isResizingChat) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizingExplorer, isResizingChat]);

  // Fetch documents from backend
  const { data: documents, isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: async (): Promise<EnhancedDocument[]> => {
      const token = localStorage.getItem('token');
      const response = await fetch('http://127.0.0.1:8000/api/documents/', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }

      const data = await response.json();
      return data.documents.map((doc: any) => ({
        id: doc.id,
        name: doc.name,
        title: doc.metadata?.title || doc.name,
        content: doc.content,
        created_at: doc.created_at,
        updated_at: doc.updated_at,
        user_id: doc.metadata?.owner_id || '',
        url: '',
        file: new File([doc.content], doc.name, { type: 'text/plain' }),
        documentType: doc.metadata?.document_type || 'plaintext',
        version: doc.metadata?.version || 1,
        isDirty: false,
      })) as EnhancedDocument[];
    },
  });

  // Create document mutation using user document service
  const createDocumentMutation = useMutation({
    mutationFn: async (data: { title: string; content: string; type: DocumentType }) => {
      const token = localStorage.getItem('token');

      // First try the new user document service
      const userDocResponse = await fetch('http://127.0.0.1:8000/api/user-documents/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({
          template_id: 'blank_document',
          title: data.title
        })
      });

      if (userDocResponse.ok) {
        const userDocResult = await userDocResponse.json();
        if (userDocResult.success) {
          // Now store in the main documents collection
          const response = await fetch('http://127.0.0.1:8000/api/documents/create-live', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token ? `Bearer ${token}` : '',
            },
            body: JSON.stringify({
              title: data.title,
              content: userDocResult.document.content,
              document_type: data.type,
              metadata: {
                created_from_template: userDocResult.document.template_used,
                user_document_service: true
              }
            })
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create document');
          }

          return response.json();
        }
      }

      // Fallback to original method
      const response = await fetch('http://127.0.0.1:8000/api/documents/create-live', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({
          title: data.title,
          content: data.content,
          document_type: data.type,
          metadata: {}
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create document');
      }

      return response.json();
    },
    onSuccess: (document) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setShowCreateModal(false);
      setNewDocumentTitle('');
      setNewDocumentType('markdown');

      // Select the newly created document
      const newDoc: Document = {
        id: document.id,
        name: document.title,
        title: document.title,
        content: document.content,
        created_at: document.created_at,
        updated_at: document.updated_at,
        user_id: document.owner_id || '',
        url: '',
        file: new File([document.content], document.title, { type: 'text/markdown' })
      };

      setSelectedDocument(newDoc);
      setDocumentContent(document.content);
    },
    onError: (error: Error) => {
      console.error('Error creating document:', error);
    }
  });

  // Upload document mutation
  const uploadDocumentMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', 'auto-detect');

      const token = localStorage.getItem('token');
      const response = await fetch('http://127.0.0.1:8000/api/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to upload document');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setShowUploadModal(false);
    },
    onError: (error: Error) => {
      console.error('Error uploading document:', error);
    }
  });

  const handleCreateDocument = useCallback(() => {
    if (newDocumentTitle.trim()) {
      const templateContent = getTemplateContent(newDocumentType, newDocumentTitle);
      createDocumentMutation.mutate({
        title: newDocumentTitle,
        content: templateContent,
        type: newDocumentType,
      });
    }
  }, [newDocumentTitle, newDocumentType, createDocumentMutation]);

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadDocumentMutation.mutate(file);
    }
  }, [uploadDocumentMutation]);

  const handleDocumentContentChange = useCallback(async (id: string, content: string) => {
    setDocumentContent(content);

    // Auto-save functionality with debouncing
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`http://127.0.0.1:8000/api/documents/edit-live/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : '',
          },
          body: JSON.stringify({
            content: content,
            title: selectedDocument?.title,
            metadata: {}
          })
        });

        if (!response.ok) {
          throw new Error('Failed to save document');
        }

        console.log('Document saved');
      } catch (error) {
        console.error('Error saving document:', error);
      }
    }, editorSettings.autoSaveDelay);
  }, [selectedDocument?.title, editorSettings.autoSaveDelay]);

  // Filter documents based on search
  const filteredDocuments = documents?.filter(doc =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div ref={containerRef} className="h-full flex bg-[#1e1e1e]">
      {/* Left Section - Document List */}
      <div
        className="bg-[#252526] border-r border-[#3e3e42] flex flex-col flex-shrink-0 relative"
        style={{ width: `${explorerWidth}px` }}
      >
        {/* Header */}
        <div className="p-3 border-b border-[#3e3e42]">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
              Explorer
            </h2>
            <div className="flex gap-1">
              <button
                onClick={() => setShowCreateModal(true)}
                className="p-1 text-gray-400 hover:text-gray-200 hover:bg-[#2a2d2e] rounded"
                title="Create new document"
              >
                <Plus className="h-4 w-4" />
              </button>
              <button
                onClick={() => setShowUploadModal(true)}
                className="p-1 text-gray-400 hover:text-gray-200 hover:bg-[#2a2d2e] rounded"
                title="Upload document"
              >
                <Upload className="h-4 w-4" />
              </button>
              <button
                onClick={() => refetch()}
                className="p-1 text-gray-400 hover:text-gray-200 hover:bg-[#2a2d2e] rounded"
                title="Refresh documents"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search files..."
              className="w-full px-2 py-1 pl-7 bg-[#3c3c3c] border border-[#3e3e42] rounded text-xs text-gray-300 placeholder-gray-500 focus:outline-none focus:border-[#007acc]"
            />
            <Search className="h-3 w-3 text-gray-500 absolute left-2 top-1/2 transform -translate-y-1/2" />
          </div>
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center text-gray-500 text-xs">
              Loading documents...
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <FileText className="h-8 w-8 mx-auto mb-2 text-gray-600" />
              <p className="text-xs">
                {searchQuery ? 'No documents match your search' : 'No documents yet'}
              </p>
            </div>
          ) : (
            <div className="p-1">
              {filteredDocuments.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => {
                    setSelectedDocument(doc);
                    setDocumentContent(doc.content);
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                    selectedDocument?.id === doc.id
                      ? 'bg-[#094771] text-white'
                      : 'text-gray-300 hover:bg-[#2a2d2e]'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <FileText className="h-3 w-3 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{doc.title || doc.name}</div>
                      <div className="text-xs text-gray-500 truncate">
                        {(doc as EnhancedDocument).documentType} • v{(doc as EnhancedDocument).version || 1}
                        {(doc as EnhancedDocument).isDirty && <span className="text-orange-400 ml-1">●</span>}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Resize handle for explorer */}
        <div
          className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-[#007acc] transition-colors"
          onMouseDown={() => setIsResizingExplorer(true)}
        />
      </div>

      {/* Main Editor Area */}
      <div className="flex-1 flex flex-col bg-[#1e1e1e] relative">
        {selectedDocument ? (
          <EditorPanel
            item={{
              ...selectedDocument,
              type: 'document' as const,
              url: selectedDocument.url || '#',
              file: selectedDocument.file || new File([selectedDocument.content], selectedDocument.name, {
                type: 'text/plain'
              })
            }}
            onContentChange={handleDocumentContentChange}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <FileText className="h-16 w-16 text-gray-700 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-400 mb-2">
                No document selected
              </h3>
              <p className="text-gray-500 mb-4 text-sm">
                Choose a document from the explorer or create a new one
              </p>
              <div className="flex gap-2 justify-center">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center px-4 py-2 bg-[#0e639c] text-white rounded hover:bg-[#1177bb] text-sm"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create New Document
                </button>
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="inline-flex items-center px-4 py-2 bg-[#2a2d2e] text-white rounded hover:bg-[#3e3e42] text-sm border border-[#3e3e42]"
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Document
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Chat Panel Toggle Button - Only show when collapsed */}
      {!isChatPanelOpen && (
        <button
          onClick={() => setIsChatPanelOpen(true)}
          className="absolute right-0 top-1/2 transform -translate-y-1/2 z-10 bg-[#2a2d2e] hover:bg-[#3e3e42] text-gray-400 hover:text-gray-200 p-2 rounded-l-md border-l border-t border-b border-[#3e3e42] transition-all duration-200"
          title="Show chat"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      )}

      {/* Right Sidebar - Chat Panel */}
      <div
        className={`border-l border-[#3e3e42] flex-shrink-0 transition-all duration-300 ease-in-out relative ${
          isChatPanelOpen ? '' : 'w-0'
        }`}
        style={{ width: isChatPanelOpen ? `${chatWidth}px` : '0' }}
      >
        {isChatPanelOpen && (
          <>
            {/* Close button inside chat panel */}
            <button
              onClick={() => setIsChatPanelOpen(false)}
              className="absolute left-2 top-3 z-10 p-1 text-gray-400 hover:text-gray-200 hover:bg-[#2a2d2e] rounded"
              title="Hide chat"
            >
              <ChevronRight className="h-4 w-4" />
            </button>

            {/* Resize handle for chat */}
            <div
              className="absolute top-0 left-0 w-1 h-full cursor-col-resize hover:bg-[#007acc] transition-colors"
              onMouseDown={() => setIsResizingChat(true)}
            />

            <div className="h-full">
              <CopilotChat
                labels={{
                  title: "AI Assistant",
                  initialMessage: "Hello! I can help you with document editing, web browsing, and research tasks. What would you like to do?",
                }}
              />
            </div>
          </>
        )}
      </div>

      {/* Create Document Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-[#252526] rounded-lg shadow-xl p-6 w-full max-w-md border border-[#3e3e42]">
            <h3 className="text-lg font-semibold text-gray-200 mb-4">
              Create New Document
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Document Title
                </label>
                <input
                  type="text"
                  value={newDocumentTitle}
                  onChange={(e) => setNewDocumentTitle(e.target.value)}
                  placeholder="Enter document title..."
                  className="w-full px-3 py-2 bg-[#3c3c3c] border border-[#3e3e42] rounded text-gray-200 placeholder-gray-500 focus:outline-none focus:border-[#007acc]"
                  onKeyPress={(e) => e.key === 'Enter' && handleCreateDocument()}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Document Type
                </label>
                <select
                  value={newDocumentType}
                  onChange={(e) => setNewDocumentType(e.target.value as DocumentType)}
                  className="w-full px-3 py-2 bg-[#3c3c3c] border border-[#3e3e42] rounded text-gray-200 focus:outline-none focus:border-[#007acc]"
                >
                  {supportedTypes.map((type) => (
                    <option key={type.type} value={type.type}>
                      {type.type.charAt(0).toUpperCase() + type.type.slice(1)} ({type.extensions.join(', ')})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border border-[#3e3e42] text-gray-400 rounded hover:bg-[#2a2d2e]"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateDocument}
                  disabled={!newDocumentTitle.trim() || createDocumentMutation.isPending}
                  className="flex-1 px-4 py-2 bg-[#0e639c] text-white rounded hover:bg-[#1177bb] disabled:opacity-50"
                >
                  {createDocumentMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-[#252526] rounded-lg shadow-xl p-6 w-full max-w-md border border-[#3e3e42]">
            <h3 className="text-lg font-semibold text-gray-200 mb-4">
              Upload Document
            </h3>
            <div className="space-y-4">
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".md,.txt,.html,.js,.ts,.py,.css,.json,.yaml,.yml,.xml"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full px-4 py-8 border-2 border-dashed border-[#3e3e42] rounded-lg text-gray-400 hover:border-[#007acc] hover:text-gray-200 transition-colors"
                >
                  <Upload className="h-8 w-8 mx-auto mb-2" />
                  <p>Click to select a file</p>
                  <p className="text-xs mt-1">Supports: .md, .txt, .html, .js, .ts, .py, .css, .json, .yaml, .xml</p>
                </button>
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="flex-1 px-4 py-2 border border-[#3e3e42] text-gray-400 rounded hover:bg-[#2a2d2e]"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function to get template content based on document type
function getTemplateContent(type: DocumentType, title: string): string {
  const date = new Date().toLocaleDateString();

  switch (type) {
    case 'markdown':
      return `# ${title}

Created on ${date}

## Overview

Start writing here...

## Content

- Item 1
- Item 2
- Item 3

## Notes

Add your notes here.
`;

    case 'richtext':
      return `<!DOCTYPE html>
<html>
<head>
    <title>${title}</title>
</head>
<body>
    <h1>${title}</h1>
    <p>Created on ${date}</p>

    <h2>Overview</h2>
    <p>Start writing here...</p>

    <h2>Content</h2>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
        <li>Item 3</li>
    </ul>
</body>
</html>`;

    case 'json':
      return `{
  "title": "${title}",
  "created": "${date}",
  "content": {
    "overview": "Start writing here...",
    "items": [
      "Item 1",
      "Item 2",
      "Item 3"
    ]
  }
}`;

    case 'code':
      return `// ${title}
// Created on ${date}

/**
 * Overview
 * Start writing here...
 */

function main() {
    console.log("Hello, World!");
}

main();`;

    case 'plaintext':
    default:
      return `${title}
Created on ${date}

Overview:
Start writing here...

Content:
- Item 1
- Item 2
- Item 3

Notes:
Add your notes here.`;
  }
}
