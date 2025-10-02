"""
User Document API - User-focused endpoints for document creation and editing
"""

import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..dependencies import get_current_user
from ..models.user import User
from ..services.user_document_service import UserDocumentService

router = APIRouter(prefix="/api/user-documents", tags=["user-documents"])

# Request models for user document operations
class CreateDocumentRequest(BaseModel):
    template_id: str
    title: Optional[str] = None

class ExportDocumentRequest(BaseModel):
    content: str
    format: str  # pdf, docx, html, txt
    title: str = "document"

class CreateSpreadsheetRequest(BaseModel):
    data: List[List[str]]
    title: str = "spreadsheet"

class CreatePresentationRequest(BaseModel):
    slides: List[dict]  # [{"title": "...", "content": "..."}]
    title: str = "presentation"

# Initialize service
document_service = UserDocumentService()

@router.get("/templates")
async def get_document_templates(current_user: User = Depends(get_current_user)):
    """Get available document templates for users"""
    try:
        templates = await document_service.get_available_templates()
        return {
            "success": True,
            "templates": templates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_document_from_template(
    request: CreateDocumentRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new document from a template"""
    try:
        result = await document_service.create_document_from_template(
            request.template_id,
            request.title
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export")
async def export_document(
    request: ExportDocumentRequest,
    current_user: User = Depends(get_current_user)
):
    """Export document content to various formats"""
    try:
        result = await document_service.export_document(
            request.content,
            request.format,
            request.title
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Return as streaming response for file download
        def generate():
            yield result["data"]

        return StreamingResponse(
            generate(),
            media_type=result["mime_type"],
            headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import")
async def import_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Import a document file and convert to editable format"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Import the document
            result = await document_service.import_document(temp_file_path)

            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error"))

            result["original_filename"] = file.filename
            return result

        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-spreadsheet")
async def create_spreadsheet(
    request: CreateSpreadsheetRequest,
    current_user: User = Depends(get_current_user)
):
    """Create an Excel spreadsheet from data"""
    try:
        result = await document_service.create_spreadsheet(
            request.data,
            request.title
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Return as streaming response for file download
        def generate():
            yield result["data"]

        return StreamingResponse(
            generate(),
            media_type=result["mime_type"],
            headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-presentation")
async def create_presentation(
    request: CreatePresentationRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a PowerPoint presentation from slide data"""
    try:
        result = await document_service.create_presentation(
            request.slides,
            request.title
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Return as streaming response for file download
        def generate():
            yield result["data"]

        return StreamingResponse(
            generate(),
            media_type=result["mime_type"],
            headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-formats")
async def get_supported_formats(current_user: User = Depends(get_current_user)):
    """Get list of supported import and export formats"""
    return {
        "import_formats": [
            {"extension": "txt", "name": "Plain Text", "description": "Simple text files"},
            {"extension": "md", "name": "Markdown", "description": "Markdown formatted text"},
            {"extension": "docx", "name": "Word Document", "description": "Microsoft Word documents"},
            {"extension": "pdf", "name": "PDF", "description": "Portable Document Format"},
            {"extension": "html", "name": "HTML", "description": "Web pages"},
            {"extension": "rtf", "name": "Rich Text", "description": "Rich Text Format"}
        ],
        "export_formats": [
            {"format": "pdf", "name": "PDF", "description": "Portable Document Format"},
            {"format": "docx", "name": "Word Document", "description": "Microsoft Word document"},
            {"format": "html", "name": "HTML", "description": "Web page"},
            {"format": "txt", "name": "Plain Text", "description": "Simple text file"}
        ]
    }

@router.post("/preview")
async def preview_document(
    content: str = Form(...),
    format: str = Form("html"),
    current_user: User = Depends(get_current_user)
):
    """Generate a preview of document content in specified format"""
    try:
        if format == "html":
            # Convert markdown to HTML for preview
            import markdown
            html_content = markdown.markdown(content)
            return {
                "success": True,
                "preview": html_content,
                "format": "html"
            }
        else:
            return {
                "success": False,
                "error": f"Preview format '{format}' not supported"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))