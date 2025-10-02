import { CopilotChat } from '@copilotkit/react-ui';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, FileText, Plus, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { EditorPanel } from '../components/EditorPanel';
import { useAppStore } from '../stores/useAppStore';
import { Document } from '../types';

export default function EditorView() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [documentContent, setDocumentContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newDocumentTitle, setNewDocumentTitle] = useState('');
  const [isChatPanelOpen, setIsChatPanelOpen] = useState(true);
  const [explorerWidth, setExplorerWidth] = useState(256); // 16rem = 256px
  const [chatWidth, setChatWidth] = useState(320); // 20rem = 320px
  const [isResizingExplorer, setIsResizingExplorer] = useState(false);
  const [isResizingChat, setIsResizingChat] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { } = useAppStore();
  const queryClient = useQueryClient();

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

  // This would be replaced with actual document API calls
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      // Placeholder - would call document service
      return [] as Document[];
    },
  });

  const createDocumentMutation = useMutation({
    mutationFn: async (data: { title: string; content: string }) => {
      // Use the direct create endpoint
      const response = await fetch('http://127.0.0.1:3000/api/documents/create-live', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          title: data.title,
          content: data.content,
          document_type: 'markdown',
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

      // Select the newly created document
      setSelectedDocument({
        id: document.id,
        name: document.title,
        title: document.title,
        content: document.content,
        created_at: document.created_at,
        updated_at: document.updated_at,
        user_id: document.owner_id || '',
        url: '',
        file: new File([document.content], document.title, { type: 'text/markdown' })
      });
      setDocumentContent(document.content);
    },
    onError: (error: any) => {
      console.error('Error creating document:', error);
      // You could add a toast notification here
    }
  });

  const handleCreateDocument = () => {
    if (newDocumentTitle.trim()) {
      createDocumentMutation.mutate({
        title: newDocumentTitle,
        content: `# ${newDocumentTitle}\n\nCreated on ${new Date().toLocaleDateString()}\n\n## Overview\n\nStart writing here...\n`,
      });
    }
  };

  const handleDocumentContentChange = async (id: string, content: string) => {
    setDocumentContent(content);

    // Auto-save functionality with debouncing
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await fetch(`http://127.0.0.1:3000/api/documents/edit-live/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
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

        // Update saved indicator (you could add UI feedback here)
        console.log('Document saved');
      } catch (error) {
        console.error('Error saving document:', error);
      }
    }, 1000); // Save after 1 second of inactivity
  };

  // Add ref for save timeout
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

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
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-1 text-gray-400 hover:text-gray-200 hover:bg-[#2a2d2e] rounded"
              title="Create new document"
            >
              <Plus className="h-4 w-4" />
            </button>
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
          ) : !documents || documents.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <FileText className="h-8 w-8 mx-auto mb-2 text-gray-600" />
              <p className="text-xs">No documents yet</p>
            </div>
          ) : (
            <div className="p-1">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => {
                    setSelectedDocument(doc);
                    setDocumentContent(doc.content);
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${selectedDocument?.id === doc.id
                      ? 'bg-[#094771] text-white'
                      : 'text-gray-300 hover:bg-[#2a2d2e]'}`}
                >
                  <div className="flex items-center space-x-2">
                    <FileText className="h-3 w-3 flex-shrink-0" />
                    <span className="truncate">{doc.title || doc.name}</span>
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
              type: 'document',
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
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center px-4 py-2 bg-[#0e639c] text-white rounded hover:bg-[#1177bb] text-sm"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create New Document
              </button>
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
        className={`border-l border-[#3e3e42] flex-shrink-0 transition-all duration-300 ease-in-out relative ${isChatPanelOpen ? '' : 'w-0'}`}
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
    </div>
  );
}
