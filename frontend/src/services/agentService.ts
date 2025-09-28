import { api } from '../utils/api';
import { Agent, Task, TaskSubmissionForm } from '../types';

class AgentService {
  async getAvailableAgents(): Promise<Agent[]> {
    const response = await api.get<{ agents: Agent[] }>('/api/agents/available');
    return response.data.agents;
  }

  async executeTask(taskForm: TaskSubmissionForm): Promise<{ task_id: string; status: string; message: string }> {
    const response = await api.post<{ task_id: string; status: string; message: string }>(
      '/api/agents/execute',
      taskForm
    );
    return response.data;
  }

  async getUserTasks(limit: number = 50): Promise<Task[]> {
    const response = await api.get<{ tasks: Task[] }>('/api/agents/tasks', {
      params: { limit }
    });
    return response.data.tasks;
  }

  async getTask(taskId: string): Promise<Task> {
    const response = await api.get<Task>(`/api/agents/tasks/${taskId}`);
    return response.data;
  }

  async cancelTask(taskId: string): Promise<{ message: string }> {
    const response = await api.delete<{ message: string }>(`/api/agents/tasks/${taskId}`);
    return response.data;
  }

  async getAgentStats(): Promise<{
    total_tasks: number;
    active_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    agents_status: Record<string, any>;
  }> {
    const response = await api.get<{
      total_tasks: number;
      active_tasks: number;
      completed_tasks: number;
      failed_tasks: number;
      agents_status: Record<string, any>;
    }>('/api/agents/stats');
    return response.data;
  }

  async checkAgentHealth(): Promise<{ status: string; agents: Record<string, any> }> {
    const response = await api.get<{ status: string; agents: Record<string, any> }>('/api/agents/health');
    return response.data;
  }

  // Helper methods for specific agent actions
  async createDocument(filename: string, content: string, documentType: string = 'markdown'): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'document_editor',
      action: 'create_document',
      payload: { filename, content, document_type: documentType }
    });
  }

  async editDocument(documentId: string, instruction: string): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'document_editor',
      action: 'edit_document',
      payload: { document_id: documentId, instruction }
    });
  }

  async searchDocuments(query: string, limit: number = 10): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'document_editor',
      action: 'search_documents',
      payload: { query, limit }
    });
  }

  async browseUrl(url: string, instruction: string): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'browser_use',
      action: 'browse',
      payload: { url, instruction }
    });
  }

  async extractFromUrl(url: string, selectors: string[]): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'browser_use',
      action: 'extract',
      payload: { url, selectors }
    });
  }

  async takeScreenshot(url: string): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'browser_use',
      action: 'screenshot',
      payload: { url }
    });
  }

  async conductResearch(
    topic: string,
    depth: 'quick' | 'standard' | 'comprehensive' = 'standard',
    sources?: string[]
  ): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'deep_research',
      action: 'research',
      payload: { topic, depth, sources }
    });
  }

  async analyzeSources(sources: string[]): Promise<{ task_id: string }> {
    return this.executeTask({
      agent_type: 'deep_research',
      action: 'analyze_sources',
      payload: { sources }
    });
  }
}

export const agentService = new AgentService();