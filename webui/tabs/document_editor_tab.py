import logging
import os
import uuid
from pathlib import Path
from typing import Any

import gradio as gr
from gradio.components import Component

from ...database import DatabaseUtils, DocumentPipeline
from ...utils import llm_provider
from ..webui_manager import WebuiManager

logger = logging.getLogger(__name__)

# Supported file formats
SUPPORTED_FORMATS = {
    ".txt": "text",
    ".md": "markdown",
    ".py": "python",
    ".js": "javascript",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sql": "sql",
    ".sh": "shell",
    ".bat": "batch",
    ".ps1": "powershell",
}


class DocumentEditorManager:
    """Manages document editing operations and state."""

    def __init__(self):
        self.current_file_path: str | None = None
        self.current_content: str = ""
        self.working_directory: str = "./tmp/documents"
        self.auto_save_enabled: bool = True
        self.backup_directory: str = "./tmp/document_backups"
        self.recent_files: list[str] = []
        self.max_recent_files: int = 10

        # Database integration
        self.document_pipeline = DocumentPipeline()
        self.db_utils = DatabaseUtils()
        self.auto_store_to_db: bool = True

        # Chat integration
        self.chat_history: list[dict[str, str]] = []
        self.chat_enabled: bool = True
        self.max_chat_history: int = 50

        # Create directories
        os.makedirs(self.working_directory, exist_ok=True)
        os.makedirs(self.backup_directory, exist_ok=True)

        # Create examples directory and sample files
        self._create_example_files()

        # Initialize with welcome message
        self._initialize_welcome_message()

    def _initialize_welcome_message(self):
        """Initialize chat with welcome message."""
        welcome_msg = """Hello! I'm your AI assistant. How can I help you with your documents today? You can ask me to edit, or use /search for web search and /research for deep analysis."""
        self.add_chat_message("assistant", welcome_msg)

    def _create_example_files(self):
        """Create example files for demonstration."""
        examples_dir = os.path.join(self.working_directory, "examples")
        os.makedirs(examples_dir, exist_ok=True)

        # Sample markdown file
        sample_md = """# Sample Document

This is a sample markdown document to demonstrate the AI Document Editor.

## Features
- **Document editing** with syntax highlighting
- **AI chat assistant** for writing help
- **Database integration** for document storage
- **Agent assistance** for improvements

## Getting Started
1. Try editing this document
2. Ask the AI assistant for help in the chat
3. Save your changes to the database

Feel free to modify this document and ask for suggestions!
"""

        # Sample Python file
        sample_py = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def greet(name):
    # This function needs better documentation
    return f"Hello, {name}!"

def calculate_area(width, height):
    return width * height

# Main execution
if __name__ == "__main__":
    result = greet("World")
    print(result)

    area = calculate_area(10, 5)
    print(f"Area: {area}")
"""

        # Sample JSON file
        sample_json = """{
  "project": "AI Document Editor",
  "version": "1.0.0",
  "description": "Sample JSON configuration file",
  "features": [
    "Document editing",
    "AI assistance",
    "Database integration",
    "Multi-format support"
  ],
  "settings": {
    "auto_save": true,
    "theme": "dark",
    "language": "en"
  }
}"""

        # Write example files
        examples = [
            ("sample.md", sample_md),
            ("sample.py", sample_py),
            ("sample.json", sample_json),
        ]

        for filename, content in examples:
            file_path = os.path.join(examples_dir, filename)
            if not os.path.exists(file_path):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"Created example file: {file_path}")
                except Exception as e:
                    logger.error(f"Error creating example file {file_path}: {e}")

    def get_file_language(self, file_path: str) -> str:
        """Get language for syntax highlighting based on file extension."""
        ext = Path(file_path).suffix.lower()
        return SUPPORTED_FORMATS.get(ext, "text")

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
                    os.path.abspath("./examples"),
                ]
                if not any(abs_file_path.startswith(d) for d in allowed_dirs):
                    raise PermissionError(f"Access denied: {file_path}")

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            language = self.get_file_language(file_path)
            self.current_file_path = file_path
            self.current_content = content
            self.add_to_recent_files(file_path)

            return content, language

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise e

    def save_file(
        self, file_path: str, content: str, create_backup: bool = True
    ) -> bool:
        """Save content to file with optional backup and database storage."""
        try:
            # Security check
            abs_file_path = os.path.abspath(file_path)
            abs_working_dir = os.path.abspath(self.working_directory)
            if not abs_file_path.startswith(abs_working_dir):
                raise PermissionError(
                    f"Can only save to working directory: {file_path}"
                )

            # Create backup if file exists and backup is enabled
            if create_backup and os.path.exists(file_path):
                self.create_backup(file_path)

            # Ensure directory exists
            os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.current_file_path = file_path
            self.current_content = content
            self.add_to_recent_files(file_path)

            # Store in database if enabled
            if self.auto_store_to_db:
                try:
                    success, message, doc_model = (
                        self.document_pipeline.process_document_from_editor(
                            content=content,
                            file_path=file_path,
                            document_type=self.get_file_language(file_path),
                            metadata={
                                "saved_from_editor": True,
                                "working_directory": self.working_directory,
                            },
                        )
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

            with open(file_path, encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
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
        self.recent_files = self.recent_files[: self.max_recent_files]

    def list_files(self, directory: str = None) -> list[str]:
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

    def search_related_documents(self, query: str, limit: int = 5) -> dict[str, list]:
        """Search for related documents in the database."""
        try:
            results = self.document_pipeline.search_documents(
                query=query,
                collection_type="documents",
                include_relations=True,
                limit=limit,
            )

            return {
                "documents": [
                    {
                        "id": result.id,
                        "content_preview": result.content[:200] + "...",
                        "metadata": result.metadata,
                        "relevance_score": result.relevance_score,
                    }
                    for result in results
                ]
            }
        except Exception as e:
            logger.error(f"Error searching related documents: {e}")
            return {"documents": []}

    def get_document_suggestions(
        self, content: str, document_type: str = "document"
    ) -> dict[str, Any]:
        """Get suggestions for policies, templates, and related documents."""
        try:
            suggestions = self.document_pipeline.get_document_suggestions(
                content=content, document_type=document_type
            )

            # Format suggestions for UI display
            formatted_suggestions = {}
            for category, results in suggestions.items():
                formatted_suggestions[category] = [
                    {
                        "id": result.id,
                        "title": result.metadata.get(
                            "title", result.metadata.get("filename", "Untitled")
                        ),
                        "content_preview": result.content[:150] + "...",
                        "relevance_score": result.relevance_score,
                        "metadata": result.metadata,
                    }
                    for result in results
                ]

            return formatted_suggestions
        except Exception as e:
            logger.error(f"Error getting document suggestions: {e}")
            return {}

    def store_policy_manual(
        self, title: str, content: str, policy_type: str = "manual"
    ) -> bool:
        """Store a policy manual in the database."""
        try:
            success, message = self.document_pipeline.store_policy_manual(
                title=title,
                content=content,
                policy_type=policy_type,
                authority_level="high",
                metadata={"source": "document_editor"},
            )
            if success:
                logger.info(f"Policy manual stored: {message}")
            else:
                logger.error(f"Failed to store policy manual: {message}")
            return success
        except Exception as e:
            logger.error(f"Error storing policy manual: {e}")
            return False

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        try:
            return self.document_pipeline.get_collection_stats()
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    def add_chat_message(self, role: str, content: str):
        """Add a message to chat history."""
        self.chat_history.append({"role": role, "content": content})

        # Maintain max history limit
        if len(self.chat_history) > self.max_chat_history:
            self.chat_history = self.chat_history[-self.max_chat_history :]

    def clear_chat_history(self):
        """Clear the chat history."""
        self.chat_history.clear()

    async def process_chat_message(
        self, message: str, current_content: str, current_file: str, webui_manager
    ) -> str:
        """Process a chat message and return AI response."""
        try:
            # Add user message to history
            self.add_chat_message("user", message)

            # Get LLM settings from agent_settings tab
            def get_setting(key, default=None):
                comp = webui_manager.id_to_component.get(f"agent_settings.{key}")
                # For now, return default values since we need component state
                # This should be updated to get actual values from the components
                if key == "llm_provider":
                    return "ollama"  # Default provider
                elif key == "llm_model_name":
                    return "llama3.2"  # Default model
                elif key == "llm_temperature":
                    return 0.7
                elif key == "ollama_num_ctx":
                    return 16000
                return default

            llm_provider_name = get_setting("llm_provider")
            llm_model_name = get_setting("llm_model_name")
            llm_temperature = get_setting("llm_temperature", 0.7)
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
                        num_ctx=ollama_num_ctx
                        if llm_provider_name == "ollama"
                        else None,
                    )

                    # Get file context
                    language = (
                        self.get_file_language(current_file) if current_file else "text"
                    )
                    file_context = f"Current file: {current_file if current_file else 'Untitled'} ({language})"
                    content_preview = (
                        current_content[:500] + "..."
                        if len(current_content) > 500
                        else current_content
                    )

                    # Create system prompt for document chat
                    system_prompt = f"""You are a helpful AI assistant integrated with a document editor.

{file_context}

Current document preview:
{content_preview}

The user can:
- Ask questions about the document
- Request edits or improvements
- Get writing suggestions
- Search for related documents
- Ask for document analysis

Provide helpful, contextual responses. If suggesting edits, be specific about what to change.
"""

                    # Create conversation context
                    conversation = [{"role": "system", "content": system_prompt}]

                    # Add recent chat history for context (last 6 messages)
                    recent_history = (
                        self.chat_history[-6:]
                        if len(self.chat_history) > 6
                        else self.chat_history
                    )
                    for msg in recent_history:
                        if msg["role"] in ["user", "assistant"]:
                            conversation.append(msg)

                    # Get response from LLM
                    response = llm.invoke(conversation)
                    if hasattr(response, "content"):
                        ai_response = response.content.strip()
                    else:
                        ai_response = str(response).strip()

                    # Add AI response to history
                    self.add_chat_message("assistant", ai_response)
                    return ai_response

                except Exception as e:
                    logger.error(f"Error using LLM for chat: {e}")
                    error_response = f"Sorry, I encountered an error: {str(e)}. Please check your LLM settings in the Agent Settings tab."
                    self.add_chat_message("assistant", error_response)
                    return error_response

            else:
                fallback_response = "Please configure your LLM settings in the Agent Settings tab to enable AI chat functionality."
                self.add_chat_message("assistant", fallback_response)
                return fallback_response

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            error_response = f"Error processing message: {str(e)}"
            self.add_chat_message("assistant", error_response)
            return error_response


async def handle_file_open(webui_manager: WebuiManager, file_path: str):
    """Handle opening a file."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        content, language = webui_manager.de_manager.read_file(file_path)

        editor_comp = webui_manager.get_component_by_id("document_editor.editor")
        file_path_comp = webui_manager.get_component_by_id(
            "document_editor.current_file_path"
        )
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            editor_comp: gr.Code(value=content, language=language, interactive=True),
            file_path_comp: gr.Textbox(value=file_path),
            status_comp: gr.Textbox(value=f"Opened: {file_path}"),
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
            file_path_comp = webui_manager.get_component_by_id(
                "document_editor.current_file_path"
            )
            status_comp = webui_manager.get_component_by_id("document_editor.status")

            return {
                editor_comp: gr.Code(
                    value=content, language=language, interactive=True
                ),
                file_path_comp: gr.Textbox(value=file_path),
                status_comp: gr.Textbox(value=f"Created: {filename}"),
            }, f"File created: {filename}"
        else:
            return {}, f"Error creating file: {filename}"

    except Exception as e:
        logger.error(f"Error creating file {filename}: {e}")
        return {}, f"Error creating file: {str(e)}"


async def handle_agent_edit(
    webui_manager: WebuiManager, components: dict[Component, Any]
):
    """Handle agent-assisted editing."""
    try:
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

        # Get LLM settings from agent_settings tab
        def get_setting(key, default=None):
            comp = webui_manager.id_to_component.get(f"agent_settings.{key}")
            value = components.get(comp, default) if comp else default
            # Fallback to default values if not set
            if not value:
                if key == "llm_provider":
                    return "ollama"
                elif key == "llm_model_name":
                    return "llama3.2"
                elif key == "llm_temperature":
                    return 0.3
                elif key == "ollama_num_ctx":
                    return 16000
            return value

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
                language = (
                    webui_manager.de_manager.get_file_language(current_file)
                    if current_file
                    else "text"
                )

                # Create system prompt for document editing
                system_prompt = f"""You are a helpful assistant specialized in editing documents.

Current document type: {language}
File: {current_file if current_file else "Untitled"}

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
                if hasattr(response, "content"):
                    new_content = response.content.strip()
                else:
                    new_content = str(response).strip()

                # Clean up the response (remove any markdown code blocks if present)
                if new_content.startswith("```"):
                    lines = new_content.split("\n")
                    if len(lines) > 2:
                        new_content = "\n".join(lines[1:-1])

                status_comp = webui_manager.get_component_by_id(
                    "document_editor.status"
                )

                return {
                    editor_comp: gr.Code(
                        value=new_content, language=language, interactive=True
                    ),
                    agent_instruction_comp: gr.Textbox(value=""),
                    status_comp: gr.Textbox(
                        value=f"Agent edit applied using {llm_model_name}"
                    ),
                }, f"Agent edit applied using {llm_model_name}"

            except Exception as e:
                logger.error(f"Error using LLM for editing: {e}")
                # Fallback to simple comment addition
                pass

        # Fallback: Simple demonstration - add instruction as comment
        language = (
            webui_manager.de_manager.get_file_language(current_file)
            if current_file
            else "text"
        )

        if language == "python":
            comment_prefix = "#"
        elif language in ["javascript", "css", "java"]:
            comment_prefix = "//"
        elif language == "html":
            comment_prefix = "<!--"
            comment_suffix = "-->"
        else:
            comment_prefix = "#"

        # Simple demonstration - add instruction as comment
        if language == "html":
            new_content = (
                f"{current_content}\n\n<!-- Agent instruction: {instruction} -->"
            )
        else:
            new_content = f"{current_content}\n\n{comment_prefix} Agent instruction: {instruction}"

        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            editor_comp: gr.Code(
                value=new_content, language=language, interactive=True
            ),
            agent_instruction_comp: gr.Textbox(value=""),
            status_comp: gr.Textbox(
                value="Agent edit applied (demo - configure LLM in settings)"
            ),
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

        recent_files_comp = webui_manager.get_component_by_id(
            "document_editor.recent_files_display"
        )
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            recent_files_comp: gr.Markdown(value=combined_md),
            status_comp: gr.Textbox(value=f"Found {len(files)} files"),
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

        results = webui_manager.de_manager.search_related_documents(
            search_query, limit=8
        )

        # Format results for display
        if results["documents"]:
            results_md = "**🔍 Search Results**\n\n"
            for i, doc in enumerate(results["documents"][:5], 1):
                title = doc["metadata"].get("filename", doc["id"])
                score = f"{doc['relevance_score']:.3f}"
                results_md += f"{i}. **{title}** (Score: {score})\n"
                results_md += f"   *{doc['content_preview']}*\n\n"
        else:
            results_md = (
                "**🔍 Search Results**\n\n*No documents found matching your query.*"
            )

        search_results_comp = webui_manager.get_component_by_id(
            "document_editor.search_results"
        )
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            search_results_comp: gr.Markdown(value=results_md),
            status_comp: gr.Textbox(
                value=f"Found {len(results['documents'])} documents"
            ),
        }, f"Search completed: {len(results['documents'])} documents found"

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return {}, f"Error searching documents: {str(e)}"


async def handle_get_suggestions(
    webui_manager: WebuiManager, content: str, current_file: str
):
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

        suggestions = webui_manager.de_manager.get_document_suggestions(
            content, document_type
        )

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
            suggestions_md += (
                "*No suggestions available. Try saving some documents first.*"
            )

        suggestions_comp = webui_manager.get_component_by_id(
            "document_editor.suggestions_display"
        )
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        total_suggestions = sum(len(v) for v in suggestions.values())
        return {
            suggestions_comp: gr.Markdown(value=suggestions_md),
            status_comp: gr.Textbox(value=f"Generated {total_suggestions} suggestions"),
        }, f"Suggestions generated: {total_suggestions} items"

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {}, f"Error getting suggestions: {str(e)}"


async def handle_store_as_policy(
    webui_manager: WebuiManager, content: str, policy_title: str, policy_type: str
):
    """Handle storing current document as a policy manual."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        if not content.strip():
            return {}, "No content to store as policy"

        if not policy_title.strip():
            return {}, "Policy title is required"

        success = webui_manager.de_manager.store_policy_manual(
            title=policy_title, content=content, policy_type=policy_type
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


async def handle_chat_message(
    webui_manager: WebuiManager, components: dict[Component, Any]
):
    """Handle sending a chat message."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        # Get components
        chat_input_comp = webui_manager.get_component_by_id(
            "document_editor.chat_input"
        )
        chatbot_comp = webui_manager.get_component_by_id("document_editor.chatbot")
        editor_comp = webui_manager.get_component_by_id("document_editor.editor")
        file_path_comp = webui_manager.get_component_by_id(
            "document_editor.current_file_path"
        )
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        # Get values
        chat_message = components.get(chat_input_comp, "").strip()
        current_content = components.get(editor_comp, "")
        current_file = components.get(file_path_comp, "")

        if not chat_message:
            return {}, "Please enter a message"

        # Process the chat message
        ai_response = await webui_manager.de_manager.process_chat_message(
            chat_message, current_content, current_file, webui_manager
        )

        # Update UI
        return {
            chatbot_comp: gr.Chatbot(value=webui_manager.de_manager.chat_history),
            chat_input_comp: gr.Textbox(value=""),
            status_comp: gr.Textbox(value="Chat message processed"),
        }, "Chat message sent"

    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        return {}, f"Error handling chat message: {str(e)}"


async def handle_clear_chat(webui_manager: WebuiManager):
    """Handle clearing the chat history."""
    if not webui_manager.de_manager:
        return {}, "No document editor manager available"

    try:
        webui_manager.de_manager.clear_chat_history()

        chatbot_comp = webui_manager.get_component_by_id("document_editor.chatbot")
        status_comp = webui_manager.get_component_by_id("document_editor.status")

        return {
            chatbot_comp: gr.Chatbot(value=[]),
            status_comp: gr.Textbox(value="Chat history cleared"),
        }, "Chat history cleared"

    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        return {}, f"Error clearing chat: {str(e)}"


def create_document_editor_tab(webui_manager: WebuiManager):
    """Create the document editor tab with IDE-style three-column layout."""
    webui_manager.init_document_editor()

    tab_components = {}

    # IDE-style three-column layout
    # IDE-style layout with bottom chat panel
    with gr.Row():
        # Left Sidebar - File Explorer & Navigation
        with gr.Column(scale=1, min_width=250):
            gr.Markdown("### 📁 EXPLORER")

            # File operations
            with gr.Group():
                gr.Markdown("**🔧 File Operations**")
                with gr.Row():
                    new_file_btn = gr.Button("📄 New", size="sm", scale=1)
                    upload_btn = gr.Button("📤 Upload", size="sm", scale=1)

                # File upload (initially hidden, shows when upload clicked)
                file_upload = gr.File(
                    label="",
                    file_types=[
                        ".txt",
                        ".md",
                        ".py",
                        ".js",
                        ".html",
                        ".css",
                        ".json",
                        ".xml",
                        ".yaml",
                        ".yml",
                    ],
                    interactive=True,
                    container=False,
                    visible=False,
                )

            # File tree/selector
            with gr.Group():
                gr.Markdown("**📂 Files**")
                refresh_files_btn = gr.Button(
                    "🔄 Refresh Files", variant="secondary", size="sm"
                )
                file_selector = gr.Dropdown(
                    label="",
                    choices=[],
                    interactive=True,
                    container=False,
                    allow_custom_value=True,
                    info="Select a file to open",
                )
                open_selected_btn = gr.Button(
                    "📂 Open Selected", variant="primary", size="sm"
                )

            # Recent files
            with gr.Group():
                gr.Markdown("**🕒 Files & Documents**")
                recent_files_display = gr.HTML(
                    value="<div style='padding: 10px; color: #888;'>Click refresh to load files</div>",
                    elem_id="files_list",
                )

            # Quick actions
            with gr.Group():
                gr.Markdown("**⚡ Quick Actions**")
                export_btn = gr.Button(
                    "💾 Export Current", variant="secondary", size="sm"
                )
                download_btn = gr.Button("⬇️ Download", variant="secondary", size="sm")

        # Main Editor Area
        with gr.Column(scale=4):
            # Tab bar for multiple documents
            with gr.Row():
                with gr.Column(scale=4):
                    active_tabs_display = gr.HTML(
                        value='<div style="display: flex; border-bottom: 1px solid #444; padding: 5px 0; min-height: 35px; align-items: center;"><span style="color: #888; padding: 10px;">No files open</span></div>',
                        elem_id="tabs_container",
                    )
                with gr.Column(scale=1):
                    close_tab_btn = gr.Button(
                        "✕ Close Tab", variant="secondary", size="sm", visible=False
                    )

            # Editor controls
            with gr.Row():
                with gr.Column(scale=4):
                    current_file_display = gr.Textbox(
                        label="",
                        value="💡 Select a file to begin editing or open a new one",
                        interactive=False,
                        container=False,
                        show_label=False,
                        max_lines=1,
                    )
                with gr.Column(scale=1):
                    with gr.Row():
                        save_btn = gr.Button("💾 Save", variant="primary", size="sm")
                        auto_save_toggle = gr.Checkbox(
                            label="Auto-save",
                            value=True,
                            interactive=True,
                            container=False,
                        )

            # Main code editor
            editor = gr.Code(
                label="",
                language="markdown",
                interactive=True,
                lines=28,
                show_label=False,
                container=True,
            )

            # Status bar
            status_display = gr.Textbox(
                label="",
                value="Ready",
                interactive=False,
                container=False,
                show_label=False,
                max_lines=1,
            )

    # Bottom Panel - AI Assistant & Chat
    with gr.Row():
        with gr.Column():
            # AI Chat Interface
            with gr.Group():
                gr.Markdown("### 🤖 CogniDoc AI Assistant")

                chatbot = gr.Chatbot(
                    lambda: webui_manager.de_manager.chat_history
                    if webui_manager.de_manager
                    else [],
                    elem_id="document_editor_chatbot",
                    label="",
                    type="messages",
                    height=200,
                    show_copy_button=True,
                    show_label=False,
                    container=True,
                )

                # Chat input row
                with gr.Row():
                    chat_input = gr.Textbox(
                        label="",
                        placeholder="Chat with your AI assistant... (e.g., /search latest AI trends)",
                        lines=1,
                        interactive=True,
                        container=False,
                        scale=5,
                    )
                    chat_send_btn = gr.Button(
                        "💬", variant="primary", size="sm", scale=1
                    )
                    clear_chat_btn = gr.Button(
                        "🗑️", variant="secondary", size="sm", scale=1
                    )

    # Bottom Panel - Policy Management (Collapsible)
    with gr.Row():
        with gr.Column():
            with gr.Accordion("📋 Policy Management", open=False):
                with gr.Row():
                    with gr.Column(scale=2):
                        # Store current as policy
                        with gr.Group():
                            gr.Markdown("**Store as Policy**")
                            with gr.Row():
                                policy_title_input = gr.Textbox(
                                    label="",
                                    placeholder="Policy title...",
                                    interactive=True,
                                    container=False,
                                    scale=2,
                                )
                                policy_type_dropdown = gr.Dropdown(
                                    label="",
                                    choices=[
                                        "manual",
                                        "procedure",
                                        "guideline",
                                        "template",
                                    ],
                                    value="manual",
                                    interactive=True,
                                    container=False,
                                    scale=1,
                                )
                            store_as_policy_btn = gr.Button(
                                "📋 Store as Policy", variant="secondary", size="sm"
                            )

                    with gr.Column(scale=2):
                        # Policy search
                        with gr.Group():
                            gr.Markdown("**Search Policies**")
                            policy_search_input = gr.Textbox(
                                label="",
                                placeholder="Search policies...",
                                interactive=True,
                                container=False,
                            )
                            with gr.Row():
                                search_policies_btn = gr.Button(
                                    "🔍 Search", variant="secondary", size="sm", scale=1
                                )
                                upload_policy_btn = gr.Button(
                                    "📤 Upload Policy",
                                    variant="secondary",
                                    size="sm",
                                    scale=1,
                                )

                            # Policy upload (initially hidden)
                            policy_upload = gr.File(
                                label="Upload Policy File",
                                file_types=[".pdf", ".txt", ".md", ".docx", ".html"],
                                interactive=True,
                                container=False,
                                visible=False,
                            )

                with gr.Row():
                    # Policy results
                    policy_results = gr.Markdown(
                        "*Policy search results will appear here*", container=False
                    )

        # Hidden components for tab management
        current_file_path = gr.Textbox(visible=False)
        open_file_trigger = gr.Textbox(visible=False, elem_id="open_file_trigger")
        switch_tab_trigger = gr.Textbox(visible=False, elem_id="switch_tab_trigger")
        close_tab_trigger = gr.Textbox(visible=False, elem_id="close_tab_trigger")

    # Store all components
    tab_components.update(
        {
            # File management
            "new_file_btn": new_file_btn,
            "upload_btn": upload_btn,
            "file_upload": file_upload,
            "refresh_files_btn": refresh_files_btn,
            "file_selector": file_selector,
            "open_selected_btn": open_selected_btn,
            "recent_files_display": recent_files_display,
            "export_btn": export_btn,
            "download_btn": download_btn,
            # Editor with tabs
            "active_tabs_display": active_tabs_display,
            "close_tab_btn": close_tab_btn,
            "current_file_display": current_file_display,
            "save_btn": save_btn,
            "auto_save_toggle": auto_save_toggle,
            "editor": editor,
            "status_display": status_display,
            "current_file_path": current_file_path,
            # AI Assistant
            "chatbot": chatbot,
            "chat_input": chat_input,
            "chat_send_btn": chat_send_btn,
            "clear_chat_btn": clear_chat_btn,
            # Policy management
            "policy_title_input": policy_title_input,
            "policy_type_dropdown": policy_type_dropdown,
            "store_as_policy_btn": store_as_policy_btn,
            "policy_search_input": policy_search_input,
            "search_policies_btn": search_policies_btn,
            "policy_upload": policy_upload,
            "upload_policy_btn": upload_policy_btn,
            "policy_results": policy_results,
            # Tab management
            "switch_tab_trigger": switch_tab_trigger,
            "close_tab_trigger": close_tab_trigger,
            "open_file_trigger": open_file_trigger,
        }
    )

    webui_manager.add_components("document_editor", tab_components)
    all_managed_components = set(webui_manager.get_components())

    # Tab management state
    if not hasattr(webui_manager, "editor_tabs"):
        webui_manager.editor_tabs = {}  # {tab_id: {path, content, language, title}}
        webui_manager.active_tab = None

    # Tab management functions
    def generate_tab_id():
        """Generate a unique tab ID."""

        return str(uuid.uuid4())[:8]

    def update_tabs_display():
        """Update the tabs HTML display."""
        if not webui_manager.editor_tabs:
            return '<div style="display: flex; border-bottom: 1px solid #444; padding: 5px 0; min-height: 35px; align-items: center;"><span style="color: #888; padding: 10px;">No files open</span></div>'

        tabs_html = '<div style="display: flex; border-bottom: 1px solid #444; padding: 5px 0; min-height: 35px; align-items: center;">'

        for tab_id, tab_data in webui_manager.editor_tabs.items():
            is_active = tab_id == webui_manager.active_tab
            title = tab_data.get("title", "Untitled")

            # Truncate long titles
            if len(title) > 20:
                title = title[:17] + "..."

            # Tab styling
            tab_style = f"""
                padding: 6px 12px;
                margin: 2px;
                border: 1px solid #555;
                border-radius: 4px 4px 0 0;
                cursor: pointer;
                background: {"#555" if is_active else "#333"};
                color: {"#fff" if is_active else "#ccc"};
                font-size: 13px;
                transition: all 0.2s;
            """

            tabs_html += f'<div style="{tab_style}" onclick="window.switchTab(\'{tab_id}\')" title="{tab_data.get("path", "")}">'
            tabs_html += f"{title}"
            if (
                len(webui_manager.editor_tabs) > 1
            ):  # Show close button only if multiple tabs
                tabs_html += f' <span onclick="event.stopPropagation(); window.closeTab(\'{tab_id}\')" style="margin-left: 8px; color: #999; hover: #fff;">✕</span>'
            tabs_html += "</div>"

        tabs_html += "</div>"

        # Add JavaScript for tab interactions
        tabs_html += """
        <script>
        window.switchTab = function(tabId) {
            // Trigger Gradio event to switch tab
            document.getElementById('switch_tab_trigger').value = tabId;
            document.getElementById('switch_tab_trigger').dispatchEvent(new Event('input'));
        };
        window.closeTab = function(tabId) {
            // Trigger Gradio event to close tab
            document.getElementById('close_tab_trigger').value = tabId;
            document.getElementById('close_tab_trigger').dispatchEvent(new Event('input'));
        };
        </script>
        """

        return tabs_html

    # Event handlers
    async def toggle_file_upload():
        """Toggle file upload visibility."""
        return gr.File(visible=True)

    async def toggle_policy_upload():
        """Toggle policy upload visibility."""
        return gr.File(visible=True)

    async def refresh_files_wrapper():
        """Refresh file list from both filesystem and database."""
        try:
            if not webui_manager.de_manager:
                return (
                    gr.Dropdown(choices=[]),
                    "*No document editor available*",
                    "❌ No manager",
                )

            # Get files from filesystem
            filesystem_files = webui_manager.de_manager.list_files()

            # Get documents from database
            database_docs = []
            try:
                from ...database.models import QueryRequest

                query_request = QueryRequest(
                    query="documents",
                    collection_name="documents",
                    limit=50,
                    include_metadata=True,
                )
                db_results = webui_manager.de_manager.document_pipeline.manager.search(
                    query_request
                )
                database_docs = [
                    f"db:{result.metadata.get('filename', result.id)}"
                    for result in db_results
                    if result.metadata.get("filename")
                ]
            except Exception as e:
                logger.warning(f"Could not load database documents: {e}")

            # Combine filesystem and database files
            all_files = []

            # Add filesystem files
            if filesystem_files:
                all_files.extend([f"fs:./tmp/documents/{f}" for f in filesystem_files])

            # Add database documents
            all_files.extend(database_docs)

            # Create clickable files display
            files_html = '<div style="padding: 10px;">'
            files_html += f'<div style="margin-bottom: 15px;"><strong>📁 File Sources:</strong><br/>• Filesystem: {len(filesystem_files)} files<br/>• Database: {len(database_docs)} documents</div>'

            # Add filesystem files
            if filesystem_files:
                files_html += '<div style="margin-bottom: 10px;"><strong>💾 Filesystem Files:</strong></div>'
                for i, file in enumerate(filesystem_files[:8], 1):
                    filename = os.path.basename(file)
                    file_path = f"fs:./tmp/documents/{file}"
                    files_html += f"""
                    <div style="margin: 2px 0; padding: 4px 8px; border: 1px solid #444; border-radius: 3px; cursor: pointer; hover: background-color: #333;"
                         onclick="window.openFileInTab('{file_path}', '{filename}')"
                         title="Click to open in new tab">
                        📄 {filename}
                    </div>
                    """

            # Add database documents
            if database_docs:
                files_html += '<div style="margin: 15px 0 5px 0;"><strong>🗄️ Database Documents:</strong></div>'
                for i, doc_path in enumerate(database_docs[:8], 1):
                    filename = doc_path.replace("db:", "")
                    files_html += f"""
                    <div style="margin: 2px 0; padding: 4px 8px; border: 1px solid #444; border-radius: 3px; cursor: pointer; hover: background-color: #333;"
                         onclick="window.openFileInTab('{doc_path}', '{filename}')"
                         title="Click to open in new tab">
                        📄 {filename} <span style="color: #888; font-size: 11px;">(DB)</span>
                    </div>
                    """

            # Add recent files
            recent_files = webui_manager.de_manager.recent_files
            if recent_files:
                files_html += '<div style="margin: 15px 0 5px 0;"><strong>🕒 Recent Files:</strong></div>'
                for file in recent_files[:5]:
                    filename = os.path.basename(file)
                    file_path = (
                        file if file.startswith(("fs:", "db:")) else f"fs:{file}"
                    )
                    files_html += f"""
                    <div style="margin: 2px 0; padding: 4px 8px; border: 1px solid #444; border-radius: 3px; cursor: pointer; hover: background-color: #333;"
                         onclick="window.openFileInTab('{file_path}', '{filename}')"
                         title="Click to open in new tab">
                        📄 {filename}
                    </div>
                    """

            files_html += """
            <script>
            window.openFileInTab = function(filePath, fileName) {
                // Trigger Gradio event to open file in new tab
                document.getElementById('open_file_trigger').value = JSON.stringify({path: filePath, name: fileName});
                document.getElementById('open_file_trigger').dispatchEvent(new Event('input'));
            };
            </script>
            </div>
            """

            total_files = len(all_files)
            gr.Info(
                f"Found {total_files} files ({len(filesystem_files)} local, {len(database_docs)} in database)"
            )
            return (
                gr.Dropdown(choices=all_files),
                gr.HTML(value=files_html),
                f"📁 Found {total_files} files",
            )

        except Exception as e:
            error_msg = f"Error refreshing files: {str(e)}"
            gr.Error(error_msg)
            return (
                gr.Dropdown(choices=[]),
                gr.HTML(
                    value="<div style='padding: 10px; color: #f44;'>Error loading files</div>"
                ),
                f"❌ {error_msg}",
            )

    async def open_selected_wrapper(file_path: str):
        """Open selected file in a new tab."""
        try:
            if not file_path or not file_path.strip():
                return (
                    gr.HTML(),
                    gr.Code(value="", language="text"),
                    "No file selected",
                    "",
                    gr.Button(visible=False),
                )

            if not webui_manager.de_manager:
                return (
                    gr.HTML(),
                    gr.Code(value="", language="text"),
                    "No document editor available",
                    "",
                    gr.Button(visible=False),
                )

            # Get filename for tab
            if file_path.startswith("db:"):
                filename = file_path[3:]
            elif file_path.startswith("fs:"):
                filename = os.path.basename(file_path[3:])
            else:
                filename = os.path.basename(file_path)

            # Check if file is already open in a tab
            for tab_id, tab_data in webui_manager.editor_tabs.items():
                if tab_data["path"] == file_path:
                    # Switch to existing tab
                    webui_manager.active_tab = tab_id
                    tabs_html = update_tabs_display()
                    gr.Info(f"Switched to existing tab: {filename}")
                    return (
                        gr.HTML(value=tabs_html),
                        gr.Code(
                            value=tab_data["content"],
                            language=tab_data["language"],
                            interactive=True,
                        ),
                        f"📄 {filename}",
                        file_path,
                        gr.Button(visible=len(webui_manager.editor_tabs) > 1),
                    )

            # Load file content based on source
            if file_path.startswith("db:"):
                # Load from database
                db_filename = file_path[3:]
                from ...database.models import QueryRequest

                query_request = QueryRequest(
                    query=db_filename,
                    collection_name="documents",
                    limit=10,
                    include_metadata=True,
                )
                db_results = webui_manager.de_manager.document_pipeline.manager.search(
                    query_request
                )

                for result in db_results:
                    if result.metadata.get("filename") == db_filename:
                        content = result.content
                        file_extension = Path(db_filename).suffix.lower()
                        language = SUPPORTED_FORMATS.get(file_extension, "text")
                        break
                else:
                    raise FileNotFoundError(
                        f"Document not found in database: {db_filename}"
                    )
            else:
                # Load from filesystem
                actual_path = (
                    file_path[3:] if file_path.startswith("fs:") else file_path
                )
                content, language = webui_manager.de_manager.read_file(actual_path)

            # Create new tab
            tab_id = generate_tab_id()
            webui_manager.editor_tabs[tab_id] = {
                "path": file_path,
                "content": content,
                "language": language,
                "title": filename,
                "modified": False,
            }
            webui_manager.active_tab = tab_id

            tabs_html = update_tabs_display()
            gr.Info(f"Opened in new tab: {filename}")

            return (
                gr.HTML(value=tabs_html),
                gr.Code(value=content, language=language, interactive=True),
                f"📄 {filename}",
                file_path,
                gr.Button(visible=len(webui_manager.editor_tabs) > 1),
            )

        except Exception as e:
            error_msg = f"Error opening file: {str(e)}"
            gr.Warning(error_msg)
            return (
                gr.HTML(),
                gr.Code(value="", language="text"),
                f"❌ Error: {str(e)}",
                "",
                gr.Button(visible=False),
            )

    async def handle_file_upload(uploaded_file):
        """Handle file upload and store in database."""
        try:
            if not uploaded_file:
                return gr.File(visible=False), "No file uploaded"

            if not webui_manager.de_manager:
                return gr.File(visible=False), "❌ No document editor available"

            # Read uploaded file
            file_path = uploaded_file.name
            filename = os.path.basename(file_path)

            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Store in working directory
            destination_path = os.path.join(
                webui_manager.de_manager.working_directory, filename
            )
            success = webui_manager.de_manager.save_file(destination_path, content)

            if success:
                gr.Info(f"File uploaded and stored: {filename}")
                return gr.File(visible=False), f"✅ Uploaded: {filename}"
            else:
                return gr.File(visible=False), f"❌ Failed to store: {filename}"

        except Exception as e:
            error_msg = f"Error uploading file: {str(e)}"
            gr.Error(error_msg)
            return gr.File(visible=False), f"❌ {error_msg}"

    async def handle_policy_upload(uploaded_file):
        """Handle policy file upload and store in database."""
        try:
            if not uploaded_file:
                return gr.File(visible=False), "No policy file uploaded"

            if not webui_manager.de_manager:
                return gr.File(visible=False), "❌ No document editor available"

            # Read uploaded policy file
            file_path = uploaded_file.name
            filename = os.path.basename(file_path)

            # Handle different file types
            if filename.lower().endswith(".pdf"):
                # For PDF files, we'd need a PDF reader - placeholder for now
                content = f"PDF Policy Document: {filename}\n\n[PDF content would be extracted here]"
            else:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

            # Store as policy in database
            policy_title = (
                filename.replace(".pdf", "").replace(".txt", "").replace(".md", "")
            )
            success = webui_manager.de_manager.store_policy_manual(
                title=policy_title,
                content=content,
                policy_type="uploaded",
                metadata={"source": "file_upload", "original_filename": filename},
            )

            if success:
                gr.Info(f"Policy uploaded and stored: {policy_title}")
                return gr.File(visible=False), f"✅ Policy uploaded: {policy_title}"
            else:
                return gr.File(
                    visible=False
                ), f"❌ Failed to store policy: {policy_title}"

        except Exception as e:
            error_msg = f"Error uploading policy: {str(e)}"
            gr.Error(error_msg)
            return gr.File(visible=False), f"❌ {error_msg}"

    async def search_policies_wrapper(search_query: str):
        """Search policies in the database."""
        try:
            if not webui_manager.de_manager:
                return "*No document editor available*", "❌ No manager"

            if not search_query.strip():
                return (
                    "*Enter a search query to find policies*",
                    "Please enter a search query",
                )

            # Search in policy_manuals collection
            results = webui_manager.de_manager.document_pipeline.search_documents(
                query=search_query, collection_type="policies", limit=10
            )

            # Format results
            if results:
                results_md = "**📋 Policy Search Results:**\n\n"
                for i, result in enumerate(results[:5], 1):
                    title = result.metadata.get("title", "Untitled Policy")
                    policy_type = result.metadata.get("policy_type", "manual")
                    score = f"{result.relevance_score:.3f}"
                    results_md += f"{i}. **{title}** ({policy_type})\n"
                    results_md += (
                        f"   Score: {score} | Preview: *{result.content[:100]}...*\n\n"
                    )
            else:
                results_md = "**📋 Policy Search Results:**\n\n*No policies found matching your query.*"

            gr.Info(f"Found {len(results)} policies")
            return results_md, f"🔍 Found {len(results)} policies"

        except Exception as e:
            error_msg = f"Error searching policies: {str(e)}"
            gr.Error(error_msg)
            return "*Error searching policies*", f"❌ {error_msg}"

    async def new_file_wrapper():
        """Create new file in a new tab."""
        try:
            if not webui_manager.de_manager:
                return (
                    gr.HTML(),
                    gr.Code(value="", language="text"),
                    "No document editor available",
                    "",
                    gr.Button(visible=False),
                )

            import datetime

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"document_{timestamp}.md"
            file_path = os.path.join(
                webui_manager.de_manager.working_directory, filename
            )

            template_content = f"# New Document\n\nCreated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\nStart writing your content here...\n"
            success = webui_manager.de_manager.save_file(file_path, template_content)

            if success:
                content, language = webui_manager.de_manager.read_file(file_path)

                # Create new tab
                tab_id = generate_tab_id()
                webui_manager.editor_tabs[tab_id] = {
                    "path": file_path,
                    "content": content,
                    "language": language,
                    "title": f"{filename} (new)",
                    "modified": False,
                }
                webui_manager.active_tab = tab_id

                tabs_html = update_tabs_display()
                gr.Info(f"Created new file in tab: {filename}")

                return (
                    gr.HTML(value=tabs_html),
                    gr.Code(value=content, language=language, interactive=True),
                    f"📄 {filename} (new)",
                    file_path,
                    gr.Button(visible=len(webui_manager.editor_tabs) > 1),
                )
            else:
                return (
                    gr.HTML(),
                    gr.Code(value="", language="text"),
                    f"❌ Failed to create: {filename}",
                    "",
                    gr.Button(visible=False),
                )

        except Exception as e:
            error_msg = f"Error creating file: {str(e)}"
            gr.Error(error_msg)
            return (
                gr.HTML(),
                gr.Code(value="", language="text"),
                f"❌ Error: {str(e)}",
                "",
                gr.Button(visible=False),
            )

    async def save_file_wrapper(content: str, file_path: str):
        """Save current file to filesystem and database."""
        try:
            if not webui_manager.de_manager:
                return "❌ No document editor available"

            if not file_path.strip():
                return "❌ No file to save"

            success = webui_manager.de_manager.save_file(file_path, content)
            if success:
                filename = os.path.basename(file_path)
                gr.Info(f"Saved to filesystem and database: {filename}")
                return f"✅ Saved: {filename}"
            else:
                return "❌ Failed to save"

        except Exception as e:
            error_msg = f"Error saving: {str(e)}"
            gr.Error(error_msg)
            return f"❌ {error_msg}"

    async def chat_wrapper(components_dict: dict[Component, Any]):
        """Handle chat messages with document context."""
        try:
            if not webui_manager.de_manager:
                return [], "", "❌ No document editor available"

            chat_input_comp = webui_manager.get_component_by_id(
                "document_editor.chat_input"
            )
            editor_comp = webui_manager.get_component_by_id("document_editor.editor")
            current_file_path_comp = webui_manager.get_component_by_id(
                "document_editor.current_file_path"
            )

            chat_message = components_dict.get(chat_input_comp, "").strip()
            current_content = components_dict.get(editor_comp, "")
            current_file = components_dict.get(current_file_path_comp, "")

            if not chat_message:
                return (
                    webui_manager.de_manager.chat_history,
                    "",
                    "Please enter a message",
                )

            ai_response = await webui_manager.de_manager.process_chat_message(
                chat_message, current_content, current_file, webui_manager
            )

            return webui_manager.de_manager.chat_history, "", "💬 Message sent"

        except Exception as e:
            error_msg = f"Chat error: {str(e)}"
            gr.Error(error_msg)
            return [], "", f"❌ {error_msg}"

    async def clear_chat_wrapper():
        """Clear chat history and reinitialize."""
        try:
            if not webui_manager.de_manager:
                return [], "❌ No document editor available"

            webui_manager.de_manager.clear_chat_history()
            webui_manager.de_manager._initialize_welcome_message()
            gr.Info("Chat cleared")
            return webui_manager.de_manager.chat_history, "🗑️ Chat cleared"

        except Exception as e:
            error_msg = f"Error clearing chat: {str(e)}"
            gr.Error(error_msg)
            return [], f"❌ {error_msg}"

    async def open_file_in_tab(trigger_value: str):
        """Open file in new tab from clickable file list."""
        try:
            if not trigger_value:
                return gr.HTML(), gr.Code(), "", "", gr.Button(visible=False)

            import json

            file_info = json.loads(trigger_value)
            file_path = file_info["path"]
            file_name = file_info["name"]

            # Check if file is already open in a tab
            for tab_id, tab_data in webui_manager.editor_tabs.items():
                if tab_data["path"] == file_path:
                    # Switch to existing tab
                    webui_manager.active_tab = tab_id
                    tab_content = tab_data["content"]
                    language = tab_data["language"]

                    tabs_html = update_tabs_display()
                    gr.Info(f"Switched to tab: {file_name}")
                    return (
                        gr.HTML(value=tabs_html),
                        gr.Code(value=tab_content, language=language, interactive=True),
                        f"📄 {file_name}",
                        file_path,
                        gr.Button(visible=len(webui_manager.editor_tabs) > 1),
                    )

            # Open file content
            if file_path.startswith("db:"):
                # Load from database
                filename = file_path[3:]
                from ...database.models import QueryRequest

                query_request = QueryRequest(
                    query=filename,
                    collection_name="documents",
                    limit=10,
                    include_metadata=True,
                )
                db_results = webui_manager.de_manager.document_pipeline.manager.search(
                    query_request
                )

                for result in db_results:
                    if result.metadata.get("filename") == filename:
                        content = result.content
                        file_extension = Path(filename).suffix.lower()
                        language = SUPPORTED_FORMATS.get(file_extension, "text")
                        break
                else:
                    raise FileNotFoundError(
                        f"Document not found in database: {filename}"
                    )
            else:
                # Load from filesystem
                actual_path = (
                    file_path[3:] if file_path.startswith("fs:") else file_path
                )
                content, language = webui_manager.de_manager.read_file(actual_path)

            # Create new tab
            tab_id = generate_tab_id()
            webui_manager.editor_tabs[tab_id] = {
                "path": file_path,
                "content": content,
                "language": language,
                "title": file_name,
                "modified": False,
            }
            webui_manager.active_tab = tab_id

            tabs_html = update_tabs_display()
            gr.Info(f"Opened in new tab: {file_name}")

            return (
                gr.HTML(value=tabs_html),
                gr.Code(value=content, language=language, interactive=True),
                f"📄 {file_name}",
                file_path,
                gr.Button(visible=len(webui_manager.editor_tabs) > 1),
            )

        except Exception as e:
            error_msg = f"Error opening file in tab: {str(e)}"
            gr.Error(error_msg)
            return (
                gr.HTML(),
                gr.Code(),
                f"❌ Error: {str(e)}",
                "",
                gr.Button(visible=False),
            )

    async def switch_tab_wrapper(tab_id: str):
        """Switch to a different tab."""
        try:
            if not tab_id or tab_id not in webui_manager.editor_tabs:
                return gr.HTML(), gr.Code(), "", "", gr.Button(visible=False)

            # Save current tab content if there's an active tab
            if (
                webui_manager.active_tab
                and webui_manager.active_tab in webui_manager.editor_tabs
            ):
                # This would save the current editor content to the tab state
                # For now, we'll implement this later
                pass

            # Switch to new tab
            webui_manager.active_tab = tab_id
            tab_data = webui_manager.editor_tabs[tab_id]

            tabs_html = update_tabs_display()
            gr.Info(f"Switched to: {tab_data['title']}")

            return (
                gr.HTML(value=tabs_html),
                gr.Code(
                    value=tab_data["content"],
                    language=tab_data["language"],
                    interactive=True,
                ),
                f"📄 {tab_data['title']}",
                tab_data["path"],
                gr.Button(visible=len(webui_manager.editor_tabs) > 1),
            )

        except Exception as e:
            error_msg = f"Error switching tab: {str(e)}"
            gr.Error(error_msg)
            return (
                gr.HTML(),
                gr.Code(),
                f"❌ Error: {str(e)}",
                "",
                gr.Button(visible=False),
            )

    async def close_tab_wrapper(tab_id: str):
        """Close a tab."""
        try:
            if not tab_id or tab_id not in webui_manager.editor_tabs:
                return gr.HTML(), gr.Code(), "", "", gr.Button(visible=False)

            tab_title = webui_manager.editor_tabs[tab_id]["title"]
            del webui_manager.editor_tabs[tab_id]

            # If we closed the active tab, switch to another one
            if webui_manager.active_tab == tab_id:
                if webui_manager.editor_tabs:
                    # Switch to the first available tab
                    webui_manager.active_tab = next(iter(webui_manager.editor_tabs))
                    tab_data = webui_manager.editor_tabs[webui_manager.active_tab]

                    tabs_html = update_tabs_display()
                    gr.Info(
                        f"Closed tab: {tab_title}, switched to: {tab_data['title']}"
                    )

                    return (
                        gr.HTML(value=tabs_html),
                        gr.Code(
                            value=tab_data["content"],
                            language=tab_data["language"],
                            interactive=True,
                        ),
                        f"📄 {tab_data['title']}",
                        tab_data["path"],
                        gr.Button(visible=len(webui_manager.editor_tabs) > 1),
                    )
                else:
                    # No tabs left
                    webui_manager.active_tab = None
                    tabs_html = update_tabs_display()
                    gr.Info(f"Closed tab: {tab_title}")

                    return (
                        gr.HTML(value=tabs_html),
                        gr.Code(value="", language="text", interactive=True),
                        "💡 Ready - Create or open a file to start editing",
                        "",
                        gr.Button(visible=False),
                    )
            else:
                # Closed a non-active tab
                tabs_html = update_tabs_display()
                gr.Info(f"Closed tab: {tab_title}")

                # Keep current active tab content
                active_tab_data = webui_manager.editor_tabs[webui_manager.active_tab]
                return (
                    gr.HTML(value=tabs_html),
                    gr.Code(
                        value=active_tab_data["content"],
                        language=active_tab_data["language"],
                        interactive=True,
                    ),
                    f"📄 {active_tab_data['title']}",
                    active_tab_data["path"],
                    gr.Button(visible=len(webui_manager.editor_tabs) > 1),
                )

        except Exception as e:
            error_msg = f"Error closing tab: {str(e)}"
            gr.Error(error_msg)
            return (
                gr.HTML(),
                gr.Code(),
                f"❌ Error: {str(e)}",
                "",
                gr.Button(visible=False),
            )

    # Connect event handlers
    upload_btn.click(fn=toggle_file_upload, outputs=[file_upload])
    upload_policy_btn.click(fn=toggle_policy_upload, outputs=[policy_upload])

    # File upload handler
    file_upload.change(
        fn=handle_file_upload,
        inputs=[file_upload],
        outputs=[file_upload, status_display],
    )

    # Policy upload handler
    policy_upload.change(
        fn=handle_policy_upload,
        inputs=[policy_upload],
        outputs=[policy_upload, status_display],
    )

    refresh_files_btn.click(
        fn=refresh_files_wrapper,
        outputs=[file_selector, recent_files_display, status_display],
    )

    open_selected_btn.click(
        fn=open_selected_wrapper,
        inputs=[file_selector],
        outputs=[
            active_tabs_display,
            editor,
            current_file_display,
            current_file_path,
            close_tab_btn,
        ],
    )

    new_file_btn.click(
        fn=new_file_wrapper,
        outputs=[
            active_tabs_display,
            editor,
            current_file_display,
            current_file_path,
            close_tab_btn,
        ],
    )

    # Tab management event handlers
    open_file_trigger.change(
        fn=open_file_in_tab,
        inputs=[open_file_trigger],
        outputs=[
            active_tabs_display,
            editor,
            current_file_display,
            current_file_path,
            close_tab_btn,
        ],
    )

    switch_tab_trigger.change(
        fn=switch_tab_wrapper,
        inputs=[switch_tab_trigger],
        outputs=[
            active_tabs_display,
            editor,
            current_file_display,
            current_file_path,
            close_tab_btn,
        ],
    )

    close_tab_trigger.change(
        fn=close_tab_wrapper,
        inputs=[close_tab_trigger],
        outputs=[
            active_tabs_display,
            editor,
            current_file_display,
            current_file_path,
            close_tab_btn,
        ],
    )

    close_tab_btn.click(
        fn=lambda: close_tab_wrapper(webui_manager.active_tab)
        if webui_manager.active_tab
        else (gr.HTML(), gr.Code(), "", "", gr.Button(visible=False)),
        outputs=[
            active_tabs_display,
            editor,
            current_file_display,
            current_file_path,
            close_tab_btn,
        ],
    )

    save_btn.click(
        fn=save_file_wrapper,
        inputs=[editor, current_file_path],
        outputs=[status_display],
    )

    # Policy search handler
    search_policies_btn.click(
        fn=search_policies_wrapper,
        inputs=[policy_search_input],
        outputs=[policy_results, status_display],
    )

    chat_send_btn.click(
        fn=chat_wrapper,
        inputs=all_managed_components,
        outputs=[chatbot, chat_input, status_display],
    )

    chat_input.submit(
        fn=chat_wrapper,
        inputs=all_managed_components,
        outputs=[chatbot, chat_input, status_display],
    )

    clear_chat_btn.click(fn=clear_chat_wrapper, outputs=[chatbot, status_display])
