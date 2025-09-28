"""
Integration module connecting DocumentEditingAgent with document editor tab functionality.

This module provides seamless integration between the AI agent and the Gradio-based
document editor interface, enabling enhanced document management capabilities.
"""

from typing import Any

import gradio as gr

from ...utils.logging_config import get_logger
from ...webui.webui_manager import WebuiManager
from .document_agent import DocumentEditingAgent

logger = get_logger(__name__)


class DocumentEditorIntegration:
    """Integration layer between DocumentEditingAgent and document editor UI."""

    def __init__(self, webui_manager: WebuiManager):
        """Initialize the integration layer."""
        self.webui_manager = webui_manager
        self.agent: DocumentEditingAgent | None = None
        self._initialization_task = None

    async def initialize_agent(
        self,
        llm: Any | None = None,
        mcp_config_path: str | None = None,
        llm_provider_name: str | None = None,
        llm_model_name: str | None = None,
        llm_temperature: float = 0.3,
        llm_api_key: str | None = None,
        llm_base_url: str | None = None,
        **llm_kwargs,
    ) -> bool:
        """Initialize the DocumentEditingAgent with LLM provider support."""
        try:
            if self.agent:
                await self.agent.close()

            # Get LLM config from webui_manager if available
            if not llm and hasattr(self.webui_manager, "get_llm_settings"):
                llm_settings = self.webui_manager.get_llm_settings()
                llm_provider_name = llm_provider_name or llm_settings.get("provider")
                llm_model_name = llm_model_name or llm_settings.get("model_name")
                llm_temperature = (
                    llm_temperature
                    if llm_temperature != 0.3
                    else llm_settings.get("temperature", 0.3)
                )
                llm_api_key = llm_api_key or llm_settings.get("api_key")
                llm_base_url = llm_base_url or llm_settings.get("base_url")

            # Set default mcp_config_path if not provided
            if mcp_config_path is None:
                from ...database.config import get_project_root

                mcp_config_path = str(get_project_root() / "data" / "mcp.json")

            self.agent = DocumentEditingAgent(
                llm=llm,
                mcp_config_path=mcp_config_path,
                working_directory=self.webui_manager.de_manager.working_directory
                if self.webui_manager.de_manager
                else "./tmp/documents",
                llm_provider_name=llm_provider_name,
                llm_model_name=llm_model_name,
                llm_temperature=llm_temperature,
                llm_api_key=llm_api_key,
                llm_base_url=llm_base_url,
                **llm_kwargs,
            )

            # Initialize agent with MCP tools and LLM
            success = await self.agent.initialize()
            if success:
                logger.info(
                    "DocumentEditingAgent initialized successfully with MCP tools"
                )
            else:
                logger.warning("DocumentEditingAgent initialized without MCP tools")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize DocumentEditingAgent: {e}")
            return False

    async def enhanced_agent_edit(
        self,
        webui_manager: WebuiManager,
        components: dict[gr.components.Component, Any],
    ) -> tuple[dict[gr.components.Component, Any], str]:
        """Enhanced agent editing using DocumentEditingAgent."""
        try:
            if not self.agent:
                await self.initialize_agent()

            if not self.agent:
                return {}, "DocumentEditingAgent not available"

            # Get current content and file
            editor_comp = webui_manager.get_component_by_id("document_editor.editor")
            current_content = components.get(editor_comp, "")

            file_path_comp = webui_manager.get_component_by_id(
                "document_editor.current_file_path"
            )
            current_file = components.get(file_path_comp, "")

            agent_instruction_comp = webui_manager.get_component_by_id(
                "document_editor.agent_instruction"
            )
            instruction = components.get(agent_instruction_comp, "").strip()

            if not instruction:
                return {}, "Please provide an instruction for the agent"

            if not current_content:
                return {}, "No document content to edit"

            # If we have a current document, try to edit it
            if self.agent.current_document_id or current_file:
                # Try to find document in database by file path
                if current_file and not self.agent.current_document_id:
                    # Search for document by file path
                    search_results = await self.agent.search_documents(
                        query=f"file_path:{current_file}",
                        collection_type="documents",
                        limit=1,
                    )
                    if search_results:
                        document_id = search_results[0]["id"]
                    else:
                        # Create new document from current content
                        filename = (
                            current_file.split("/")[-1]
                            if current_file
                            else "untitled.md"
                        )
                        (
                            success,
                            message,
                            document_id,
                        ) = await self.agent.create_document(
                            filename=filename,
                            content=current_content,
                            document_type=self.webui_manager.de_manager.get_file_language(
                                current_file
                            )
                            if current_file
                            else "text",
                        )
                        if not success:
                            return {}, f"Failed to create document: {message}"
                else:
                    document_id = self.agent.current_document_id

                # Edit the document
                success, message, updated_doc_id = await self.agent.edit_document(
                    document_id=document_id, instruction=instruction, use_llm=True
                )

                if success:
                    # Get the updated content
                    updated_doc = self.agent.chroma_manager.get_document(
                        "documents", updated_doc_id or document_id
                    )
                    if updated_doc:
                        language = (
                            self.webui_manager.de_manager.get_file_language(
                                current_file
                            )
                            if current_file
                            else "text"
                        )

                        status_comp = webui_manager.get_component_by_id(
                            "document_editor.status"
                        )

                        return {
                            editor_comp: gr.Code(
                                value=updated_doc.content,
                                language=language,
                                interactive=True,
                            ),
                            agent_instruction_comp: gr.Textbox(value=""),
                            status_comp: gr.Textbox(
                                value="Document edited successfully using DocumentEditingAgent"
                            ),
                        }, "Document edited successfully using enhanced AI agent"
                else:
                    return {}, f"Agent editing failed: {message}"
            else:
                return {}, "No document context available for editing"

        except Exception as e:
            logger.error(f"Error in enhanced agent edit: {e}")
            return {}, f"Error in agent edit: {str(e)}"

    async def enhanced_document_search(
        self,
        search_query: str,
        collection_type: str = "documents",
        use_mcp_tools: bool = True,
    ) -> tuple[str, str]:
        """Enhanced document search using agent capabilities."""
        try:
            if not self.agent:
                await self.initialize_agent()

            if not self.agent:
                return (
                    "**Search Results**\n\n*DocumentEditingAgent not available*",
                    "Agent not available",
                )

            if not search_query.strip():
                return (
                    "**Search Results**\n\n*Please enter a search query*",
                    "Empty query",
                )

            # Search using agent
            results = await self.agent.search_documents(
                query=search_query,
                collection_type=collection_type,
                limit=10,
                use_mcp_tools=use_mcp_tools,
            )

            # Format results
            if results:
                results_md = "**🔍 Enhanced Search Results**\n\n"
                for i, result in enumerate(results[:8], 1):
                    title = result.get("metadata", {}).get(
                        "filename", result.get("id", "Unknown")
                    )
                    score = f"{result.get('relevance_score', 0):.3f}"
                    source = result.get("source", "database")

                    results_md += (
                        f"{i}. **{title}** (Score: {score}, Source: {source})\n"
                    )

                    content_preview = result.get("content", "")
                    if len(content_preview) > 150:
                        content_preview = content_preview[:150] + "..."
                    results_md += f"   *{content_preview}*\n\n"

                message = f"Found {len(results)} documents using enhanced search"
            else:
                results_md = "**🔍 Enhanced Search Results**\n\n*No documents found matching your query.*"
                message = "No results found"

            return results_md, message

        except Exception as e:
            logger.error(f"Error in enhanced document search: {e}")
            return f"**Search Error**\n\n*{str(e)}*", f"Search error: {str(e)}"

    async def enhanced_get_suggestions(
        self, content: str, current_file: str
    ) -> tuple[str, str]:
        """Get enhanced document suggestions using agent."""
        try:
            if not self.agent:
                await self.initialize_agent()

            if not self.agent:
                return (
                    "**Suggestions**\n\n*DocumentEditingAgent not available*",
                    "Agent not available",
                )

            if not content.strip():
                return "**Suggestions**\n\n*No content to analyze*", "Empty content"

            # Determine document type
            document_type = "document"
            if current_file:
                document_type = self.webui_manager.de_manager.get_file_language(
                    current_file
                )

            # Get suggestions using agent
            suggestions = await self.agent.get_document_suggestions(
                content=content, document_type=document_type
            )

            # Format suggestions
            suggestions_md = "**💡 Enhanced Document Suggestions**\n\n"

            # Database suggestions
            if suggestions.get("related_policies"):
                suggestions_md += "**📋 Related Policies:**\n"
                for policy in suggestions["related_policies"][:3]:
                    title = policy["title"]
                    score = f"{policy['relevance_score']:.3f}"
                    suggestions_md += f"• **{title}** (Score: {score})\n"
                    suggestions_md += f"  *{policy['content_preview']}*\n\n"

            if suggestions.get("similar_documents"):
                suggestions_md += "**📄 Similar Documents:**\n"
                for doc in suggestions["similar_documents"][:3]:
                    title = doc["title"]
                    score = f"{doc['relevance_score']:.3f}"
                    suggestions_md += f"• **{title}** (Score: {score})\n"
                    suggestions_md += f"  *{doc['content_preview']}*\n\n"

            if suggestions.get("templates"):
                suggestions_md += "**📋 Available Templates:**\n"
                for template in suggestions["templates"][:2]:
                    title = template["title"]
                    suggestions_md += f"• **{title}**\n"
                    suggestions_md += f"  *{template['content_preview']}*\n\n"

            # MCP suggestions
            if suggestions.get("mcp_suggestions"):
                suggestions_md += "**🔧 MCP Tool Suggestions:**\n"
                for mcp_suggestion in suggestions["mcp_suggestions"][:2]:
                    title = mcp_suggestion.get("title", "MCP Suggestion")
                    suggestions_md += f"• **{title}**\n"
                    if "description" in mcp_suggestion:
                        suggestions_md += f"  *{mcp_suggestion['description']}*\n\n"

            if not any(suggestions.values()):
                suggestions_md += (
                    "*No suggestions available. Try saving some documents first.*"
                )

            total_suggestions = sum(len(v) for v in suggestions.values())
            message = f"Generated {total_suggestions} enhanced suggestions"

            return suggestions_md, message

        except Exception as e:
            logger.error(f"Error getting enhanced suggestions: {e}")
            return f"**Suggestions Error**\n\n*{str(e)}*", f"Error: {str(e)}"

    async def enhanced_create_document(
        self, filename: str, document_type: str, initial_content: str = ""
    ) -> tuple[dict[gr.components.Component, Any], str]:
        """Create a new document using the agent."""
        try:
            if not self.agent:
                await self.initialize_agent()

            if not self.agent:
                return {}, "DocumentEditingAgent not available"

            if not filename:
                return {}, "Filename is required"

            # Create document using agent
            success, message, document_id = await self.agent.create_document(
                filename=filename, content=initial_content, document_type=document_type
            )

            if success and document_id:
                # Get the created document
                document = self.agent.chroma_manager.get_document(
                    "documents", document_id
                )
                if document:
                    file_path = document.metadata.get("file_path", "")
                    language = self.webui_manager.de_manager.get_file_language(
                        file_path
                    )

                    editor_comp = self.webui_manager.get_component_by_id(
                        "document_editor.editor"
                    )
                    file_path_comp = self.webui_manager.get_component_by_id(
                        "document_editor.current_file_path"
                    )
                    status_comp = self.webui_manager.get_component_by_id(
                        "document_editor.status"
                    )

                    return {
                        editor_comp: gr.Code(
                            value=document.content, language=language, interactive=True
                        ),
                        file_path_comp: gr.Textbox(value=file_path),
                        status_comp: gr.Textbox(
                            value=f"Created with agent: {filename}"
                        ),
                    }, f"Document created successfully: {filename}"
                else:
                    return {}, "Document created but could not retrieve content"
            else:
                return {}, f"Failed to create document: {message}"

        except Exception as e:
            logger.error(f"Error creating document with agent: {e}")
            return {}, f"Error creating document: {str(e)}"

    async def get_agent_status(self) -> dict[str, Any]:
        """Get status information about the agent."""
        try:
            if not self.agent:
                return {
                    "initialized": False,
                    "mcp_tools_available": 0,
                    "message": "Agent not initialized",
                }

            stats = await self.agent.get_database_stats()

            return {
                "initialized": True,
                "mcp_tools_available": len(self.agent.mcp_tools),
                "session_id": self.agent.session_id,
                "current_document": self.agent.current_document_id,
                "database_stats": stats,
                "message": "Agent ready",
            }

        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {
                "initialized": False,
                "error": str(e),
                "message": "Error getting status",
            }

    async def close(self):
        """Close the integration and cleanup resources."""
        try:
            if self.agent:
                await self.agent.close()
                self.agent = None

            logger.info("DocumentEditorIntegration closed")

        except Exception as e:
            logger.error(f"Error closing DocumentEditorIntegration: {e}")


# Integration helper functions for backward compatibility with existing document_editor_tab.py


async def enhanced_agent_edit_handler(
    webui_manager: WebuiManager, components: dict[gr.components.Component, Any]
):
    """Enhanced version of handle_agent_edit that uses DocumentEditingAgent."""
    integration = getattr(webui_manager, "_doc_agent_integration", None)

    if not integration:
        # Initialize integration on first use
        integration = DocumentEditorIntegration(webui_manager)
        webui_manager._doc_agent_integration = integration

        # Initialize with LLM from webui manager if available
        llm = getattr(webui_manager, "llm", None)
        await integration.initialize_agent(llm=llm)

    return await integration.enhanced_agent_edit(webui_manager, components)


async def enhanced_search_handler(webui_manager: WebuiManager, search_query: str):
    """Enhanced version of handle_search_documents that uses DocumentEditingAgent."""
    integration = getattr(webui_manager, "_doc_agent_integration", None)

    if not integration:
        integration = DocumentEditorIntegration(webui_manager)
        webui_manager._doc_agent_integration = integration
        await integration.initialize_agent()

    results_md, message = await integration.enhanced_document_search(search_query)

    search_results_comp = webui_manager.get_component_by_id(
        "document_editor.search_results"
    )
    status_comp = webui_manager.get_component_by_id("document_editor.status")

    return {
        search_results_comp: gr.Markdown(value=results_md),
        status_comp: gr.Textbox(value=message),
    }, message


async def enhanced_suggestions_handler(
    webui_manager: WebuiManager, content: str, current_file: str
):
    """Enhanced version of handle_get_suggestions that uses DocumentEditingAgent."""
    integration = getattr(webui_manager, "_doc_agent_integration", None)

    if not integration:
        integration = DocumentEditorIntegration(webui_manager)
        webui_manager._doc_agent_integration = integration
        await integration.initialize_agent()

    suggestions_md, message = await integration.enhanced_get_suggestions(
        content, current_file
    )

    suggestions_comp = webui_manager.get_component_by_id(
        "document_editor.suggestions_display"
    )
    status_comp = webui_manager.get_component_by_id("document_editor.status")

    return {
        suggestions_comp: gr.Markdown(value=suggestions_md),
        status_comp: gr.Textbox(value=message),
    }, message
