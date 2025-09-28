
import React, { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';
import { Icon } from './ui/Icon';

interface ChatPanelProps {
    messages: ChatMessage[];
    onSendMessage: (message: string) => void;
    isLoading: boolean;
}

const ChatMessageComponent: React.FC<{ message: ChatMessage }> = ({ message }) => {
    const isUser = message.sender === 'user';
    return (
        <div className={`flex items-start gap-2 my-2 ${isUser ? 'justify-end' : ''}`}>
            {!isUser && (
                <div className="w-6 h-6 flex-shrink-0 rounded bg-[#0e639c] flex items-center justify-center">
                    <Icon name="sparkles" className="w-4 h-4 text-white" />
                </div>
            )}
            <div className={`px-3 py-2 rounded max-w-[85%] text-sm ${isUser
                ? 'bg-[#094771] text-gray-100'
                : 'bg-[#1e1e1e] text-gray-300 border border-[#3e3e42]'
            }`}>
                <p className="whitespace-pre-wrap break-words">{message.text}</p>
            </div>
        </div>
    );
};

const LoadingIndicator: React.FC = () => (
    <div className="flex items-start gap-2 my-2">
        <div className="w-6 h-6 flex-shrink-0 rounded bg-[#0e639c] flex items-center justify-center">
            <Icon name="sparkles" className="w-4 h-4 text-white" />
        </div>
        <div className="px-3 py-2 rounded bg-[#1e1e1e] border border-[#3e3e42] flex items-center gap-1 text-gray-300">
            <span className="animate-pulse text-sm">●</span>
            <span className="animate-pulse delay-150 text-sm">●</span>
            <span className="animate-pulse delay-300 text-sm">●</span>
        </div>
    </div>
);


export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, onSendMessage, isLoading }) => {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(scrollToBottom, [messages, isLoading]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            onSendMessage(input);
            setInput('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className="w-full h-full bg-[#252526] flex flex-col">
            <div className="p-3 border-b border-[#3e3e42] flex-shrink-0">
                <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">AI Assistant</h2>
            </div>
            <div className="flex-grow p-3 overflow-y-auto">
                {messages.map((msg) => (
                    <ChatMessageComponent key={msg.id} message={msg} />
                ))}
                {isLoading && <LoadingIndicator />}
                <div ref={messagesEndRef} />
            </div>
            <div className="p-3 border-t border-[#3e3e42] flex-shrink-0">
                <form onSubmit={handleSubmit} className="flex items-end gap-2">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask anything..."
                        className="flex-grow bg-[#3c3c3c] text-gray-200 rounded p-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#007acc] resize-none border border-[#3e3e42] placeholder-gray-500 min-h-[36px] max-h-[120px]"
                        rows={1}
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="p-2 bg-[#0e639c] text-white rounded hover:bg-[#1177bb] disabled:bg-[#3e3e42] disabled:text-gray-600 disabled:cursor-not-allowed transition-colors"
                    >
                        <Icon name="send" className="w-4 h-4" />
                    </button>
                </form>
            </div>
        </div>
    );
};