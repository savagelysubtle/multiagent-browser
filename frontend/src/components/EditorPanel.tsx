import { Editor } from '@monaco-editor/react';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import * as monaco from 'monaco-editor';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { DocumentType, EditorMode, useAppStore } from '../stores/useAppStore';
import type { Document } from '../types';
import { Icon } from './ui/Icon';

interface EditorPanelProps {
    item: (Document & { type: 'document' | 'manual' }) | null;
    onContentChange: (id: string, content: string) => void;
}

export const EditorPanel: React.FC<EditorPanelProps> = ({ item, onContentChange }) => {
    const { editorSettings, updateEditorSettings, markDocumentDirty, setDocumentEditorMode } = useAppStore();
    const [editorMode, setEditorMode] = useState<EditorMode>('source');
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [showFindReplace, setShowFindReplace] = useState(false);
    const [replaceTerm, setReplaceTerm] = useState('');
    const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'error' | 'dirty'>('saved');

    const monacoRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
    const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const markdownPreviewRef = useRef<HTMLDivElement>(null);

    // Detect document type and language
    const documentType: DocumentType = item?.name ? detectDocumentType(item.name) : 'plaintext';
    const language = detectLanguage(item?.name || '');

    // Handle content changes with auto-save
    const handleContentChange = useCallback((newContent: string) => {
        if (!item) return;

        // Mark document as dirty immediately
        markDocumentDirty(item.id, true);
        setSaveStatus('dirty');

        // Clear existing timeout
        if (saveTimeoutRef.current) {
            clearTimeout(saveTimeoutRef.current);
        }

        // Auto-save after delay
        if (editorSettings.autoSave) {
            setSaveStatus('saving');
            saveTimeoutRef.current = setTimeout(async () => {
                try {
                    await onContentChange(item.id, newContent);
                    markDocumentDirty(item.id, false);
                    setSaveStatus('saved');
                } catch (error) {
                    console.error('Auto-save failed:', error);
                    setSaveStatus('error');
                }
            }, editorSettings.autoSaveDelay);
        }
    }, [item, editorSettings, markDocumentDirty, onContentChange]);

    // Manual save function
    const handleManualSave = useCallback(async () => {
        if (!item || !monacoRef.current) return;

        const content = monacoRef.current.getValue();
        setSaveStatus('saving');

        try {
            await onContentChange(item.id, content);
            markDocumentDirty(item.id, false);
            setSaveStatus('saved');
        } catch (error) {
            console.error('Manual save failed:', error);
            setSaveStatus('error');
        }
    }, [item, markDocumentDirty, onContentChange]);

    // Handle keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 's':
                        e.preventDefault();
                        handleManualSave();
                        break;
                    case 'f':
                        e.preventDefault();
                        setShowFindReplace(!showFindReplace);
                        break;
                    case 'F11':
                        e.preventDefault();
                        setIsFullscreen(!isFullscreen);
                        break;
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleManualSave, showFindReplace, isFullscreen]);

    // Monaco editor configuration
    const editorOptions: monaco.editor.IStandaloneEditorConstructionOptions = {
        fontSize: editorSettings.fontSize,
        fontFamily: editorSettings.fontFamily,
        lineHeight: editorSettings.lineHeight,
        wordWrap: editorSettings.wordWrap ? 'on' : 'off',
        minimap: { enabled: editorSettings.minimap },
        lineNumbers: editorSettings.showLineNumbers ? 'on' : 'off',
        cursorBlinking: 'smooth',
        smoothScrolling: true,
        automaticLayout: true,
        scrollBeyondLastLine: false,
        renderWhitespace: 'selection',
        bracketPairColorization: { enabled: true },
        guides: {
            indentation: true,
            bracketPairs: true,
        },
    };

    // Handle download
    const handleDownload = () => {
        if (!item) return;

        const content = monacoRef.current?.getValue() || item.content;
        const blob = new Blob([content], { type: getFileTypeFromDocumentType(documentType) });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.href = url;
        link.download = item.name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    // Handle export to different formats
    const handleExport = async (format: 'pdf' | 'html' | 'docx') => {
        if (!item || !monacoRef.current) return;

        const content = monacoRef.current.getValue();

        try {
            const response = await fetch('/api/documents/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                },
                body: JSON.stringify({
                    document_id: item.id,
                    content,
                    format,
                    document_type: documentType,
                }),
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `${item.name.split('.')[0]}.${format}`;
                link.click();
                URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error('Export failed:', error);
        }
    };

    // Find and replace functionality
    const handleFind = () => {
        if (!monacoRef.current || !searchTerm) return;

        const matches = monacoRef.current.getModel()?.findMatches(
            searchTerm,
            true,
            false,
            true,
            null,
            true
        );

        if (matches && matches.length > 0) {
            monacoRef.current.setSelection(matches[0].range);
            monacoRef.current.revealRangeInCenter(matches[0].range);
        }
    };

    const handleReplace = () => {
        if (!monacoRef.current || !searchTerm) return;

        const selection = monacoRef.current.getSelection();
        const selectedText = monacoRef.current.getModel()?.getValueInRange(selection!);

        if (selectedText === searchTerm) {
            monacoRef.current.executeEdits('replace', [{
                range: selection!,
                text: replaceTerm,
            }]);
        }
    };

    const handleReplaceAll = () => {
        if (!monacoRef.current || !searchTerm) return;

        const model = monacoRef.current.getModel();
        if (!model) return;

        const matches = model.findMatches(searchTerm, true, false, true, null, true);
        const edits = matches.map(match => ({
            range: match.range,
            text: replaceTerm,
        }));

        monacoRef.current.executeEdits('replace-all', edits);
    };

    // Render markdown preview
    const renderMarkdownPreview = (content: string) => {
        const html = marked(content);
        return DOMPurify.sanitize(html);
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

    const isTextFile = documentType !== 'pdf';
    const isReadOnly = item.type === 'manual' || !isTextFile;

    return (
        <div className={`w-full h-full flex flex-col ${isFullscreen ? 'fixed inset-0 z-50 bg-[#1e1e1e]' : ''}`}>
            {/* Enhanced toolbar */}
            <div className="bg-[#2d2d30] px-4 py-2 text-sm border-b border-[#3e3e42] text-gray-300 flex justify-between items-center flex-shrink-0">
                <div className="flex items-center gap-2">
                    <Icon name="file" className="w-4 h-4 text-gray-400" />
                    <span className="flex items-center gap-2">
                        {item.name}
                        {(item as any)?.isDirty && <span className="text-orange-400">●</span>}
                    </span>
                    <span className="text-xs text-gray-500">
                        {documentType} • {language}
                    </span>
                    <div className="flex items-center gap-1 text-xs">
                        <span className={`px-2 py-1 rounded ${
                            saveStatus === 'saved' ? 'bg-green-700 text-green-200' :
                            saveStatus === 'saving' ? 'bg-yellow-700 text-yellow-200' :
                            saveStatus === 'error' ? 'bg-red-700 text-red-200' :
                            'bg-orange-700 text-orange-200'
                        }`}>
                            {saveStatus === 'saved' ? 'Saved' :
                             saveStatus === 'saving' ? 'Saving...' :
                             saveStatus === 'error' ? 'Error' : 'Unsaved'}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {/* Editor mode toggle for markdown */}
                    {documentType === 'markdown' && (
                        <div className="flex rounded overflow-hidden border border-[#3e3e42]">
                            <button
                                onClick={() => setEditorMode('source')}
                                className={`px-2 py-1 text-xs ${
                                    editorMode === 'source' ? 'bg-[#094771] text-white' : 'text-gray-400 hover:text-gray-200'
                                }`}
                            >
                                Source
                            </button>
                            <button
                                onClick={() => setEditorMode('visual')}
                                className={`px-2 py-1 text-xs ${
                                    editorMode === 'visual' ? 'bg-[#094771] text-white' : 'text-gray-400 hover:text-gray-200'
                                }`}
                            >
                                Preview
                            </button>
                            <button
                                onClick={() => setEditorMode('split')}
                                className={`px-2 py-1 text-xs ${
                                    editorMode === 'split' ? 'bg-[#094771] text-white' : 'text-gray-400 hover:text-gray-200'
                                }`}
                            >
                                Split
                            </button>
                        </div>
                    )}

                    {/* Toolbar buttons */}
                    <button
                        onClick={() => setShowFindReplace(!showFindReplace)}
                        className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-[#094771] transition-colors"
                        title="Find & Replace (Ctrl+F)"
                    >
                        <Icon name="search" className="w-4 h-4" />
                    </button>

                    <button
                        onClick={handleManualSave}
                        className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-[#094771] transition-colors"
                        title="Save (Ctrl+S)"
                        disabled={saveStatus === 'saving'}
                    >
                        <Icon name="save" className="w-4 h-4" />
                    </button>

                    <button
                        onClick={() => setIsFullscreen(!isFullscreen)}
                        className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-[#094771] transition-colors"
                        title="Toggle Fullscreen (F11)"
                    >
                        <Icon name={isFullscreen ? "minimize" : "maximize"} className="w-4 h-4" />
                    </button>

                    {/* Export dropdown */}
                    <div className="relative group">
                        <button className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-[#094771] transition-colors">
                            <Icon name="download" className="w-4 h-4" />
                        </button>
                        <div className="absolute right-0 top-full mt-1 bg-[#252526] border border-[#3e3e42] rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                            <button onClick={handleDownload} className="block w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-[#094771]">
                                Download Original
                            </button>
                            <button onClick={() => handleExport('pdf')} className="block w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-[#094771]">
                                Export as PDF
                            </button>
                            <button onClick={() => handleExport('html')} className="block w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-[#094771]">
                                Export as HTML
                            </button>
                            <button onClick={() => handleExport('docx')} className="block w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-[#094771]">
                                Export as DOCX
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Find & Replace Panel */}
            {showFindReplace && (
                <div className="bg-[#2d2d30] border-b border-[#3e3e42] p-3">
                    <div className="flex gap-2 mb-2">
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Find..."
                            className="flex-1 px-2 py-1 bg-[#3c3c3c] border border-[#3e3e42] rounded text-xs text-gray-300"
                            onKeyPress={(e) => e.key === 'Enter' && handleFind()}
                        />
                        <button onClick={handleFind} className="px-3 py-1 bg-[#094771] text-white rounded text-xs">
                            Find
                        </button>
                    </div>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={replaceTerm}
                            onChange={(e) => setReplaceTerm(e.target.value)}
                            placeholder="Replace..."
                            className="flex-1 px-2 py-1 bg-[#3c3c3c] border border-[#3e3e42] rounded text-xs text-gray-300"
                        />
                        <button onClick={handleReplace} className="px-3 py-1 bg-[#0e639c] text-white rounded text-xs">
                            Replace
                        </button>
                        <button onClick={handleReplaceAll} className="px-3 py-1 bg-[#0e639c] text-white rounded text-xs">
                            Replace All
                        </button>
                    </div>
                </div>
            )}

            {/* Editor Content */}
            <div className="flex-1 flex">
                {isTextFile ? (
                    documentType === 'markdown' && editorMode === 'split' ? (
                        // Split view for markdown
                        <>
                            <div className="flex-1 border-r border-[#3e3e42]">
                                <Editor
                                    height="100%"
                                    language="markdown"
                                    value={item.content}
                                    onChange={handleContentChange}
                                    options={{ ...editorOptions, readOnly: isReadOnly }}
                                    theme={editorSettings.theme}
                                    onMount={(editor) => {
                                        monacoRef.current = editor;
                                    }}
                                />
                            </div>
                            <div className="flex-1 p-4 bg-white text-black overflow-y-auto">
                                <div
                                    ref={markdownPreviewRef}
                                    className="prose prose-sm max-w-none"
                                    dangerouslySetInnerHTML={{ __html: renderMarkdownPreview(item.content) }}
                                />
                            </div>
                        </>
                    ) : documentType === 'markdown' && editorMode === 'visual' ? (
                        // Preview only for markdown
                        <div className="flex-1 p-4 bg-white text-black overflow-y-auto">
                            <div
                                ref={markdownPreviewRef}
                                className="prose prose-sm max-w-none"
                                dangerouslySetInnerHTML={{ __html: renderMarkdownPreview(item.content) }}
                            />
                        </div>
                    ) : (
                        // Monaco editor for all other cases
                        <Editor
                            height="100%"
                            language={language}
                            value={item.content}
                            onChange={handleContentChange}
                            options={{ ...editorOptions, readOnly: isReadOnly }}
                            theme={editorSettings.theme}
                            onMount={(editor) => {
                                monacoRef.current = editor;
                            }}
                        />
                    )
                ) : (
                    // PDF or other non-text files
                    <iframe
                        src={item.url}
                        title={item.name}
                        className="w-full h-full border-none bg-white"
                    />
                )}
            </div>
        </div>
    );
};

// Helper functions
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

function detectLanguage(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
        js: 'javascript',
        jsx: 'javascript',
        ts: 'typescript',
        tsx: 'typescript',
        py: 'python',
        html: 'html',
        htm: 'html',
        css: 'css',
        scss: 'scss',
        md: 'markdown',
        json: 'json',
        yaml: 'yaml',
        yml: 'yaml',
        xml: 'xml',
        txt: 'plaintext',
    };
    return langMap[ext || ''] || 'plaintext';
}

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