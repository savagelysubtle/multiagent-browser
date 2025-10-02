
import React, { useState } from 'react';
import EditorRibbon from '../components/EditorRibbon';

export default function Editor({ theme, setTheme }) {
  const [document, setDocument] = useState({ content: 'This is a placeholder for the editor.' });
  const [userSettings, setUserSettings] = useState({
    fontSize: 'base',
    fontFamily: 'sans',
  });

  const handleSettingsChange = (newSettings) => {
    setUserSettings(prev => ({ ...prev, ...newSettings }));
  };

  const handleContentChange = (e) => {
    setDocument(prev => ({ ...prev, content: e.target.value }));
  };

  const fontClass = {
    sm: 'text-sm',
    base: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl',
  }[userSettings.fontSize];

  const familyClass = {
    mono: 'font-mono',
    sans: 'font-sans',
    serif: 'font-serif',
  }[userSettings.fontFamily];

  return (
    <div className="flex flex-col h-full">
      <EditorRibbon
        userSettings={userSettings}
        onSettingsChange={handleSettingsChange}
        theme={theme}
        onThemeChange={setTheme}
        document={document}
      />
      <div className="flex-1 p-4">
        <textarea
          value={document.content}
          onChange={handleContentChange}
          className={`w-full h-full p-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 ${fontClass} ${familyClass}`}
        />
      </div>
    </div>
  );
}
