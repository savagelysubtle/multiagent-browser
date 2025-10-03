"""
User Document API Routes - User-Focused Document Operations
Provides endpoints for document creation, editing, and format conversion
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from web_ui.services.user_document_service import UserDocumentService
from web_ui.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter()

# Initialize service
user_document_service = UserDocumentService()


# Request/Response models
class CreateDocumentRequest(BaseModel):
    template_id: str
    title: str | None = None


class ExportDocumentRequest(BaseModel):
    content: str
    format: str  # pdf, docx, html, txt
    title: str = "document"


class PreviewRequest(BaseModel):
    content: str
    format: str = "html"


@router.get("/templates")
async def get_document_templates():
    """Get list of available document templates"""
    try:
        templates = await user_document_service.get_available_templates()
        return {"success": True, "templates": templates}
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_document_from_template(request: CreateDocumentRequest):
    """Create a new document from a template"""
    try:
        result = await user_document_service.create_document_from_template(
            template_id=request.template_id, title=request.title
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_document(request: ExportDocumentRequest):
    """Export document to specified format"""
    try:
        result = await user_document_service.export_document(
            content=request.content, format=request.format, title=request.title
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Return as streaming response
        def generate():
            yield result["data"]

        return StreamingResponse(
            generate(),
            media_type=result["mime_type"],
            headers={
                "Content-Disposition": f"attachment; filename={result['filename']}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_document(file: UploadFile = File(...)):
    """Import document from uploaded file"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Import using user document service
            result = await user_document_service.import_document(temp_file_path)

            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error"))

            return result

        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
async def preview_document(
    content: str = Form(...), format: str = Form(default="html")
):
    """Generate preview of document content"""
    try:
        if format == "html":
            # Convert markdown to HTML
            import markdown

            html_content = markdown.markdown(content)
            return {"success": True, "preview": html_content, "format": "html"}
        else:
            # For other formats, return plain text
            return {"success": True, "preview": content, "format": "text"}

    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported import and export formats"""
    return {
        "success": True,
        "import_formats": [
            {"format": "txt", "name": "Plain Text", "description": "Text files"},
            {"format": "md", "name": "Markdown", "description": "Markdown files"},
            {
                "format": "docx",
                "name": "Word Document",
                "description": "Microsoft Word documents",
            },
            {
                "format": "pdf",
                "name": "PDF",
                "description": "PDF documents (text extraction)",
            },
            {"format": "html", "name": "HTML", "description": "Web pages"},
            {"format": "rtf", "name": "Rich Text", "description": "Rich text format"},
        ],
        "export_formats": [
            {"format": "pdf", "name": "PDF", "description": "Portable Document Format"},
            {
                "format": "docx",
                "name": "Word Document",
                "description": "Microsoft Word document",
            },
            {"format": "html", "name": "HTML", "description": "Web page"},
            {"format": "txt", "name": "Plain Text", "description": "Plain text file"},
        ],
        "template_formats": ["markdown"],
    }
