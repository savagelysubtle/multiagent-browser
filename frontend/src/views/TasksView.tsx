import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { Clock, CheckCircle, XCircle, AlertCircle, Bot, Globe, FileSearch, X } from 'lucide-react';
import { agentService } from '../services/agentService';
import { Task, TaskStatus } from '../types';
import { cn } from '../utils/cn';

export default function TasksView() {
  const queryClient = useQueryClient();

  // Fetch user tasks
  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => agentService.getUserTasks(),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Cancel task mutation
  const cancelTaskMutation = useMutation({
    mutationFn: (taskId: string) => agentService.cancelTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'running':
        return <AlertCircle className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'cancelled':
        return <XCircle className="h-5 w-5 text-gray-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getAgentIcon = (agentType: string) => {
    switch (agentType) {
      case 'document_editor':
        return <FileSearch className="h-6 w-6 text-blue-500" />;
      case 'browser_use':
        return <Globe className="h-6 w-6 text-green-500" />;
      case 'deep_research':
        return <Bot className="h-6 w-6 text-purple-500" />;
      default:
        return <Bot className="h-6 w-6 text-gray-500" />;
    }
  };

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
      case 'running':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400';
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const formatAgentName = (agentType: string) => {
    return agentType
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="h-full p-6 overflow-auto">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
          Agent Tasks
        </h1>

        {!tasks || tasks.length === 0 ? (
          <div className="text-center py-12">
            <Bot className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No tasks yet
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              Start by using one of the agents to create your first task!
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {tasks.map((task: Task) => (
              <div
                key={task.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    {/* Agent Icon */}
                    <div className="flex-shrink-0">
                      {getAgentIcon(task.agent_type)}
                    </div>

                    {/* Task Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                          {formatAgentName(task.agent_type)}
                        </h3>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          {task.action}
                        </span>
                        <span className={cn(
                          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                          getStatusColor(task.status)
                        )}>
                          {task.status}
                        </span>
                      </div>

                      <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400 mb-3">
                        <div className="flex items-center space-x-1">
                          {getStatusIcon(task.status)}
                          <span>
                            Created {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                          </span>
                        </div>
                        {task.completed_at && (
                          <span>
                            • Completed {formatDistanceToNow(new Date(task.completed_at), { addSuffix: true })}
                          </span>
                        )}
                      </div>

                      {/* Progress Bar */}
                      {task.progress && task.status === 'running' && (
                        <div className="mb-3">
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="text-gray-700 dark:text-gray-300">
                              {task.progress.message}
                            </span>
                            <span className="text-gray-500 dark:text-gray-400">
                              {task.progress.percentage}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full transition-all duration-300"
                              style={{ width: `${task.progress.percentage}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Error Display */}
                      {task.error && (
                        <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                          <div className="flex items-center">
                            <XCircle className="h-4 w-4 text-red-500 mr-2 flex-shrink-0" />
                            <span className="text-sm text-red-700 dark:text-red-400">
                              {task.error}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Result Display */}
                      {task.result && task.status === 'completed' && (
                        <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
                          <div className="text-sm text-green-700 dark:text-green-400">
                            <strong>Result:</strong>
                            <pre className="mt-1 whitespace-pre-wrap font-mono text-xs">
                              {typeof task.result === 'string'
                                ? task.result
                                : JSON.stringify(task.result, null, 2)
                              }
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex-shrink-0 ml-4">
                    {(task.status === 'pending' || task.status === 'running') && (
                      <button
                        onClick={() => cancelTaskMutation.mutate(task.id)}
                        disabled={cancelTaskMutation.isPending}
                        className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/40 disabled:opacity-50"
                      >
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}