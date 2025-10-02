import React, { useState } from 'react';
import { User, Wifi, WifiOff, LogOut } from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import { authService } from '../../services/authService';

interface HeaderProps {
  connectionStatus: 'connected' | 'disconnected' | 'reconnecting';
  selectedAgent: string;
  setSelectedAgent: (agentType: string) => void;
}

export default function Header({ connectionStatus, selectedAgent, setSelectedAgent }: HeaderProps) {
  const { user, setUser } = useAppStore();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = async () => {
    try {
      await authService.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
      // Force logout even if server request fails
      setUser(null);
    }
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-green-500" />;
      case 'reconnecting':
        return <Wifi className="h-4 w-4 text-yellow-500 animate-pulse" />;
      default:
        return <WifiOff className="h-4 w-4 text-red-500" />;
    }
  };

  const getConnectionText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'reconnecting':
        return 'Reconnecting...';
      default:
        return 'Disconnected';
    }
  };

  return (
    <header className="bg-[#2d2d30] border-b border-[#3e3e42] px-4 py-2">
      <div className="flex items-center justify-between">
        {/* Left side - could add breadcrumbs or page title here */}
        <div className="flex items-center space-x-3">
          <h2 className="text-sm font-medium text-gray-300">
            Agent Dashboard
          </h2>
          {/* Agent Selector */}
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 text-xs bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            <option value="document_editor">Document Editor</option>
            <option value="browser_use">Browser Agent</option>
            <option value="deep_research">Research Agent</option>
          </select>
        </div>

        {/* Right side - controls */}
        <div className="flex items-center space-x-4">
          {/* Connection Status */}
          <div className="flex items-center space-x-2 text-xs text-gray-400">
            {getConnectionIcon()}
            <span className="hidden sm:block">{getConnectionText()}</span>
          </div>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center space-x-2 p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-[#094771]"
            >
              <div className="w-6 h-6 bg-[#0e639c] rounded-full flex items-center justify-center">
                {user?.picture ? (
                  <img
                    src={user.picture}
                    alt={user.name || user.email}
                    className="w-6 h-6 rounded-full"
                  />
                ) : (
                  <User className="h-3 w-3 text-white" />
                )}
              </div>
              <div className="hidden md:block text-left">
                <div className="text-xs font-medium text-gray-300">
                  {user?.name || 'User'}
                </div>
                <div className="text-xs text-gray-500">
                  {user?.email}
                </div>
              </div>
            </button>

            {/* User Dropdown */}
            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-[#252526] rounded shadow-lg border border-[#3e3e42] z-50">
                <div className="py-1">
                  <div className="px-4 py-2 text-sm text-gray-300 border-b border-[#3e3e42]">
                    <div className="font-medium">{user?.name || 'User'}</div>
                    <div className="text-xs text-gray-500">
                      {user?.email}
                    </div>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center w-full px-4 py-2 text-sm text-gray-300 hover:bg-[#094771] hover:text-white"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Click outside to close menu */}
      {showUserMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </header>
  );
}