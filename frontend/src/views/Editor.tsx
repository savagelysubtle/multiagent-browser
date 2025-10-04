
import React, { useState } from 'react';
import ReactQuill from 'react-quill';
import 'quill/dist/quill.snow.css'; // import styles
import DOMPurify from 'dompurify';

export default function Editor() {
  const [content, setContent] = useState('This is a placeholder for the editor.');

  const handleContentChange = (newContent) => {
    const sanitizedContent = DOMPurify.sanitize(newContent);
    setContent(sanitizedContent);
  };

  const modules = {
    toolbar: [
      [{ 'header': '1'}, {'header': '2'}, { 'font': [] }],
      [{size: []}],
      ['bold', 'italic', 'underline', 'strike', 'blockquote'],
      [{'list': 'ordered'}, {'list': 'bullet'}, 
       {'indent': '-1'}, {'indent': '+1'}],
      ['link', 'image', 'video'],
      ['clean']
    ],
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 p-4">
        <ReactQuill
          value={content}
          onChange={handleContentChange}
          modules={modules}
          className="w-full h-full p-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        />
      </div>
    </div>
  );
}
