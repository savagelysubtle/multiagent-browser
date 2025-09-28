import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';

// Layout components
import Sidebar from '../components/layout/Sidebar';
import Header from '../components/layout/Header';

// Feature views
import EditorView from '../views/EditorView';
import TasksView from '../views/TasksView';
import SettingsView from '../views/SettingsView';

export default function DashboardPage() {
  const { isConnected } = useWebSocket();

  return (
    <div className="flex h-screen bg-[#1e1e1e]">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header with connection status */}
        <Header connectionStatus={isConnected ? 'connected' : 'disconnected'} />

        {/* Content area */}
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<EditorView />} />
            <Route path="/editor" element={<EditorView />} />
            <Route path="/tasks" element={<TasksView />} />
            <Route path="/settings" element={<SettingsView />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}