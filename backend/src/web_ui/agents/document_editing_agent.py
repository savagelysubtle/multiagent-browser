import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from langchain.schema import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from ..config import config
from ..services.chroma_service import ChromaService
from ..services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class DocumentEditingAgent:
    """Enhanced document editing agent with comprehensive format support"""

    def __init__(self, llm_provider: str = "anthropic"):
        # ...existing initialization code...
        self.chroma_service = ChromaService()
        self.document_processor = DocumentProcessor()

        # Enhanced supported operations
        self.operations = {
            "create": self.create_document,
            "edit": self.edit_document,
            "format": self.format_document,
            "convert": self.convert_document,
            "generate_from_template": self.generate_from_template,
            "extract_text": self.extract_text_from_file,
            "summarize": self.summarize_document,
            "translate": self.translate_document,
            "export": self.export_document,
            "batch_process": self.batch_process_documents,
        }

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process document editing request with enhanced capabilities"""
        try:
            operation = request.get("operation", "edit")

            if operation not in self.operations:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}",
                    "supported_operations": list(self.operations.keys())
                }

            result = await self.operations[operation](request)

            # Store operation in history
            await self._store_operation_history(request, result)

            return result

        except Exception as e:
            logger.error(f"Error processing document request: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "operation": request.get("operation", "unknown")
            }

    async def create_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document with AI assistance"""
        # ...existing create_document code...
        document_type = request.get("document_type", "markdown")
        content_request = request.get("content", "")
        template_name = request.get("template")

        if template_name:
            # Create from template
            template_data = request.get("template_data", {})
            result = await self.document_processor.create_document_from_template(
                template_name, template_data, document_type
            )

            if result["success"]:
                # Store in ChromaDB
                doc_id = await self._store_document(result["document"], request)
                result["document_id"] = doc_id

            return result
        else:
            # Create with AI assistance
            # ...existing AI-assisted creation logic...
            pass

    async def convert_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Convert document between formats"""
        try:
            source_format = request.get("source_format", "markdown")
            target_format = request.get("target_format", "pdf")
            content = request.get("content", "")
            file_path = request.get("file_path")

            if file_path:
                # Process file
                result = await self.document_processor.process_file(file_path, target_format)
            else:
                # Convert content
                result = await self.document_processor.convert_document(
                    content, source_format, target_format
                )

            return result

        except Exception as e:
            logger.error(f"Error converting document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_from_template(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate document from template with AI data filling"""
        try:
            template_name = request.get("template_name")
            user_input = request.get("user_input", "")
            output_format = request.get("output_format", "pdf")

            if not template_name:
                return {
                    "success": False,
                    "error": "Template name is required"
                }

            # Use AI to extract data from user input
            template_data = await self._extract_template_data(user_input, template_name)

            # Generate document
            result = await self.document_processor.create_document_from_template(
                template_name, template_data, output_format
            )

            return result

        except Exception as e:
            logger.error(f"Error generating from template: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def extract_text_from_file(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process text from uploaded files"""
        try:
            file_path = request.get("file_path")
            target_format = request.get("target_format", "markdown")

            if not file_path:
                return {
                    "success": False,
                    "error": "File path is required"
                }

            result = await self.document_processor.process_file(file_path, target_format)

            # Optionally store extracted content
            if result.get("success") and request.get("store", False):
                doc_id = await self._store_document(result["content"], request)
                result["document_id"] = doc_id

            return result

        except Exception as e:
            logger.error(f"Error extracting text from file: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def export_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Export document in specified format"""
        try:
            document_id = request.get("document_id")
            output_format = request.get("output_format", "pdf")

            # Retrieve document from ChromaDB
            document = await self.chroma_service.get_document(document_id)

            if not document:
                return {
                    "success": False,
                    "error": "Document not found"
                }

            # Convert to target format
            result = await self.document_processor.convert_document(
                document["content"], "markdown", output_format
            )

            return result

        except Exception as e:
            logger.error(f"Error exporting document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def batch_process_documents(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process multiple documents in batch"""
        try:
            file_paths = request.get("file_paths", [])
            operation = request.get("batch_operation", "extract")
            target_format = request.get("target_format", "markdown")

            results = []

            for file_path in file_paths:
                if operation == "extract":
                    result = await self.document_processor.process_file(file_path, target_format)
                elif operation == "convert":
                    result = await self.document_processor.process_file(file_path, target_format)
                else:
                    result = {
                        "success": False,
                        "error": f"Unsupported batch operation: {operation}",
                        "file_path": file_path
                    }

                result["file_path"] = file_path
                results.append(result)

            success_count = sum(1 for r in results if r.get("success"))

            return {
                "success": True,
                "processed": len(results),
                "successful": success_count,
                "failed": len(results) - success_count,
                "results": results
            }

        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _extract_template_data(self, user_input: str, template_name: str) -> Dict[str, Any]:
        """Use AI to extract data for template from user input"""
        template_fields = {
            'business_letter': ['recipient_name', 'recipient_address', 'salutation', 'body', 'sender_name', 'sender_title', 'sender_company'],
            'report': ['title', 'author', 'department', 'executive_summary', 'introduction', 'findings', 'recommendations', 'conclusion'],
            'memo': ['to', 'from', 'date', 'subject', 'body'],
            'invoice': ['invoice_number', 'client_name', 'client_address', 'items', 'total', 'due_date']
        }

        fields = template_fields.get(template_name, [])

        prompt = f"""
        Extract the following information from the user input for a {template_name}:

        Required fields: {', '.join(fields)}

        User input: {user_input}

        Please provide the extracted data in JSON format. If a field is not found, use a reasonable default or leave it empty.
        Add today's date as the 'date' field in YYYY-MM-DD format.
        """

        message = HumanMessage(content=prompt)
        response = await self.llm.ainvoke([message])

        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {}

            # Add default date
            data['date'] = datetime.now().strftime('%Y-%m-%d')

            return data

        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return {'date': datetime.now().strftime('%Y-%m-%d')}

    async def _store_document(self, content: Union[str, bytes], request: Dict[str, Any]) -> str:
        """Store document in ChromaDB"""
        try:
            if isinstance(content, bytes):
                # For binary content, we'll store metadata and file reference
                content_text = f"Binary document - {request.get('document_type', 'unknown')} format"
            else:
                content_text = content

            doc_id = await self.chroma_service.store_document(
                content=content_text,
                title=request.get("title", "Untitled Document"),
                document_type=request.get("document_type", "markdown"),
                metadata={
                    "operation": request.get("operation", "unknown"),
                    "created_at": datetime.now().isoformat(),
                    "format": request.get("document_type", "markdown"),
                    "template_used": request.get("template_name"),
                }
            )

            return doc_id

        except Exception as e:
            logger.error(f"Error storing document: {str(e)}")
            raise

    async def _store_operation_history(self, request: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Store operation history for analytics"""
        try:
            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": request.get("operation"),
                "success": result.get("success", False),
                "request_summary": {
                    "operation": request.get("operation"),
                    "document_type": request.get("document_type"),
                    "template": request.get("template_name"),
                },
                "result_summary": {
                    "success": result.get("success"),
                    "error": result.get("error"),
                }
            }

            # Store in separate collection for analytics
            await self.chroma_service.store_operation_history(history_entry)

        except Exception as e:
            logger.error(f"Error storing operation history: {str(e)}")
            # Don't fail the main operation for history logging errors
            pass