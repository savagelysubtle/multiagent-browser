import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAppStore } from '../stores/useAppStore'; // Import useAppStore

// Layout components
import Sidebar from '../components/layout/Sidebar';
import Header from '../components/layout/Header';

// Feature views
import EditorView from '../views/EditorView';
import TasksView from '../views/TasksView';
import SettingsView from '../views/SettingsView';
import ChatView from '../views/ChatView'; // Import ChatView

export default function DashboardPage() {
  const { isConnected } = useWebSocket();
  const { selectedAgent, setSelectedAgent } = useAppStore(); // Get selectedAgent and setSelectedAgent

  return (
    <div className="flex h-screen bg-[#1e1e1e]">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header with connection status and agent selector */}
        <Header
          connectionStatus={isConnected ? 'connected' : 'disconnected'}
          selectedAgent={selectedAgent}
          setSelectedAgent={setSelectedAgent}
        />

        {/* Content area */}
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<EditorView />} />
            <Route path="/editor" element={<EditorView />} />
            <Route path="/tasks" element={<TasksView />} />
            <Route path="/settings" element={<SettingsView />} />
            <Route path="/chat" element={<ChatView />} /> {/* Add route for ChatView */}
          </Routes>
        </main>
      </div>
    </div>
  );
}