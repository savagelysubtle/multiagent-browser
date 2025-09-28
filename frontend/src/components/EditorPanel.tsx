
import React from 'react';
import type { Document } from '../types';
import { Icon } from './ui/Icon';

interface EditorPanelProps {
    item: (Document & { type: 'document' | 'manual' }) | null;
    onContentChange: (id: string, content: string) => void;
}

export const EditorPanel: React.FC<EditorPanelProps> = ({ item, onContentChange }) => {
    const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        if (item && item.type === 'document' && item.file.type.startsWith('text/')) {
            onContentChange(item.id, e.target.value);
        }
    };

    const handleDownload = () => {
        if (!item) return;

        const link = window.document.createElement('a');
        link.href = item.url;
        link.download = item.name;
        window.document.body.appendChild(link);
        link.click();
        window.document.body.removeChild(link);
    };

    if (!item) {
        return (
            <div className="w-full h-full flex flex-col items-center justify-center bg-[#1e1e1e] text-gray-500">
                <Icon name="edit" className="w-16 h-16 mb-4 text-gray-700" />
                <p>Select a file from the explorer to start editing.</p>
                <p className="text-sm">Or create a new file.</p>
            </div>
        );
    }

    const isTextFile = item.file.type.startsWith('text/');
    const isPdfFile = item.file.type === 'application/pdf';
    const isReadOnly = item.type === 'manual' || !isTextFile;

    return (
        <div className="w-full h-full flex flex-col">
            <div className="bg-[#2d2d30] px-4 py-2 text-sm border-b border-[#3e3e42] text-gray-300 flex justify-between items-center flex-shrink-0">
                <span className="flex items-center gap-2">
                    <Icon name="file" className="w-4 h-4 text-gray-400" />
                    {item.name}
                </span>
                 <button
                    onClick={handleDownload}
                    className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-[#094771] transition-colors"
                    title={`Download ${item.name}`}
                    aria-label={`Download file ${item.name}`}
                >
                    <Icon name="download" className="w-4 h-4" />
                </button>
            </div>
            {isTextFile ? (
                <textarea
                    value={item.content}
                    onChange={handleTextChange}
                    readOnly={isReadOnly}
                    className={`flex-grow p-4 text-gray-200 font-mono text-sm leading-relaxed focus:outline-none resize-none ${
                        isReadOnly ? 'bg-[#1e1e1e] cursor-default' : 'bg-[#1e1e1e]'
                    }`}
                    placeholder="Start typing your document content here..."
                    spellCheck="false"
                />
            ) : isPdfFile ? (
                 <iframe
                    src={item.url}
                    title={item.name}
                    className="w-full h-full border-none bg-white"
                />
            ) : (
                <div className="w-full h-full flex flex-col items-center justify-center bg-[#1e1e1e] text-gray-500 p-4">
                    <Icon name="file" className="w-16 h-16 mb-4 text-gray-700" />
                    <p className="font-bold text-gray-400">Preview not available</p>
                     <p className="text-sm text-center">Cannot display file '{item.name}' ({item.file.type}).</p>
                     <p className="text-sm mt-2">You can still download it using the button above.</p>
                </div>
            )}
        </div>
    );
};