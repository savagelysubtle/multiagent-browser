import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bot, Send, Loader2 } from 'lucide-react';
import { agentService } from '../services/agentService';
import { useAppStore } from '../stores/useAppStore';
import { ChatMessage } from '../types';
import { agUiService } from '../services/agUiService';
import { RunAgentInput, EventType, TextMessageContentEvent, TextMessageEndEvent, TextMessageStartEvent, RunFinishedEvent } from '@ag-ui/client';

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
  const messageIdRef = useRef<string | null>(null);

  const { addTask } = useAppStore();

  // Fetch available agents
  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentService.getAvailableAgents(),
  });

  useEffect(() => {
    const agent = agUiService.getAgent();
    console.log('ChatView: AG-UI Agent initialized', agent);

    const handleEvent = (event: any) => {
      console.log('ChatView: Received AG-UI event:', event);
      switch (event.type) {
        case EventType.RUN_STARTED:
          console.log('ChatView: RUN_STARTED event', event);
          setIsProcessing(true);
          break;
        case EventType.TEXT_MESSAGE_START:
          console.log('ChatView: TEXT_MESSAGE_START event', event);
          messageIdRef.current = event.message_id;
          setMessages((prev) => [
            ...prev,
            {
              id: event.message_id,
              sender: 'ai',
              text: '',
              timestamp: new Date().toISOString(),
            },
          ]);
          break;
        case EventType.TEXT_MESSAGE_CONTENT:
          console.log('ChatView: TEXT_MESSAGE_CONTENT event', event);
          if (messageIdRef.current === event.message_id) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === event.message_id ? { ...msg, text: msg.text + event.delta } : msg
              )
            );
          }
          break;
        case EventType.TEXT_MESSAGE_END:
          console.log('ChatView: TEXT_MESSAGE_END event', event);
          messageIdRef.current = null;
          break;
        case EventType.RUN_FINISHED:
          console.log('ChatView: RUN_FINISHED event', event);
          setIsProcessing(false);
          break;
        default:
          console.warn('ChatView: Unhandled AG-UI event type:', event.type, event);
          break;
      }
    };

    agent.onEvent(handleEvent);

    return () => {
      console.log('ChatView: Cleaning up AG-UI event listener');
      agent.offEvent(handleEvent);
    };
  }, []);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isProcessing) {
      console.log('ChatView: Message empty or processing, not sending.');
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsProcessing(true);
    console.log('ChatView: User message added, processing started.');

    try {
      const agent = agUiService.getAgent();
      const runAgentInput: RunAgentInput = {
        thread_id: agent.threadId,
        run_id: userMessage.id, // Use user message ID as run_id for now
        messages: [
          {
            role: 'user',
            content: inputMessage,
            message_id: userMessage.id,
          },
        ],
        metadata: { selectedAgent: selectedAgent }, // Include selectedAgent in metadata
      };
      console.log('ChatView: Sending RunAgentInput:', runAgentInput);
      await agent.run(runAgentInput);
      console.log('ChatView: RunAgentInput sent successfully.');

    } catch (error: any) {
      console.error('ChatView: Error sending RunAgentInput:', error);
      const errorMessage: ChatMessage = {
        id: Date.now().toString() + '_error',
        sender: 'ai',
        text: `Sorry, I encountered an error: ${error.message || 'Unknown error occurred'}. Please try again.`,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorMessage]);
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
              onClick={() => setInputMessage('Create a new document called "Project Plan"')}
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
              onClick={() => setInputMessage('Help me write a technical specification document')}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Get Writing Help
            </button>
            <button
              onClick={() => setInputMessage('What documents do I have?')}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              List Documents
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}