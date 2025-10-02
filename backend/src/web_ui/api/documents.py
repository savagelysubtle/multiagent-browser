"""
Enhanced Document API endpoints with comprehensive format support
"""

import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents.document_editing_agent import DocumentEditingAgent
from ..dependencies import get_current_user
from ..models.user import User
from ..services.document_processor import DocumentProcessor

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Enhanced request models
class DocumentConversionRequest(BaseModel):
    content: str
    source_format: str
    target_format: str
    title: Optional[str] = None

class TemplateGenerationRequest(BaseModel):
    template_name: str
    user_input: str
    output_format: str = "pdf"
    title: Optional[str] = None

class BatchProcessRequest(BaseModel):
    operation: str  # "extract", "convert"
    target_format: str = "markdown"
    file_paths: List[str]

class DocumentExportRequest(BaseModel):
    document_id: str
    output_format: str
    include_metadata: bool = False

# Initialize services
document_agent = DocumentEditingAgent()
document_processor = DocumentProcessor()

@router.post("/upload-and-process")
async def upload_and_process_file(
    file: UploadFile = File(...),
    target_format: str = Form("markdown"),
    store_result: bool = Form(False),
    current_user: User = Depends(get_current_user)
):
    """Upload and process a file with format conversion"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Process the file
            result = await document_processor.process_file(temp_file_path, target_format)

            if result.get("success"):
                # Optionally store in database
                if store_result:
                    request_data = {
                        "operation": "extract_text",
                        "file_path": temp_file_path,
                        "target_format": target_format,
                        "store": True,
                        "title": file.filename,
                        "document_type": target_format
                    }

                    agent_result = await document_agent.extract_text_from_file(request_data)
                    if agent_result.get("success"):
                        result["document_id"] = agent_result.get("document_id")

                result["original_filename"] = file.filename
                return result
            else:
                raise HTTPException(status_code=400, detail=result.get("error", "Processing failed"))

        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/convert")
async def convert_document(
    request: DocumentConversionRequest,
    current_user: User = Depends(get_current_user)
):
    """Convert document content between formats"""
    try:
        result = await document_processor.convert_document(
            request.content,
            request.source_format,
            request.target_format
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Conversion failed"))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-from-template")
async def generate_from_template(
    request: TemplateGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate document from template using AI to extract data"""
    try:
        agent_request = {
            "operation": "generate_from_template",
            "template_name": request.template_name,
            "user_input": request.user_input,
            "output_format": request.output_format,
            "title": request.title
        }

        result = await document_agent.generate_from_template(agent_request)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Generation failed"))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def get_available_templates(current_user: User = Depends(get_current_user)):
    """Get list of available document templates"""
    return {
        "templates": [
            {
                "name": "business_letter",
                "description": "Professional business letter template",
                "fields": ["recipient_name", "recipient_address", "salutation", "body", "sender_name", "sender_title", "sender_company"]
            },
            {
                "name": "report",
                "description": "Comprehensive report template",
                "fields": ["title", "author", "department", "executive_summary", "introduction", "findings", "recommendations", "conclusion"]
            },
            {
                "name": "memo",
                "description": "Internal memo template",
                "fields": ["to", "from", "date", "subject", "body"]
            },
            {
                "name": "invoice",
                "description": "Professional invoice template",
                "fields": ["invoice_number", "client_name", "client_address", "items", "total", "due_date"]
            }
        ]
    }

@router.post("/batch-process")
async def batch_process_documents(
    files: List[UploadFile] = File(...),
    operation: str = Form("extract"),
    target_format: str = Form("markdown"),
    current_user: User = Depends(get_current_user)
):
    """Process multiple files in batch"""
    try:
        temp_files = []
        file_paths = []

        # Save all uploaded files temporarily
        for file in files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_files.append(temp_file.name)
                file_paths.append(temp_file.name)

        try:
            # Process batch
            agent_request = {
                "operation": "batch_process",
                "file_paths": file_paths,
                "batch_operation": operation,
                "target_format": target_format
            }

            result = await document_agent.batch_process_documents(agent_request)

            # Add original filenames to results
            for i, file_result in enumerate(result.get("results", [])):
                if i < len(files):
                    file_result["original_filename"] = files[i].filename

            return result

        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                Path(temp_file).unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/{document_id}")
async def export_document(
    document_id: str,
    request: DocumentExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export document in specified format"""
    try:
        agent_request = {
            "operation": "export",
            "document_id": document_id,
            "output_format": request.output_format
        }

        result = await document_agent.export_document(agent_request)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Export failed"))

        # If result contains binary data, return as streaming response
        if isinstance(result.get("content"), bytes):
            def generate():
                yield result["content"]

            content_type = {
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "html": "text/html",
                "txt": "text/plain"
            }.get(request.output_format, "application/octet-stream")

            filename = f"document_{document_id}.{request.output_format}"

            return StreamingResponse(
                generate(),
                media_type=content_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-formats")
async def get_supported_formats(current_user: User = Depends(get_current_user)):
    """Get list of supported input and output formats"""
    return {
        "input_formats": [
            "txt", "md", "markdown", "html", "htm", "rtf", "csv", "json",
            "docx", "doc", "xlsx", "xls", "pptx", "ppt", "pdf",
            "xml", "yaml", "yml"
        ],
        "output_formats": [
            "markdown", "html", "pdf", "docx", "txt", "json"
        ],
        "template_formats": [
            "pdf", "docx", "html", "markdown"
        ]
    }

@router.get("/processing-status/{task_id}")
async def get_processing_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of long-running document processing task"""
    # This would integrate with a task queue system like Celery
    # For now, return a placeholder
    return {
        "task_id": task_id,
        "status": "completed",  # pending, processing, completed, failed
        "progress": 100,
        "result": None
    }

@router.post("/create-template")
async def create_custom_template(
    name: str = Form(...),
    content: str = Form(...),
    description: str = Form(""),
    fields: List[str] = Form(...),
    current_user: User = Depends(get_current_user)
):
    """Create a custom document template"""
    try:
        # This would store the template in the database
        # For now, return success response
        return {
            "success": True,
            "template": {
                "name": name,
                "description": description,
                "content": content,
                "fields": fields,
                "created_by": current_user.id,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))