"""
Minimal Document Upload API Endpoints for Demo.

FastAPI endpoints for drag & drop document upload functionality demo.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.document_simple import DOCUMENT_CONFIG
from app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/config/upload-limits", response_model=Dict[str, Any])
async def get_upload_configuration():
  """Get upload limits and supported file types for frontend."""
  return {
    "max_file_size_mb": DOCUMENT_CONFIG["MAX_FILE_SIZE_MB"],
    "max_files_per_upload": DOCUMENT_CONFIG["MAX_FILES_PER_UPLOAD"],
    "supported_file_types": {
      "PDF": {
        "extensions": [".pdf"],
        "mime_types": ["application/pdf"],
        "description": "Fatture elettroniche, F24, dichiarazioni fiscali"
      },
      "Excel": {
        "extensions": [".xlsx", ".xls"],
        "mime_types": [
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "application/vnd.ms-excel"
        ],
        "description": "Bilanci, registri IVA, contabilità"
      },
      "CSV": {
        "extensions": [".csv"],
        "mime_types": ["text/csv"],
        "description": "Registri IVA, estratti conto, dati contabili"
      }
    },
    "processing_timeout_seconds": DOCUMENT_CONFIG["PROCESSING_TIMEOUT_SECONDS"],
    "default_expiration_hours": DOCUMENT_CONFIG["DEFAULT_EXPIRATION_HOURS"],
    "italian_text": {
      "drop_zone_text": "Trascina qui i tuoi documenti fiscali (PDF, Excel, CSV)",
      "or_browse": "oppure seleziona i file",
      "max_size_text": f"Massimo {DOCUMENT_CONFIG['MAX_FILE_SIZE_MB']}MB per file, fino a {DOCUMENT_CONFIG['MAX_FILES_PER_UPLOAD']} file",
      "supported_formats": "Formati supportati: fatture elettroniche, F24, bilanci, registri IVA",
      "processing_time": "I documenti verranno elaborati automaticamente e conservati per 48 ore"
    }
  }


@router.post("/upload", response_model=Dict[str, Any])
async def upload_documents_demo(
  files: List[UploadFile] = File(..., description="Documents to upload (max 5 files, 10MB each)"),
  analysis_query: Optional[str] = Form(None, description="Optional analysis question")
):
  """
  Demo upload endpoint for document processing.
  
  This is a demonstration endpoint that validates files and returns mock responses.
  In the full implementation, this would process documents and store them securely.
  """
  try:
    # Basic validation
    if len(files) > DOCUMENT_CONFIG["MAX_FILES_PER_UPLOAD"]:
      raise HTTPException(
        status_code=400, 
        detail=f"Too many files. Maximum {DOCUMENT_CONFIG['MAX_FILES_PER_UPLOAD']} files allowed."
      )
    
    results = []
    for file in files:
      file_size = 0
      if hasattr(file, 'size') and file.size:
        file_size = file.size
      else:
        # Read to get size
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset
      
      if file_size > DOCUMENT_CONFIG["MAX_FILE_SIZE_MB"] * 1024 * 1024:
        results.append({
          "filename": file.filename,
          "status": "error",
          "error": f"File too large (max {DOCUMENT_CONFIG['MAX_FILE_SIZE_MB']}MB)"
        })
        continue
      
      # Mock successful upload
      results.append({
        "filename": file.filename,
        "status": "uploaded",
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "message": "File uploaded successfully (demo mode)",
        "processing_status": "demo"
      })
    
    logger.info(f"Demo upload: {len(files)} files processed")
    
    return {
      "success": True,
      "message": f"Demo: {len(results)} files processed",
      "files": results,
      "analysis_query": analysis_query,
      "demo_mode": True,
      "note": "This is a demonstration. In production, files would be processed and analyzed by AI."
    }
  
  except Exception as e:
    logger.error(f"Demo upload error: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Upload demo error: {str(e)}")


@router.get("/demo-status")
async def get_demo_status():
  """Get status of document upload demo system."""
  return {
    "status": "active",
    "version": "1.0.0",
    "features": [
      "Drag & drop file upload",
      "Italian tax document support",
      "File validation and security checks",
      "AI-powered document analysis",
      "GDPR-compliant storage"
    ],
    "demo_limitations": [
      "Files are not actually stored",
      "No real AI analysis performed",
      "No user authentication required"
    ],
    "supported_documents": [
      "Fatture Elettroniche (PDF)",
      "F24 Tax Forms (PDF)", 
      "Bilanci e Registri IVA (Excel/CSV)",
      "Dichiarazioni Fiscali (PDF)"
    ]
  }