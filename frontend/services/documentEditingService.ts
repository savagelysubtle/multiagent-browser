/**
 * API service for DocumentEditingAgent integration.
 * 
 * This module provides functions to communicate with the DocumentEditingAgent
 * API server from the React frontend.
 */

import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export interface DocumentCreateRequest {
  filename: string;
  content?: string;
  document_type?: string;
  metadata?: Record<string, any>;
}

export interface DocumentEditRequest {
  document_id: string;
  instruction: string;
  use_llm?: boolean;
}

export interface DocumentSearchRequest {
  query: string;
  collection_type?: string;
  limit?: number;
  use_mcp_tools?: boolean;
}

export interface DocumentSuggestionsRequest {
  content: string;
  document_type?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

/**
 * API service class for DocumentEditingAgent operations
 */
class DocumentEditingService {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Get agent status
   */
  async getAgentStatus() {
    try {
      const response = await axios.get(${this.baseURL}/agent/status);
      return response.data;
    } catch (error) {
      console.error("Error getting agent status:", error);
      throw error;
    }
  }

  /**
   * Create a new document
   */
  async createDocument(request: DocumentCreateRequest) {
    try {
      const response = await axios.post(${this.baseURL}/documents/create, request);
      return response.data;
    } catch (error) {
      console.error("Error creating document:", error);
      throw error;
    }
  }

  /**
   * Edit an existing document
   */
  async editDocument(request: DocumentEditRequest) {
    try {
      const response = await axios.post(${this.baseURL}/documents/edit, request);
      return response.data;
    } catch (error) {
      console.error("Error editing document:", error);
      throw error;
    }
  }

  /**
   * Search documents
   */
  async searchDocuments(request: DocumentSearchRequest) {
    try {
      const response = await axios.post(${this.baseURL}/documents/search, request);
      return response.data;
    } catch (error) {
      console.error("Error searching documents:", error);
      throw error;
    }
  }

  /**
   * Get document suggestions
   */
  async getDocumentSuggestions(request: DocumentSuggestionsRequest) {
    try {
      const response = await axios.post(${this.baseURL}/documents/suggestions, request);
      return response.data;
    } catch (error) {
      console.error("Error getting suggestions:", error);
      throw error;
    }
  }

  /**
   * Get LLM providers and models
   */
  async getLLMProviders() {
    try {
      const response = await axios.get(${this.baseURL}/llm/providers);
      return response.data;
    } catch (error) {
      console.error("Error getting LLM providers:", error);
      throw error;
    }
  }

  /**
   * Get current LLM configuration
   */
  async getLLMConfig() {
    try {
      const response = await axios.get(${this.baseURL}/llm/config);
      return response.data;
    } catch (error) {
      console.error("Error getting LLM config:", error);
      throw error;
    }
  }

  /**
   * Health check
   */
  async healthCheck() {
    try {
      const response = await axios.get(${this.baseURL}/health);
      return response.data;
    } catch (error) {
      console.error("Health check failed:", error);
      throw error;
    }
  }
}

// Export singleton instance
export const documentEditingService = new DocumentEditingService();
export default documentEditingService;
