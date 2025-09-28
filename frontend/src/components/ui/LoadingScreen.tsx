import React from 'react';

export default function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Loading...
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          Initializing Web-UI
        </p>
      </div>
    </div>
  );
}