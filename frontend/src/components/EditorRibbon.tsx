import React, { useState, useRef, useEffect } from 'react';
import { Sun, Moon, ChevronDown } from 'lucide-react';

const Dropdown = ({ label, options, selected, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [ref]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-1 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 px-2 py-1 rounded-md"
      >
        <span>{label}</span>
        <ChevronDown className="h-4 w-4" />
      </button>
      {isOpen && (
        <div className="absolute top-full mt-1 w-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10">
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                onSelect(option.value);
                setIsOpen(false);
              }}
              className={`w-full text-left px-3 py-1.5 text-sm ${selected === option.value ? 'bg-blue-500 text-white' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default function EditorRibbon({ userSettings, onSettingsChange, theme, onThemeChange, document }) {
  const wordCount = document?.content.split(/\s+/).filter(Boolean).length || 0;
  const charCount = document?.content.length || 0;

  const fontSizes = [
    { label: 'Small', value: 'sm' },
    { label: 'Medium', value: 'base' },
    { label: 'Large', value: 'lg' },
    { label: 'Extra Large', value: 'xl' },
  ];

  const fontFamilies = [
    { label: 'Mono', value: 'mono' },
    { label: 'Sans', value: 'sans' },
    { label: 'Serif', value: 'serif' },
  ];

  return (
    <div className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
      <div className="flex items-center space-x-4">
        <Dropdown
          label="Font Size"
          options={fontSizes}
          selected={userSettings.fontSize}
          onSelect={(value) => onSettingsChange({ fontSize: value })}
        />
        <Dropdown
          label="Font Family"
          options={fontFamilies}
          selected={userSettings.fontFamily}
          onSelect={(value) => onSettingsChange({ fontFamily: value })}
        />
      </div>
      <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
        <span>Words: {wordCount}</span>
        <span>Characters: {charCount}</span>
      </div>
      <div>
        <button onClick={() => onThemeChange(theme === 'light' ? 'dark' : 'light')} className="p-2 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700">
          {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
        </button>
      </div>
    </div>
  );
}