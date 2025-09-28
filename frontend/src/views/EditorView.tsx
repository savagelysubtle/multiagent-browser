import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, FileText, Search, Save, Trash2 } from 'lucide-react';
import { agentService } from '../services/agentService';
import { useAppStore } from '../stores/useAppStore';
import { Document } from '../types';

export default function EditorView() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [documentContent, setDocumentContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newDocumentTitle, setNewDocumentTitle] = useState('');

  const { addTask } = useAppStore();
  const queryClient = useQueryClient();

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
      return agentService.createDocument(
        `${data.title}.md`,
        data.content,
        'markdown'
      );
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setShowCreateModal(false);
      setNewDocumentTitle('');
      // Add task to store for tracking
      addTask({
        id: result.task_id,
        agent_type: 'document_editor',
        action: 'create_document',
        status: 'pending',
        created_at: new Date().toISOString(),
      });
    },
  });

  const searchDocumentsMutation = useMutation({
    mutationFn: (query: string) => {
      return agentService.searchDocuments(query);
    },
    onSuccess: (result) => {
      addTask({
        id: result.task_id,
        agent_type: 'document_editor',
        action: 'search_documents',
        status: 'pending',
        created_at: new Date().toISOString(),
      });
    },
  });

  const editDocumentMutation = useMutation({
    mutationFn: (data: { documentId: string; instruction: string }) => {
      return agentService.editDocument(data.documentId, data.instruction);
    },
    onSuccess: (result) => {
      addTask({
        id: result.task_id,
        agent_type: 'document_editor',
        action: 'edit_document',
        status: 'pending',
        created_at: new Date().toISOString(),
      });
    },
  });

  const handleCreateDocument = () => {
    if (newDocumentTitle.trim()) {
      createDocumentMutation.mutate({
        title: newDocumentTitle,
        content: 'Welcome to your new document!\n\nStart writing here...',
      });
    }
  };

  const handleSearchDocuments = () => {
    if (searchQuery.trim()) {
      searchDocumentsMutation.mutate(searchQuery);
    }
  };

  const handleEditDocument = () => {
    if (selectedDocument && documentContent !== selectedDocument.content) {
      const instruction = `Update the document content to: ${documentContent}`;
      editDocumentMutation.mutate({
        documentId: selectedDocument.id,
        instruction,
      });
    }
  };

  return (
    <div className="h-full flex bg-gray-50 dark:bg-gray-900">
      {/* Document List Sidebar */}
      <div className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Documents
            </h2>
            <button
              onClick={() => setShowCreateModal(true)}
              className="p-2 text-primary hover:bg-primary/10 rounded-md"
              title="Create new document"
            >
              <Plus className="h-5 w-5" />
            </button>
          </div>

          {/* Search */}
          <div className="flex space-x-2">
            <div className="flex-1 relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="w-full px-3 py-2 pl-9 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                onKeyPress={(e) => e.key === 'Enter' && handleSearchDocuments()}
              />
              <Search className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            </div>
            <button
              onClick={handleSearchDocuments}
              disabled={!searchQuery.trim() || searchDocumentsMutation.isPending}
              className="px-3 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 text-sm"
            >
              Search
            </button>
          </div>
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              Loading documents...
            </div>
          ) : !documents || documents.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              <FileText className="h-12 w-12 mx-auto mb-2 text-gray-300 dark:text-gray-600" />
              <p>No documents yet</p>
              <p className="text-xs">Create your first document!</p>
            </div>
          ) : (
            <div className="p-2">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => {
                    setSelectedDocument(doc);
                    setDocumentContent(doc.content);
                  }}
                  className={`w-full text-left p-3 rounded-md mb-1 transition-colors ${
                    selectedDocument?.id === doc.id
                      ? 'bg-primary/10 border border-primary/20'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <FileText className="h-5 w-5 text-gray-400 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                        {doc.title || doc.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                        {doc.content.substring(0, 100)}...
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 flex flex-col">
        {selectedDocument ? (
          <>
            {/* Editor Header */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    {selectedDocument.title || selectedDocument.name}
                  </h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Last modified: {new Date(selectedDocument.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={handleEditDocument}
                    disabled={documentContent === selectedDocument.content || editDocumentMutation.isPending}
                    className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary/90 disabled:opacity-50"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {editDocumentMutation.isPending ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            </div>

            {/* Editor Content */}
            <div className="flex-1 p-4">
              <textarea
                value={documentContent}
                onChange={(e) => setDocumentContent(e.target.value)}
                className="w-full h-full p-4 border border-gray-300 dark:border-gray-600 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm"
                placeholder="Start writing your document..."
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-white dark:bg-gray-800">
            <div className="text-center">
              <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                No document selected
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Choose a document from the sidebar to start editing
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create New Document
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Document Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Create New Document
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Document Title
                </label>
                <input
                  type="text"
                  value={newDocumentTitle}
                  onChange={(e) => setNewDocumentTitle(e.target.value)}
                  placeholder="Enter document title..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  onKeyPress={(e) => e.key === 'Enter' && handleCreateDocument()}
                />
              </div>
              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateDocument}
                  disabled={!newDocumentTitle.trim() || createDocumentMutation.isPending}
                  className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
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