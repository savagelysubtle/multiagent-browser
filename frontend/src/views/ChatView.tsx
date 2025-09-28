import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bot, Send, Loader2 } from 'lucide-react';
import { agentService } from '../services/agentService';
import { useAppStore } from '../stores/useAppStore';
import { ChatMessage } from '../types';

export default function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      sender: 'ai',
      text: 'Hello! I can help you with document editing, web browsing, and research tasks. What would you like to do?',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState('document_editor');

  const { addTask } = useAppStore();

  // Fetch available agents
  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentService.getAvailableAgents(),
  });

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isProcessing) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsProcessing(true);

    try {
      // Determine the appropriate action based on the message content
      let action = 'chat';
      let payload: any = { message: inputMessage };

      // Simple intent detection based on keywords
      if (inputMessage.toLowerCase().includes('create') && inputMessage.toLowerCase().includes('document')) {
        action = 'create_document';
        payload = {
          filename: 'chat_document.md',
          content: inputMessage,
          document_type: 'markdown'
        };
      } else if (inputMessage.toLowerCase().includes('search') || inputMessage.toLowerCase().includes('find')) {
        action = 'search_documents';
        payload = { query: inputMessage, limit: 10 };
      } else if (inputMessage.toLowerCase().includes('browse') || inputMessage.toLowerCase().includes('website')) {
        setSelectedAgent('browser_use');
        action = 'browse';
        // Extract URL from message if present
        const urlMatch = inputMessage.match(/(https?:\/\/[^\s]+)/);
        payload = {
          url: urlMatch ? urlMatch[0] : 'https://google.com',
          instruction: inputMessage
        };
      } else if (inputMessage.toLowerCase().includes('research')) {
        setSelectedAgent('deep_research');
        action = 'research';
        payload = {
          topic: inputMessage,
          depth: 'standard'
        };
      }

      // Submit task to agent
      const response = await agentService.executeTask({
        agent_type: selectedAgent,
        action,
        payload,
      });

      // Add AI response
      const aiMessage: ChatMessage = {
        id: Date.now().toString() + '_ai',
        sender: 'ai',
        text: `I've started a ${selectedAgent.replace('_', ' ')} task to help with your request. Task ID: ${response.task_id}. You can monitor the progress in the Tasks view.`,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, aiMessage]);

    } catch (error: any) {
      const errorMessage: ChatMessage = {
        id: Date.now().toString() + '_error',
        sender: 'ai',
        text: `Sorry, I encountered an error: ${error.message || 'Unknown error occurred'}`,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Bot className="h-6 w-6 text-primary" />
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              AI Assistant
            </h1>
          </div>

          {/* Agent Selector */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600 dark:text-gray-400">Agent:</label>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="border border-gray-300 dark:border-gray-600 rounded-md px-3 py-1 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="document_editor">Document Editor</option>
              <option value="browser_use">Browser Agent</option>
              <option value="deep_research">Research Agent</option>
            </select>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="max-w-4xl mx-auto">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
                }`}
              >
                {message.sender === 'ai' && (
                  <div className="flex items-center space-x-2 mb-2">
                    <Bot className="h-4 w-4 text-primary" />
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      AI Assistant
                    </span>
                  </div>
                )}
                <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                {message.timestamp && (
                  <p className="text-xs opacity-70 mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                )}
              </div>
            </div>
          ))}

          {isProcessing && (
            <div className="flex justify-start">
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Processing your request...
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-3">
            <div className="flex-1">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask me to create documents, browse websites, or research topics..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
                rows={2}
                disabled={isProcessing}
              />
            </div>
            <button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isProcessing}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>

          {/* Quick Actions */}
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => setInputMessage('Create a new markdown document with a project plan')}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Create Document
            </button>
            <button
              onClick={() => setInputMessage('Search for documents about React')}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Search Documents
            </button>
            <button
              onClick={() => setInputMessage('Browse https://github.com and find trending repositories')}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Browse Web
            </button>
            <button
              onClick={() => setInputMessage('Research the latest trends in AI development')}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Research Topic
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}