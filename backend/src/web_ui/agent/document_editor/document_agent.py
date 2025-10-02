"""
Document Editing Agent with ChromaDB MCP Integration.

This agent handles document editing operations, integrates with the database pipeline,
and uses ChromaDB MCP tools for advanced document management.
"""

import asyncio
import json
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ...database import (
    ChromaManager,
    DatabaseUtils,
    DocumentPipeline,
    MCPConfigManager,
)
from ...utils import config, llm_provider
from ...utils.logging_config import get_logger
from ...utils.mcp_client import setup_mcp_client_and_tools

logger = get_logger(__name__)


class DocumentEditingAgent:
    """
    Advanced document editing agent with ChromaDB MCP integration.

    Features:
    - Document CRUD operations with database persistence
    - AI-powered document editing and suggestions
    - Integration with ChromaDB MCP tools
    - Policy and template management
    - Advanced search and relation discovery
    """

    def __init__(
        self,
        llm: Any | None = None,
        mcp_config_path: str | None = None,
        working_directory: str = "./tmp/documents",
        llm_provider_name: str | None = None,
        llm_model_name: str | None = None,
        llm_temperature: float = 0.3,
        llm_api_key: str | None = None,
        llm_base_url: str | None = None,
        **llm_kwargs,
    ):
        """Initialize the Document Editing Agent."""
        self.llm = llm
        self.mcp_config_path = mcp_config_path
        self.working_directory = working_directory

        # LLM configuration
        self.llm_provider_name = llm_provider_name
        self.llm_model_name = llm_model_name
        self.llm_temperature = llm_temperature
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url
        self.llm_kwargs = llm_kwargs

        # Database components
        self.chroma_manager = ChromaManager()
        self.document_pipeline = DocumentPipeline()
        self.database_utils = DatabaseUtils()
        self.mcp_config_manager = MCPConfigManager(self.document_pipeline)

        # MCP client and tools
        self.mcp_client = None
        self.mcp_tools = []
        self.agent_executor: AgentExecutor | None = None # Initialize agent_executor

        # Agent state
        self.current_document_id: str | None = None
        self.session_id = str(uuid.uuid4())

        # Ensure working directory exists
        os.makedirs(working_directory, exist_ok=True)

        self.logger = get_logger(__name__)
        self.logger.info(f"DocumentEditingAgent initialized with session: {self.session_id}")

    async def initialize(self) -> bool:
        """Initialize MCP client, tools, and LLM if needed."""
        try:
            # Initialize LLM if not provided but configuration is available
            if not self.llm and self.llm_provider_name:
                await self.setup_llm()

            # Load MCP configuration
            mcp_config = await self._load_mcp_config()
            if not mcp_config:
                self.logger.warning(
                    "No MCP configuration found, running with basic database tools only"
                )
                return False

            # Setup MCP client with Chroma tools
            if "chroma" in mcp_config.get("mcpServers", {}):
                chroma_config = mcp_config["mcpServers"]["chroma"]
                self.logger.info(f"Setting up ChromaDB MCP client: {chroma_config}")

                self.mcp_client = await setup_mcp_client_and_tools(
                    {"chroma": chroma_config}
                )

                if self.mcp_client:
                    self.mcp_tools = self.mcp_client.get_tools()
                    self.logger.info(f"Loaded {len(self.mcp_tools)} MCP tools")
                    self._setup_llm_with_tools() # Setup LLM with tools after loading them
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to initialize MCP client: {e}")
            return False

    async def setup_llm(
        self,
        provider_name: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ) -> bool:
        """Setup or reconfigure the LLM using the provider system."""
        try:
            # Use provided params or fall back to instance config
            provider = provider_name or self.llm_provider_name
            model = model_name or self.llm_model_name
            temp = temperature if temperature is not None else self.llm_temperature
            key = api_key or self.llm_api_key
            url = base_url or self.llm_base_url

            if not provider:
                self.logger.warning("No LLM provider specified")
                return False

            if not model:
                # Use default model for provider
                default_models = config.model_names.get(provider, [])
                model = default_models[0] if default_models else "default"

            # Prepare LLM kwargs
            llm_config = {
                "model_name": model,
                "temperature": temp,
                **self.llm_kwargs,
                **kwargs,
            }

            if key:
                llm_config["api_key"] = key
            if url:
                llm_config["base_url"] = url

            # Create LLM using provider
            self.llm = llm_provider.get_llm_model(provider, **llm_config)

            # Update instance config
            self.llm_provider_name = provider
            self.llm_model_name = model
            self.llm_temperature = temp
            self.llm_api_key = key
            self.llm_base_url = url

            self.logger.info(f"LLM configured: {provider}/{model}")
            return True

        except Exception as e:
            self.logger.error(f"Error setting up LLM: {e}")
            return False

    def _setup_llm_with_tools(self):
        """Sets up the LLM with the loaded MCP tools using LangChain's create_react_agent."""
        if not self.llm:
            self.logger.warning("LLM not available, cannot set up tools.")
            return

        if not self.mcp_tools:
            self.logger.warning("No MCP tools loaded, cannot set up tools with LLM.")
            return

        self.logger.info(f"Setting up LLM with {len(self.mcp_tools)} tools.")

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    "You are an AI assistant specialized in document editing and management. "
                    "You can create, edit, and search documents. "
                    "Use the available tools to fulfill user requests. "
                    "Be concise and helpful."
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessage(content="{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Create the ReAct agent
        agent = create_react_agent(self.llm, self.mcp_tools, prompt)

        # Create the AgentExecutor
        self.agent_executor = AgentExecutor(agent=agent, tools=self.mcp_tools, verbose=True)
        self.logger.info("LLM with tools (AgentExecutor) setup complete.")

    def get_available_providers(self) -> dict[str, Any]:
        """Get available LLM providers and their models."""
        return {
            "providers": list(config.PROVIDER_DISPLAY_NAMES.keys()),
            "models_by_provider": config.model_names,
        }

    def get_current_llm_config(self) -> dict[str, Any]:
        """Get current LLM configuration."""
        return {
            "provider": self.llm_provider_name,
            "model": self.llm_model_name,
            "temperature": self.llm_temperature,
            "has_llm": self.llm is not None,
            "base_url": self.llm_base_url,
            "api_key_set": bool(self.llm_api_key),
        }

    async def _load_mcp_config(self) -> dict[str, Any] | None:
        """Load MCP configuration from file or database."""
        try:
            # First try to get active config from database
            active_config = await self.mcp_config_manager.get_active_config()
            if active_config:
                self.logger.info("Using active MCP configuration from database")
                return active_config["config_data"]

            # Fallback to file-based config
            if self.mcp_config_path is None:
                from ...database.config import get_project_root

                self.mcp_config_path = str(get_project_root() / "data" / "mcp.json")

            if os.path.exists(self.mcp_config_path):
                with open(self.mcp_config_path) as f:
                    config_data = json.load(f)
                    self.logger.info(
                        f"Loaded MCP configuration from file: {self.mcp_config_path}"
                    )
                    return config_data

            return None

        except Exception as e:
            self.logger.error(f"Error loading MCP configuration: {e}")
            return None

    async def create_document(
        self,
        filename: str,
        content: str = "",
        document_type: str = "document",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str, str | None]:
        """Create a new document with database persistence."""
        try:
            file_path = os.path.join(self.working_directory, filename)

            # Ensure file has appropriate extension
            if not Path(filename).suffix:
                extension_map = {
                    "python": ".py",
                    "markdown": ".md",
                    "javascript": ".js",
                    "html": ".html",
                    "json": ".json",
                }
                filename += extension_map.get(document_type, ".txt")
                file_path = os.path.join(self.working_directory, filename)

            # Create template content if empty
            if not content:
                content = await self._generate_template_content(document_type, filename)

            # Save file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Store in database
            success, message, doc_model = (
                self.document_pipeline.process_document_from_editor(
                    content=content,
                    file_path=file_path,
                    document_type=document_type,
                    metadata={
                        **(metadata or {}),
                        "created_by_agent": True,
                        "agent_session": self.session_id,
                        "llm_provider": self.llm_provider_name,
                        "llm_model": self.llm_model_name,
                    },
                )
            )

            if success and doc_model:
                self.current_document_id = doc_model.id
                self.logger.info(f"Document created successfully: {filename}")
                return True, f"Document created: {filename}", doc_model.id
            else:
                return False, f"Failed to store document: {message}", None

        except Exception as e:
            self.logger.error(f"Error creating document: {e}")
            return False, f"Error creating document: {str(e)}", None

    async def edit_document(
        self, document_id: str, instruction: str, use_llm: bool = True
    ) -> tuple[bool, str, str | None]:
        """Edit a document using AI assistance and MCP tools."""
        try:
            # Get document from database
            document = self.chroma_manager.get_document("documents", document_id)
            if not document:
                return False, f"Document not found: {document_id}", None

            current_content = document.content

            if use_llm and self.llm:
                # Use LLM for intelligent editing
                new_content = await self._llm_edit_document(
                    content=current_content,
                    instruction=instruction,
                    document_metadata=document.metadata,
                )
            elif use_llm and not self.llm:
                # Try to setup LLM if requested but not available
                if await self.setup_llm():
                    new_content = await self._llm_edit_document(
                        content=current_content,
                        instruction=instruction,
                        document_metadata=document.metadata,
                    )
                else:
                    self.logger.warning(
                        "LLM requested but unavailable, using simple editing"
                    )
                    new_content = await self._simple_edit_document(
                        current_content, instruction
                    )
            else:
                # Simple instruction-based editing
                new_content = await self._simple_edit_document(
                    current_content, instruction
                )

            if new_content and new_content != current_content:
                # Update file on disk
                file_path = document.metadata.get("file_path")
                if file_path and os.path.exists(file_path):
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                # Update in database
                success, message, doc_model = (
                    self.document_pipeline.process_document_from_editor(
                        content=new_content,
                        file_path=file_path
                        or f"{self.working_directory}/updated_{document_id}.txt",
                        document_type=document.metadata.get(
                            "document_type", "document"
                        ),
                        metadata={
                            **document.metadata,
                            "last_edited_by_agent": True,
                            "edit_instruction": instruction,
                            "edit_timestamp": datetime.now().isoformat(),
                            "llm_used": bool(self.llm and use_llm),
                        },
                    )
                )

                if success:
                    return (
                        True,
                        "Document edited successfully",
                        doc_model.id if doc_model else document_id,
                    )
                else:
                    return False, f"Failed to update document: {message}", None
            else:
                return False, "No changes made to document", document_id

        except Exception as e:
            self.logger.error(f"Error editing document: {e}")
            return False, f"Error editing document: {str(e)}", None

    async def _llm_edit_document(
        self, content: str, instruction: str, document_metadata: dict[str, Any]
    ) -> str | None:
        """Use LLM to edit document content."""
        try:
            if not self.llm:
                self.logger.warning("LLM not available for document editing")
                return None

            document_type = document_metadata.get("language", "text")
            filename = document_metadata.get("filename", "document")

            system_prompt = f"""You are an expert document editor specializing in {document_type} content.

Document: {filename}
Type: {document_type}
LLM: {self.llm_provider_name}/{self.llm_model_name}

Instructions:
1. Follow the user's editing instruction precisely
2. Maintain the document's structure and formatting
3. For code files, preserve syntax and functionality
4. For markdown, maintain proper formatting
5. Return ONLY the edited content, no explanations
6. If the instruction is unclear, make reasonable assumptions

User instruction: {instruction}

Original content:
{content}

Provide the edited content:"""

            if hasattr(self.llm, "ainvoke"):
                response = await self.llm.ainvoke(system_prompt)
            else:
                # Fallback for synchronous LLMs
                response = self.llm.invoke(system_prompt)

            if hasattr(response, "content"):
                new_content = response.content.strip()
            else:
                new_content = str(response).strip()

            # Clean up response (remove markdown code blocks if present)
            if new_content.startswith("```"):
                lines = new_content.split("\n")
                if len(lines) > 2:
                    new_content = "\n".join(lines[1:-1])

            return new_content

        except Exception as e:
            self.logger.error(f"Error in LLM document editing: {e}")
            return None

    async def _simple_edit_document(self, content: str, instruction: str) -> str:
        """Simple instruction-based editing without LLM."""
        # Basic instruction processing
        instruction_lower = instruction.lower()

        if "add comment" in instruction_lower:
            return f"{content}\n\n# Note: {instruction}"
        elif "remove" in instruction_lower and "line" in instruction_lower:
            # Simple line removal (demonstration)
            lines = content.split("\n")
            if len(lines) > 1:
                lines.pop()  # Remove last line
                return "\n".join(lines)
        elif "append" in instruction_lower:
            return f"{content}\n\n{instruction.replace('append', '').strip()}"

        return content

    async def search_documents(
        self,
        query: str,
        collection_type: str = "documents",
        limit: int = 10,
        use_mcp_tools: bool = True,
    ) -> list[dict[str, Any]]:
        """Search documents using database and MCP tools."""
        try:
            results = []

            # Search using database pipeline
            search_results = self.document_pipeline.search_documents(
                query=query,
                collection_type=collection_type,
                include_relations=True,
                limit=limit,
            )

            # Convert to dict format
            for result in search_results:
                results.append(
                    {
                        "id": result.id,
                        "content": result.content,
                        "metadata": result.metadata,
                        "relevance_score": result.relevance_score,
                        "source": "database",
                    }
                )

            # Use MCP tools for additional search if available
            if use_mcp_tools and self.mcp_tools:
                mcp_results = await self._search_with_mcp_tools(query, limit)
                results.extend(mcp_results)

            # Sort by relevance score
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

            return results[:limit]

        except Exception as e:
            self.logger.error(f"Error searching documents: {e}")
            return []

    async def _search_with_mcp_tools(
        self, query: str, limit: int
    ) -> list[dict[str, Any]]:
        """Use MCP tools for document search."""
        try:
            results = []

            # Find search tools
            search_tools = [
                tool for tool in self.mcp_tools if "search" in tool.name.lower()
            ]

            for tool in search_tools:
                try:
                    # Attempt to use the search tool
                    tool_result = await tool.ainvoke({"query": query, "limit": limit})

                    # Process tool result
                    if isinstance(tool_result, list):
                        for item in tool_result:
                            results.append(
                                {
                                    **item,
                                    "source": f"mcp_{tool.name}",
                                    "relevance_score": item.get("score", 0.5),
                                }
                            )
                    elif isinstance(tool_result, dict):
                        results.append(
                            {
                                **tool_result,
                                "source": f"mcp_{tool.name}",
                                "relevance_score": tool_result.get("score", 0.5),
                            }
                        )

                except Exception as tool_error:
                    self.logger.warning(f"MCP tool {tool.name} failed: {tool_error}")
                    continue

            return results

        except Exception as e:
            self.logger.error(f"Error using MCP tools for search: {e}")
            return []

    async def get_document_suggestions(
        self, content: str, document_type: str = "document"
    ) -> dict[str, list[dict[str, Any]]]:
        """Get intelligent document suggestions."""
        try:
            # Get suggestions from database pipeline
            suggestions = self.document_pipeline.get_document_suggestions(
                content=content, document_type=document_type
            )

            # Convert search results to dict format
            formatted_suggestions = {}
            for category, results in suggestions.items():
                formatted_suggestions[category] = [
                    {
                        "id": result.id,
                        "title": result.metadata.get(
                            "title", result.metadata.get("filename", "Untitled")
                        ),
                        "content_preview": result.content[:200] + "..."
                        if len(result.content) > 200
                        else result.content,
                        "relevance_score": result.relevance_score,
                        "metadata": result.metadata,
                        "source": "database",
                    }
                    for result in results
                ]

            # Add MCP-based suggestions if available
            if self.mcp_tools:
                mcp_suggestions = await self._get_mcp_suggestions(
                    content, document_type
                )
                if mcp_suggestions:
                    formatted_suggestions["mcp_suggestions"] = mcp_suggestions

            return formatted_suggestions

        except Exception as e:
            self.logger.error(f"Error getting document suggestions: {e}")
            return {}

    async def _get_mcp_suggestions(
        self, content: str, document_type: str
    ) -> list[dict[str, Any]]:
        """Get suggestions using MCP tools."""
        try:
            suggestions = []

            # Find relevant MCP tools for suggestions
            suggestion_tools = [
                tool
                for tool in self.mcp_tools
                if any(
                    keyword in tool.name.lower()
                    for keyword in ["suggest", "recommend", "similar"]
                )
            ]

            for tool in suggestion_tools:
                try:
                    result = await tool.ainvoke(
                        {
                            "content": content[:500],  # Limit content length
                            "type": document_type,
                        }
                    )

                    if isinstance(result, list):
                        suggestions.extend(result)
                    elif isinstance(result, dict):
                        suggestions.append(result)

                except Exception as tool_error:
                    self.logger.warning(
                        f"MCP suggestion tool {tool.name} failed: {tool_error}"
                    )
                    continue

            return suggestions

        except Exception as e:
            self.logger.error(f"Error getting MCP suggestions: {e}")
            return []

    async def store_as_policy(
        self,
        document_id: str,
        policy_title: str,
        policy_type: str = "manual",
        authority_level: str = "medium",
    ) -> tuple[bool, str]:
        """Store document as a policy manual."""
        try:
            # Get document content
            document = self.chroma_manager.get_document("documents", document_id)
            if not document:
                return False, f"Document not found: {document_id}"

            # Store as policy
            success, message = self.document_pipeline.store_policy_manual(
                title=policy_title,
                content=document.content,
                policy_type=policy_type,
                authority_level=authority_level,
                metadata={
                    "original_document_id": document_id,
                    "created_by_agent": True,
                    "agent_session": self.session_id,
                    "llm_provider": self.llm_provider_name,
                    "llm_model": self.llm_model_name,
                },
            )

            return success, message

        except Exception as e:
            self.logger.error(f"Error storing policy: {e}")
            return False, f"Error storing policy: {str(e)}"

    async def _generate_template_content(
        self, document_type: str, filename: str
    ) -> str:
        """Generate template content for new documents."""
        templates = {
            "python": f'#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"""\n{filename}\n\nCreated by DocumentEditingAgent\n"""\n\n',
            "markdown": f"# {Path(filename).stem.replace('_', ' ').title()}\n\nCreated: {datetime.now().strftime('%Y-%m-%d')}\n\n## Overview\n\n",
            "javascript": f"/**\n * {filename}\n * Created by DocumentEditingAgent\n * Date: {datetime.now().strftime('%Y-%m-%d')}\n */\n\n",
            "html": f'<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>{Path(filename).stem}</title>\n</head>\n<body>\n    <h1>{Path(filename).stem}</h1>\n    \n</body>\n</html>',
            "json": '{\n    "name": "'
            + Path(filename).stem
            + '",\n    "created": "'
            + datetime.now().isoformat()
            + '"\n}',
        }

        return templates.get(
            document_type,
            f"# {filename}\n\nCreated by DocumentEditingAgent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        )

    async def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            # Get collection stats from document pipeline
            pipeline_stats = self.document_pipeline.get_collection_stats()

            # Get additional database health info
            health_info = self.database_utils.health_check()

            # Get MCP config stats
            mcp_stats = self.mcp_config_manager.get_collection_stats()

            return {
                "pipeline_stats": pipeline_stats,
                "health_info": health_info,
                "mcp_config_stats": mcp_stats,
                "agent_session": self.session_id,
                "current_document": self.current_document_id,
                "mcp_tools_available": len(self.mcp_tools),
                "llm_config": self.get_current_llm_config(),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

    async def chat(self, message: str, context_document_id: str | None = None) -> str:
        """Handles general chat messages using the LLM."""
        self.logger.info(f"DocumentEditingAgent received chat message: {message}")
        prompt = f"You are an AI assistant specialized in document editing and research. Respond concisely and helpfully.\n\nUser: {message}"

        if context_document_id:
            # In a real scenario, fetch document content and add to prompt
            self.logger.debug(f"Chat with context_document_id: {context_document_id}")
            prompt = f"You are an AI assistant specialized in document editing and research. Respond concisely and helpfully, using the following document context if relevant.\n\nDocument Context: [Document content for {context_document_id}]\n\nUser: {message}"

        response = await self._get_llm_response(prompt)
        self.logger.info(f"DocumentEditingAgent chat response: {response[:100]}...")
        return response

    async def _get_llm_response(self, prompt: str) -> str:
        """Invokes the LLM with the given prompt and returns the response."""
        try:
            if not self.llm:
                self.logger.warning("LLM not available for _get_llm_response")
                return "I'm sorry, but I don't have an LLM configured. Please configure your AI settings first."

            if hasattr(self.llm, "ainvoke"):
                response = await self.llm.ainvoke(prompt)
            else:
                response = self.llm.invoke(prompt)

            if hasattr(response, "content"):
                return response.content.strip()
            else:
                return str(response).strip()
        except Exception as e:
            self.logger.error(f"Error invoking LLM: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"

    async def chat_with_user_stream(
        self, message: str, session_id: str = "default", context_document_id: str | None = None
    ) -> AsyncGenerator[str]:
        """Stream chat responses for real-time interaction."""
        try:
            if not self.agent_executor:
                yield "I'm sorry, but the AI agent is not fully configured. Please check the backend logs."
                return

            # Retrieve chat history for the session
            chat_history = self._get_chat_history_for_session(session_id)

            # Append user's message to history
            chat_history.append(HumanMessage(content=message))

            # Prepare input for the agent executor
            full_response_content = ""
            async for chunk in self.agent_executor.astream({"input": message, "chat_history": chat_history}):
                if "output" in chunk:
                    content_chunk = chunk["output"]
                    full_response_content += content_chunk
                    yield content_chunk
                elif "actions" in chunk:
                    for action in chunk["actions"]:
                        tool_message = f"\n> Tool Used: {action.tool} with input {action.tool_input}\n"
                        full_response_content += tool_message
                        yield tool_message
                elif "steps" in chunk:
                    for step in chunk["steps"]:
                        observation_message = f"\n> Observation: {step.observation}\n"
                        full_response_content += observation_message
                        yield observation_message

            # Append AI's full response to history
            chat_history.append(AIMessage(content=full_response_content))

        except Exception as e:
            self.logger.error(f"Error in streaming chat with agent executor: {e}")
            yield f"I apologize, but I encountered an error: {str(e)}"

    async def process_batch_documents(
        self, file_paths: list[str], document_type: str = "document"
    ) -> dict[str, Any]:
        """Process multiple documents in batch."""
        try:
            results = {"processed": [], "failed": [], "total": len(file_paths)}

            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        success, message, doc_model = (
                            self.document_pipeline.process_document_from_editor(
                                content=content,
                                file_path=file_path,
                                document_type=document_type,
                                metadata={
                                    "batch_processed": True,
                                    "agent_session": self.session_id,
                                    "processed_at": datetime.now().isoformat(),
                                    "llm_provider": self.llm_provider_name,
                                },
                            )
                        )

                        if success and doc_model:
                            results["processed"].append(
                                {
                                    "file_path": file_path,
                                    "document_id": doc_model.id,
                                    "message": message,
                                }
                            )
                        else:
                            results["failed"].append(
                                {"file_path": file_path, "error": message}
                            )
                    else:
                        results["failed"].append(
                            {"file_path": file_path, "error": "File not found"}
                        )

                except Exception as file_error:
                    results["failed"].append(
                        {"file_path": file_path, "error": str(file_error)}
                    )

            self.logger.info(
                f"Batch processing completed: {len(results['processed'])} processed, {len(results['failed'])} failed"
            )
            return results

        except Exception as e:
            self.logger.error(f"Error in batch processing: {e}")
            return {
                "processed": [],
                "failed": file_paths,
                "total": len(file_paths),
                "error": str(e),
            }

    async def close(self):
        """Clean up agent resources."""
        try:
            if self.mcp_client:
                await self.mcp_client.__aexit__(None, None, None)
                self.mcp_client = None

            self.logger.info(f"DocumentEditingAgent session {self.session_id} closed")

        except Exception as e:
            self.logger.error(f"Error closing DocumentEditingAgent: {e}")

    def __del__(self):
        """Ensure cleanup on deletion."""
        if hasattr(self, "mcp_client") and self.mcp_client:
            # Note: Can't use async in __del__, so log a warning
            self.logger.warning(
                f"DocumentEditingAgent session {self.session_id} was not properly closed"
            )
