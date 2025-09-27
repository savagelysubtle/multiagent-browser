import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional, List
import mimetypes

import gradio as gr
from gradio.components import Component

from ..webui_manager import WebuiManager
from ...utils import llm_provider
from ...database import DocumentPipeline, DatabaseUtils

logger = logging.getLogger(__name__)

# Supported file formats
SUPPORTED_FORMATS = {
    '.txt': 'text',
    '.md': 'markdown',
    '.py': 'python',
    '.js': 'javascript',
    '.html': 'html',
    '.css': 'css',
    '.json': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.sql': 'sql',
    '.sh': 'shell',
    '.bat': 'batch',
    '.ps1': 'powershell'
}

class DocumentEditorManager:
    """Manages document editing operations and state."""

    def __init__(self):
        self.current_file_path: Optional[str] = None
        self.current_content: str = ""
        self.working_directory: str = "./tmp/documents"
        self.auto_save_enabled: bool = True
        self.backup_directory: str = "./tmp/document_backups"
        self.recent_files: List[str] = []
        self.max_recent_files: int = 10

        # Database integration
        self.document_pipeline = DocumentPipeline()
        self.db_utils = DatabaseUtils()
        self.auto_store_to_db: bool = True

        # Create directories
        os.makedirs(self.working_directory, exist_ok=True)
        os.makedirs(self.backup_directory, exist_ok=True)

    def get_file_language(self, file_path: str) -> str:
        """Get language for syntax highlighting based on file extension."""
        ext = Path(file_path).suffix.lower()
        return SUPPORTED_FORMATS.get(ext, 'text')

    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_FORMATS

    def read_file(self, file_path: str) -> tuple[str, str]:
        """Read file content and return content and language."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Security check - ensure file is within working directory
            abs_file_path = os.path.abspath(file_path)
            abs_working_dir = os.path.abspath(self.working_directory)
            if not abs_file_path.startswith(abs_working_dir):
                # Allow reading from common document directories
                allowed_dirs = [
                    os.path.abspath("./"),
                    os.path.abspath("./src"),
                    os.path.abspath("./docs"),
                    os.path.abspath("./examples")
                ]
                if not any(abs_file_path.startswith(d) for d in allowed_dirs):
                    raise PermissionError(f"Access denied: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            language = self.get_file_language(file_path)
            self.current_file_path = file_path
            self.current_content = content
            self.add_to_recent_files(file_path)

            return content, language

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise e

    def save_file(self, file_path: str, content: str, create_backup: bool = True) -> bool:
        """Save content to file with optional backup and database storage."""
        try:
            # Security check
            abs_file_path = os.path.abspath(file_path)
            abs_working_dir = os.path.abspath(self.working_directory)
            if not abs_file_path.startswith(abs_working_dir):
                raise PermissionError(f"Can only save to working directory: {file_path}")

            # Create backup if file exists and backup is enabled
            if create_backup and os.path.exists(file_path):
                self.create_backup(file_path)

            # Ensure directory exists
            os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.current_file_path = file_path
            self.current_content = content
            self.add_to_recent_files(file_path)

            # Store in database if enabled
            if self.auto_store_to_db:
                try:
                    success, message, doc_model = self.document_pipeline.process_document_from_editor(
                        content=content,
                        file_path=file_path,
                        document_type=self.get_file_language(file_path),
                        metadata={
                            "saved_from_editor": True,
                            "working_directory": self.working_directory
                        }
                    )
                    if success:
                        logger.info(f"Document stored in database: {message}")
                    else:
                        logger.warning(f"Failed to store in database: {message}")
                except Exception as db_error:
                    logger.error(f"Database storage error: {db_error}")

            logger.info(f"File saved: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving file {file_path}: {e}")
            return False

    def create_backup(self, file_path: str) -> str:
        """Create a backup of the file."""
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            backup_name = f"{filename}.{timestamp}.bak"
            backup_path = os.path.join(self.backup_directory, backup_name)

            with open(file_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            logger.info(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Error creating backup for {file_path}: {e}")
            return ""

    def add_to_recent_files(self, file_path: str):
        """Add file to recent files list."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.max_recent_files]

    def list_files(self, directory: str = None) -> List[str]:
        """List files in directory."""
        if directory is None:
            directory = self.working_directory

        try:
            files = []
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if self.is_supported_format(filename):
                        file_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_path, directory)
                        files.append(rel_path)
            return sorted(files)
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []

    def search_related_documents(self, query: str, limit: int = 5) -> Dict[str, List]:
        """Search for related documents in the database."""
        try:
            results = self.document_pipeline.search_documents(
                query=query,
                collection_type="documents",
                include_relations=True,
                limit=limit
            )

            return {
                "documents": [
                    {
                        "id": result.id,
                        "content_preview": result.content[:200] + "...",
                        "metadata": result.metadata,
                        "relevance_score": result.relevance_score
                    }
                    for result in results
                ]
            }
        except Exception as e:
            logger.error(f"Error searching related documents: {e}")
            return {"documents": []}

    def get_document_suggestions(self, content: str, document_type: str = "document") -> Dict[str, Any]:
        """Get suggestions for policies, templates, and related documents."""
        try:
            suggestions = self.document_pipeline.get_document_suggestions(
                content=content,
                document_type=document_type
            )

            # Format suggestions for UI display
            formatted_suggestions = {}
            for category, results in suggestions.items():
                formatted_suggestions[category] = [
                    {
                        "id": result.id,
                        "title": result.metadata.get("title", result.metadata.get("filename", "Untitled")),
                        "content_preview": result.content[:150] + "...",
                        "relevance_score": result.relevance_score,
                        "metadata": result.metadata
                    }
                    for result in results
                ]

            return formatted_suggestions
        except Exception as e:
            logger.error(f"Error getting document suggestions: {e}")
            return {}

    def store_policy_manual(self, title: str, content: str, policy_type: str = "manual") -> bool:
        """Store a policy manual in the database."""
        try:
            success, message = self.document_pipeline.store_policy_manual(
                title=title,
                content=content,
                policy_type=policy_type,
                authority_level="high",
                metadata={"source": "document_editor"}
            )
            if success:
                logger.info(f"Policy manual stored: {message}")
            else:
                logger.error(f"Failed to store policy manual: {message}")
            return success
        except Exception as e:
            logger.error(f"Error storing policy manual: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            return self.document_pipeline.get_collection_stats()
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

async def handle_file_open(webui_manager: WebuiManager, file_path: str):
    """Handle opening a file."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        content, language = webui_manager.de_manager.read_file(file_path)

        editor_comp = webui_manager.get_component_by_id("document_editor.editor")
        file_path_comp = webui_manager.get_component_by_id("document_editor.current_file_path")
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            editor_comp: gr.Code(value=content, language=language, interactive=True),
            file_path_comp: gr.Textbox(value=file_path),
            status_comp: gr.Textbox(value=f"Opened: {file_path}")
        }, f"File opened: {file_path}"

    except Exception as e:
        logger.error(f"Error opening file {file_path}: {e}")
        return {}, f"Error opening file: {str(e)}"

async def handle_file_save(webui_manager: WebuiManager, content: str, file_path: str):
    """Handle saving a file."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        if not file_path:
            return {}, "No file path specified"

        success = webui_manager.de_manager.save_file(file_path, content)
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        if success:
            return {
                status_comp: gr.Textbox(value=f"Saved: {file_path}")
            }, f"File saved: {file_path}"
        else:
            return {
                status_comp: gr.Textbox(value=f"Error saving: {file_path}")
            }, f"Error saving file: {file_path}"

    except Exception as e:
        logger.error(f"Error saving file {file_path}: {e}")
        return {}, f"Error saving file: {str(e)}"

async def handle_new_file(webui_manager: WebuiManager, filename: str, file_type: str):
    """Handle creating a new file."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        if not filename:
            return {}, "Filename is required"

        # Add extension based on file type
        if not filename.endswith(tuple(SUPPORTED_FORMATS.keys())):
            if file_type == "python":
                filename += ".py"
            elif file_type == "markdown":
                filename += ".md"
            elif file_type == "javascript":
                filename += ".js"
            elif file_type == "html":
                filename += ".html"
            elif file_type == "css":
                filename += ".css"
            elif file_type == "json":
                filename += ".json"
            else:
                filename += ".txt"

        file_path = os.path.join(webui_manager.de_manager.working_directory, filename)

        # Create basic template based on file type
        template_content = ""
        if file_type == "python":
            template_content = "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n"
        elif file_type == "markdown":
            template_content = "# Document Title\n\n"
        elif file_type == "html":
            template_content = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Document</title>\n</head>\n<body>\n    \n</body>\n</html>"
        elif file_type == "javascript":
            template_content = "// JavaScript Document\n\n"
        elif file_type == "css":
            template_content = "/* CSS Stylesheet */\n\n"
        elif file_type == "json":
            template_content = "{\n    \n}"

        success = webui_manager.de_manager.save_file(file_path, template_content)

        if success:
            content, language = webui_manager.de_manager.read_file(file_path)

            editor_comp = webui_manager.get_component_by_id("document_editor.editor")
            file_path_comp = webui_manager.get_component_by_id("document_editor.current_file_path")
            status_comp = webui_manager.get_component_by_id("document_editor.status")

            return {
                editor_comp: gr.Code(value=content, language=language, interactive=True),
                file_path_comp: gr.Textbox(value=file_path),
                status_comp: gr.Textbox(value=f"Created: {filename}")
            }, f"File created: {filename}"
        else:
            return {}, f"Error creating file: {filename}"

    except Exception as e:
        logger.error(f"Error creating file {filename}: {e}")
        return {}, f"Error creating file: {str(e)}"

async def handle_agent_edit(webui_manager: WebuiManager, components: Dict[Component, Any]):
    """Handle agent-assisted editing."""
    try:
        # Get current content and file
        editor_comp = webui_manager.get_component_by_id("document_editor.editor")
        current_content = components.get(editor_comp, "")

        file_path_comp = webui_manager.get_component_by_id("document_editor.current_file_path")
        current_file = components.get(file_path_comp, "")

        agent_instruction_comp = webui_manager.get_component_by_id("document_editor.agent_instruction")
        instruction = components.get(agent_instruction_comp, "").strip()

        if not instruction:
            return {}, "Please provide an instruction for the agent"

        if not current_content:
            return {}, "No document content to edit"

        # Get LLM settings from agent_settings tab
        def get_setting(key, default=None):
            comp = webui_manager.id_to_component.get(f"agent_settings.{key}")
            return components.get(comp, default) if comp else default

        llm_provider_name = get_setting("llm_provider")
        llm_model_name = get_setting("llm_model_name")
        llm_temperature = get_setting("llm_temperature", 0.3)  # Lower temp for editing
        llm_base_url = get_setting("llm_base_url")
        llm_api_key = get_setting("llm_api_key")
        ollama_num_ctx = get_setting("ollama_num_ctx", 16000)

        # Initialize LLM if settings available
        if llm_provider_name and llm_model_name:
            try:
                llm = llm_provider.get_llm_model(
                    provider=llm_provider_name,
                    model_name=llm_model_name,
                    temperature=llm_temperature,
                    base_url=llm_base_url or None,
                    api_key=llm_api_key or None,
                    num_ctx=ollama_num_ctx if llm_provider_name == "ollama" else None,
                )

                # Get file language for context
                language = webui_manager.de_manager.get_file_language(current_file) if current_file else 'text'

                # Create system prompt for document editing
                system_prompt = f"""You are a helpful assistant specialized in editing documents.

Current document type: {language}
File: {current_file if current_file else 'Untitled'}

Instructions:
1. Follow the user's editing instruction precisely
2. Maintain the document's structure and formatting
3. For code files, preserve syntax and functionality
4. For markdown, maintain proper formatting
5. Return ONLY the edited content, no explanations
6. If the instruction is unclear, make reasonable assumptions

User instruction: {instruction}

Original content:
{current_content}

Provide the edited content:"""

                # Get response from LLM
                response = llm.invoke(system_prompt)
                if hasattr(response, 'content'):
                    new_content = response.content.strip()
                else:
                    new_content = str(response).strip()

                # Clean up the response (remove any markdown code blocks if present)
                if new_content.startswith('```'):
                    lines = new_content.split('\n')
                    if len(lines) > 2:
                        new_content = '\n'.join(lines[1:-1])

                status_comp = webui_manager.get_component_by_id("document_editor.status")

                return {
                    editor_comp: gr.Code(value=new_content, language=language, interactive=True),
                    agent_instruction_comp: gr.Textbox(value=""),
                    status_comp: gr.Textbox(value=f"Agent edit applied using {llm_model_name}")
                }, f"Agent edit applied using {llm_model_name}"

            except Exception as e:
                logger.error(f"Error using LLM for editing: {e}")
                # Fallback to simple comment addition
                pass

        # Fallback: Simple demonstration - add instruction as comment
        language = webui_manager.de_manager.get_file_language(current_file) if current_file else 'text'

        if language == 'python':
            comment_prefix = "#"
        elif language in ['javascript', 'css', 'java']:
            comment_prefix = "//"
        elif language == 'html':
            comment_prefix = "<!--"
            comment_suffix = "-->"
        else:
            comment_prefix = "#"

        # Simple demonstration - add instruction as comment
        if language == 'html':
            new_content = f"{current_content}\n\n<!-- Agent instruction: {instruction} -->"
        else:
            new_content = f"{current_content}\n\n{comment_prefix} Agent instruction: {instruction}"

        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            editor_comp: gr.Code(value=new_content, language=language, interactive=True),
            agent_instruction_comp: gr.Textbox(value=""),
            status_comp: gr.Textbox(value="Agent edit applied (demo - configure LLM in settings)")
        }, "Agent edit applied (demo mode)"

    except Exception as e:
        logger.error(f"Error in agent edit: {e}")
        return {}, f"Error in agent edit: {str(e)}"

async def handle_refresh_files(webui_manager: WebuiManager):
    """Handle refreshing the file list."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        files = webui_manager.de_manager.list_files()
        recent_files = webui_manager.de_manager.recent_files

        # Create file list markdown
        files_md = "**Available Files**\n"
        if files:
            for file in files[:10]:  # Show max 10 files
                files_md += f"- `{file}`\n"
            if len(files) > 10:
                files_md += f"... and {len(files) - 10} more files\n"
        else:
            files_md += "*No files found*\n"

        # Create recent files markdown
        recent_md = "**Recent Files**\n"
        if recent_files:
            for file in recent_files[:5]:  # Show max 5 recent
                filename = os.path.basename(file)
                recent_md += f"- `{filename}`\n"
        else:
            recent_md += "*No recent files*\n"

        combined_md = files_md + "\n" + recent_md

        recent_files_comp = webui_manager.get_component_by_id("document_editor.recent_files_display")
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            recent_files_comp: gr.Markdown(value=combined_md),
            status_comp: gr.Textbox(value=f"Found {len(files)} files")
        }, f"File list refreshed: {len(files)} files found"

    except Exception as e:
        logger.error(f"Error refreshing files: {e}")
        return {}, f"Error refreshing files: {str(e)}"

async def handle_open_example(webui_manager: WebuiManager, example_file: str):
    """Handle opening an example file."""
    try:
        example_path = f"./tmp/documents/examples/{example_file}"
        return await handle_file_open(webui_manager, example_path)
    except Exception as e:
        logger.error(f"Error opening example {example_file}: {e}")
        return {}, f"Error opening example: {str(e)}"

async def handle_search_documents(webui_manager: WebuiManager, search_query: str):
    """Handle searching for related documents."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        if not search_query.strip():
            return {}, "Please enter a search query"

        results = webui_manager.de_manager.search_related_documents(search_query, limit=8)

        # Format results for display
        if results["documents"]:
            results_md = "**🔍 Search Results**\n\n"
            for i, doc in enumerate(results["documents"][:5], 1):
                title = doc["metadata"].get("filename", doc["id"])
                score = f"{doc['relevance_score']:.3f}"
                results_md += f"{i}. **{title}** (Score: {score})\n"
                results_md += f"   *{doc['content_preview']}*\n\n"
        else:
            results_md = "**🔍 Search Results**\n\n*No documents found matching your query.*"

        search_results_comp = webui_manager.get_component_by_id("document_editor.search_results")
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            search_results_comp: gr.Markdown(value=results_md),
            status_comp: gr.Textbox(value=f"Found {len(results['documents'])} documents")
        }, f"Search completed: {len(results['documents'])} documents found"

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return {}, f"Error searching documents: {str(e)}"

async def handle_get_suggestions(webui_manager: WebuiManager, content: str, current_file: str):
    """Handle getting document suggestions based on current content."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        if not content.strip():
            return {}, "No content to analyze for suggestions"

        # Determine document type from file extension
        document_type = "document"
        if current_file:
            document_type = webui_manager.de_manager.get_file_language(current_file)

        suggestions = webui_manager.de_manager.get_document_suggestions(content, document_type)

        # Format suggestions for display
        suggestions_md = "**💡 Document Suggestions**\n\n"

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

        if not any(suggestions.values()):
            suggestions_md += "*No suggestions available. Try saving some documents first.*"

        suggestions_comp = webui_manager.get_component_by_id("document_editor.suggestions_display")
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        total_suggestions = sum(len(v) for v in suggestions.values())
        return {
            suggestions_comp: gr.Markdown(value=suggestions_md),
            status_comp: gr.Textbox(value=f"Generated {total_suggestions} suggestions")
        }, f"Suggestions generated: {total_suggestions} items"

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {}, f"Error getting suggestions: {str(e)}"

async def handle_store_as_policy(webui_manager: WebuiManager, content: str, policy_title: str, policy_type: str):
    """Handle storing current document as a policy manual."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        if not content.strip():
            return {}, "No content to store as policy"

        if not policy_title.strip():
            return {}, "Policy title is required"

        success = webui_manager.de_manager.store_policy_manual(
            title=policy_title,
            content=content,
            policy_type=policy_type
        )

        status_comp = webui_manager.get_component_by_id("document_editor.status")

        if success:
            return {
                status_comp: gr.Textbox(value=f"Stored as policy: {policy_title}")
            }, f"Policy stored successfully: {policy_title}"
        else:
            return {
                status_comp: gr.Textbox(value=f"Failed to store policy: {policy_title}")
            }, f"Error storing policy: {policy_title}"

    except Exception as e:
        logger.error(f"Error storing policy: {e}")
        return {}, f"Error storing policy: {str(e)}"

def create_document_editor_tab(webui_manager: WebuiManager):
    """Create the document editor tab."""
    webui_manager.init_document_editor()

    tab_components = {}

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📁 File Manager")

            # New file section
            with gr.Group():
                gr.Markdown("**Create New File**")
                with gr.Row():
                    new_filename = gr.Textbox(
                        label="Filename",
                        placeholder="my_document.md",
                        interactive=True
                    )
                    new_file_type = gr.Dropdown(
                        label="Type",
                        choices=["text", "markdown", "python", "javascript", "html", "css", "json"],
                        value="markdown",
                        interactive=True
                    )
                create_file_btn = gr.Button("📄 Create", variant="primary")

            # File browser
            with gr.Group():
                gr.Markdown("**Open Existing File**")
                file_path_input = gr.Textbox(
                    label="File Path",
                    placeholder="./tmp/documents/examples/sample.md",
                    interactive=True
                )
                with gr.Row():
                    open_file_btn = gr.Button("📂 Open", variant="secondary", scale=2)
                    refresh_files_btn = gr.Button("🔄 Refresh", variant="secondary", scale=1)

                # Recent files and file listing
                recent_files_display = gr.Markdown("**Files**\n*Click refresh to load files*")

            # Database Search Section
            with gr.Group():
                gr.Markdown("**🔍 Document Search**")
                search_query_input = gr.Textbox(
                    label="Search Query",
                    placeholder="Search for related documents...",
                    interactive=True
                )
                search_documents_btn = gr.Button("🔍 Search Database", variant="secondary")
                search_results = gr.Markdown("**Search Results**\n*Enter a query to search documents*")

            # Example files section
            with gr.Group():
                gr.Markdown("**📚 Example Files**")
                example_files_list = gr.Dropdown(
                    label="Choose example",
                    choices=["sample.md", "sample.py", "sample.json"],
                    value="sample.md",
                    interactive=True
                )
                open_example_btn = gr.Button("📖 Open Example", variant="secondary")

        with gr.Column(scale=3):
            gr.Markdown("### ✏️ Document Editor")

            # Current file display
            current_file_path = gr.Textbox(
                label="Current File",
                interactive=False,
                visible=True
            )

            # Main editor
            editor = gr.Code(
                label="Document Content",
                language="markdown",
                interactive=True,
                lines=20
            )

            # Control buttons
            with gr.Row():
                save_btn = gr.Button("💾 Save", variant="primary")
                auto_save_toggle = gr.Checkbox(
                    label="Auto-save",
                    value=True,
                    interactive=True
                )

            # Agent integration
            with gr.Group():
                gr.Markdown("### 🤖 Agent Assistant")
                agent_instruction = gr.Textbox(
                    label="Agent Instruction",
                    placeholder="e.g., 'Add documentation comments to this Python code'",
                    lines=2,
                    interactive=True
                )
                with gr.Row():
                    agent_edit_btn = gr.Button("🔧 Apply Agent Edit", variant="secondary", scale=2)
                    get_suggestions_btn = gr.Button("💡 Get Suggestions", variant="secondary", scale=1)

            # Database Integration
            with gr.Group():
                gr.Markdown("### 📊 Database Features")

                # Document suggestions
                suggestions_display = gr.Markdown("**💡 Suggestions**\n*Edit content and click 'Get Suggestions' for related documents*")

                # Policy storage
                with gr.Row():
                    policy_title_input = gr.Textbox(
                        label="Policy Title",
                        placeholder="Enter title to store as policy...",
                        interactive=True,
                        scale=3
                    )
                    policy_type_dropdown = gr.Dropdown(
                        label="Type",
                        choices=["manual", "template", "guideline", "procedure"],
                        value="manual",
                        interactive=True,
                        scale=1
                    )
                store_policy_btn = gr.Button("📋 Store as Policy", variant="secondary")

            # Status and feedback
            status = gr.Textbox(
                label="Status",
                value="Ready - Try opening an example file or creating a new one",
                interactive=False,
                lines=2
            )

    # Store components
    tab_components.update({
        "new_filename": new_filename,
        "new_file_type": new_file_type,
        "create_file_btn": create_file_btn,
        "file_path_input": file_path_input,
        "open_file_btn": open_file_btn,
        "refresh_files_btn": refresh_files_btn,
        "recent_files_display": recent_files_display,
        "search_query_input": search_query_input,
        "search_documents_btn": search_documents_btn,
        "search_results": search_results,
        "example_files_list": example_files_list,
        "open_example_btn": open_example_btn,
        "current_file_path": current_file_path,
        "editor": editor,
        "save_btn": save_btn,
        "auto_save_toggle": auto_save_toggle,
        "agent_instruction": agent_instruction,
        "agent_edit_btn": agent_edit_btn,
        "get_suggestions_btn": get_suggestions_btn,
        "suggestions_display": suggestions_display,
        "policy_title_input": policy_title_input,
        "policy_type_dropdown": policy_type_dropdown,
        "store_policy_btn": store_policy_btn,
        "status": status
    })

    webui_manager.add_components("document_editor", tab_components)

    # Get all managed components for event handling
    all_managed_components = set(webui_manager.get_components())
    tab_outputs = list(tab_components.values())

    # Event handlers
    async def open_file_wrapper(file_path: str) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for file open."""
        update_dict, message = await handle_file_open(webui_manager, file_path)
        if message:
            gr.Info(message)
        yield update_dict

    async def save_file_wrapper(content: str, file_path: str) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for file save."""
        update_dict, message = await handle_file_save(webui_manager, content, file_path)
        if message:
            gr.Info(message)
        yield update_dict

    async def create_file_wrapper(filename: str, file_type: str) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for file creation."""
        update_dict, message = await handle_new_file(webui_manager, filename, file_type)
        if message:
            gr.Info(message)
        yield update_dict

    async def agent_edit_wrapper(components_dict: Dict[Component, Any]) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for agent edit."""
        update_dict, message = await handle_agent_edit(webui_manager, components_dict)
        if message:
            gr.Info(message)
        yield update_dict

    async def refresh_files_wrapper() -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for refreshing file list."""
        update_dict, message = await handle_refresh_files(webui_manager)
        if message:
            gr.Info(message)
        yield update_dict

    async def open_example_wrapper(example_file: str) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for opening an example file."""
        update_dict, message = await handle_open_example(webui_manager, example_file)
        if message:
            gr.Info(message)
        yield update_dict

    async def search_documents_wrapper(search_query: str) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for searching documents."""
        update_dict, message = await handle_search_documents(webui_manager, search_query)
        if message:
            gr.Info(message)
        yield update_dict

    async def get_suggestions_wrapper(content: str, current_file: str) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for getting document suggestions."""
        update_dict, message = await handle_get_suggestions(webui_manager, content, current_file)
        if message:
            gr.Info(message)
        yield update_dict

    async def store_policy_wrapper(content: str, policy_title: str, policy_type: str) -> AsyncGenerator[Dict[Component, Any], None]:
        """Wrapper for storing document as policy."""
        update_dict, message = await handle_store_as_policy(webui_manager, content, policy_title, policy_type)
        if message:
            gr.Info(message)
        yield update_dict

    # Connect event handlers
    open_file_btn.click(
        fn=open_file_wrapper,
        inputs=[file_path_input],
        outputs=tab_outputs
    )

    save_btn.click(
        fn=save_file_wrapper,
        inputs=[editor, current_file_path],
        outputs=tab_outputs
    )

    create_file_btn.click(
        fn=create_file_wrapper,
        inputs=[new_filename, new_file_type],
        outputs=tab_outputs
    )

    agent_edit_btn.click(
        fn=agent_edit_wrapper,
        inputs=all_managed_components,
        outputs=tab_outputs
    )

    refresh_files_btn.click(
        fn=refresh_files_wrapper,
        outputs=tab_outputs
    )

    open_example_btn.click(
        fn=open_example_wrapper,
        inputs=[example_files_list],
        outputs=tab_outputs
    )

    # Database feature event handlers
    search_documents_btn.click(
        fn=search_documents_wrapper,
        inputs=[search_query_input],
        outputs=tab_outputs
    )

    get_suggestions_btn.click(
        fn=get_suggestions_wrapper,
        inputs=[editor, current_file_path],
        outputs=tab_outputs
    )

    store_policy_btn.click(
        fn=store_policy_wrapper,
        inputs=[editor, policy_title_input, policy_type_dropdown],
        outputs=tab_outputs
    )