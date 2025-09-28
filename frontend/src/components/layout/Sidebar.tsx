import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  FileText,
  MessageCircle,
  ListTodo,
  Settings,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import { cn } from '../../utils/cn';

const navigation = [
  { name: 'Editor', href: '/editor', icon: FileText },
  { name: 'Chat', href: '/chat', icon: MessageCircle },
  { name: 'Tasks', href: '/tasks', icon: ListTodo },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore();

  return (
    <div className={cn(
      "bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300",
      sidebarCollapsed ? "w-16" : "w-64"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        {!sidebarCollapsed && (
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Web-UI
          </h1>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="p-1 rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
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
                "w-full flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
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
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className={cn(
          "flex items-center text-xs text-gray-500 dark:text-gray-400",
          sidebarCollapsed ? "justify-center" : ""
        )}>
          <div className="w-2 h-2 bg-green-400 rounded-full mr-2" />
          {!sidebarCollapsed && "Connected"}
        </div>
      </div>
    </div>
  );
}