import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  FileText,
  ListTodo,
  Settings,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import { cn } from '../../utils/cn';

const navigation = [
  { name: 'Editor', href: '/editor', icon: FileText },
  { name: 'Tasks', href: '/tasks', icon: ListTodo },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore();

  return (
    <div className={cn(
      "bg-[#252526] border-r border-[#3e3e42] flex flex-col transition-all duration-300",
      sidebarCollapsed ? "w-16" : "w-64"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[#3e3e42]">
        {!sidebarCollapsed && (
          <h1 className="text-lg font-semibold text-gray-200">
            Web-UI
          </h1>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="p-1 rounded text-gray-400 hover:text-gray-200 hover:bg-[#2a2d2e]"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <ChevronLeft className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href ||
                          (item.href === '/editor' && location.pathname === '/');

          return (
            <button
              key={item.name}
              onClick={() => navigate(item.href)}
              className={cn(
                "w-full flex items-center px-2 py-2 text-sm font-medium rounded transition-colors",
                isActive
                  ? "bg-[#094771] text-white"
                  : "text-gray-400 hover:bg-[#2a2d2e] hover:text-gray-200"
              )}
              title={sidebarCollapsed ? item.name : undefined}
            >
              <item.icon className={cn("h-5 w-5", sidebarCollapsed ? "mx-auto" : "mr-3")} />
              {!sidebarCollapsed && item.name}
            </button>
          );
        })}
      </nav>

      {/* Connection Status */}
      <div className="p-4 border-t border-[#3e3e42]">
        <div className={cn(
          "flex items-center text-xs text-gray-400",
          sidebarCollapsed ? "justify-center" : ""
        )}>
          <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
          {!sidebarCollapsed && "Connected"}
        </div>
      </div>
    </div>
  );
}