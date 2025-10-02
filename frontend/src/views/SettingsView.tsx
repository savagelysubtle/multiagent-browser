import React, { useState } from 'react';
import { Save, User, Palette, Bot, Bell, Shield } from 'lucide-react';
import { useAppStore } from '../stores/useAppStore';
import { authService } from '../services/authService';
import { toast } from 'react-toastify';

interface SettingsViewProps {
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
}

export default function SettingsView({ theme, setTheme }: SettingsViewProps) {
  const { user } = useAppStore();
  const [activeTab, setActiveTab] = useState('profile');
  const [isSaving, setIsSaving] = useState(false);

  // Profile settings
  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    email: user?.email || '',
  });

  // Agent settings
  const [agentSettings, setAgentSettings] = useState({
    defaultAgent: 'document_editor',
    autoSave: true,
    taskTimeout: 300,
    enableNotifications: true,
  });

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'appearance', name: 'Appearance', icon: Palette },
    { id: 'agents', name: 'Agents', icon: Bot },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'security', name: 'Security', icon: Shield },
  ];

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      await authService.updateUserPreferences({
        name: profileData.name,
      });
      toast.success('Profile updated successfully!');
    } catch (error: any) {
      toast.error(error.message || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAgentSettings = async () => {
    setIsSaving(true);
    try {
      await authService.updateUserState({
        agentSettings,
      });
      toast.success('Agent settings saved successfully!');
    } catch (error: any) {
      toast.error(error.message || 'Failed to save agent settings');
    } finally {
      setIsSaving(false);
    }
  };

  const renderProfileTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Profile Information
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Name
            </label>
            <input
              type="text"
              value={profileData.name}
              onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Email
            </label>
            <input
              type="email"
              value={profileData.email}
              disabled
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Email cannot be changed
            </p>
          </div>
        </div>
        <div className="mt-6">
          <button
            onClick={handleSaveProfile}
            disabled={isSaving}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </div>
    </div>
  );

  const renderAppearanceTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Theme
        </h3>
        <div className="space-y-3">
          <label className="flex items-center">
            <input
              type="radio"
              name="theme"
              value="light"
              checked={theme === 'light'}
              onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}
              className="mr-3"
            />
            <span className="text-gray-700 dark:text-gray-300">Light</span>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="theme"
              value="dark"
              checked={theme === 'dark'}
              onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}
              className="mr-3"
            />
            <span className="text-gray-700 dark:text-gray-300">Dark</span>
          </label>
        </div>
      </div>
    </div>
  );

  const renderAgentsTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Agent Configuration
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Agent
            </label>
            <select
              value={agentSettings.defaultAgent}
              onChange={(e) => setAgentSettings({ ...agentSettings, defaultAgent: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="document_editor">Document Editor</option>
              <option value="browser_use">Browser Agent</option>
              <option value="deep_research">Research Agent</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Task Timeout (seconds)
            </label>
            <input
              type="number"
              value={agentSettings.taskTimeout}
              onChange={(e) => setAgentSettings({ ...agentSettings, taskTimeout: parseInt(e.target.value) })}
              min="60"
              max="3600"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="autoSave"
              checked={agentSettings.autoSave}
              onChange={(e) => setAgentSettings({ ...agentSettings, autoSave: e.target.checked })}
              className="mr-3"
            />
            <label htmlFor="autoSave" className="text-sm text-gray-700 dark:text-gray-300">
              Auto-save document changes
            </label>
          </div>
        </div>

        <div className="mt-6">
          <button
            onClick={handleSaveAgentSettings}
            disabled={isSaving}
            className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save Agent Settings'}
          </button>
        </div>
      </div>
    </div>
  );

  const renderNotificationsTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Notification Preferences
        </h3>
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="enableNotifications"
              checked={agentSettings.enableNotifications}
              onChange={(e) => setAgentSettings({ ...agentSettings, enableNotifications: e.target.checked })}
              className="mr-3"
            />
            <label htmlFor="enableNotifications" className="text-sm text-gray-700 dark:text-gray-300">
              Enable task completion notifications
            </label>
          </div>

          <div className="text-sm text-gray-500 dark:text-gray-400">
            <p>Notifications will appear when:</p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Agent tasks are completed</li>
              <li>Tasks fail or encounter errors</li>
              <li>WebSocket connection is lost</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );

  const renderSecurityTab = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          Security Settings
        </h3>
        <div className="space-y-4">
          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
            <h4 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">
              Session Information
            </h4>
            <div className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
              <p>Current session is secured with JWT authentication</p>
              <p>Session expires after 24 hours of inactivity</p>
              <p>All API communications are encrypted</p>
            </div>
          </div>

          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2">
              Data Privacy
            </h4>
            <div className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
              <p>Your documents and data are stored locally</p>
              <p>Agent tasks are processed securely</p>
              <p>No data is shared with third parties</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return renderProfileTab();
      case 'appearance':
        return renderAppearanceTab();
      case 'agents':
        return renderAgentsTab();
      case 'notifications':
        return renderNotificationsTab();
      case 'security':
        return renderSecurityTab();
      default:
        return renderProfileTab();
    }
  };

  return (
    <div className="h-full flex bg-gray-50 dark:bg-gray-900">
      {/* Settings Navigation */}
      <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Settings
          </h2>
        </div>
        <nav className="p-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <Icon className="h-5 w-5 mr-3" />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Settings Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-6">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}