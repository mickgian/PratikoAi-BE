#!/usr/bin/env python3
"""
Standalone Demo App for PratikoAI Document Upload Functionality.

This is a minimal FastAPI app that demonstrates the document upload
and processing features we've implemented.
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Import our new document functionality
from app.api.v1.documents_minimal import router as documents_router
from app.api.v1.demo import router as demo_router

# Create FastAPI app
app = FastAPI(
    title="PratikoAI Document Processing Demo",
    description="Demo of drag & drop document upload and AI analysis for Italian tax professionals",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include our routers
app.include_router(documents_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with links to demo features."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PratikoAI Document Processing Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .card { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
            .button { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
            .button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <h1>🚀 PratikoAI Document Processing Demo</h1>
        <p>This demo showcases the document upload and processing functionality we've implemented.</p>
        
        <div class="card">
            <h3>📄 Document Upload Demo</h3>
            <p>Try the drag & drop interface for Italian tax document upload.</p>
            <a href="/api/v1/demo/document-upload" class="button">Open Upload Interface</a>
        </div>
        
        <div class="card">
            <h3>📚 API Documentation</h3>
            <p>Explore the complete API documentation with interactive testing.</p>
            <a href="/docs" class="button">View API Docs (Swagger)</a>
            <a href="/redoc" class="button">View ReDoc</a>
        </div>
        
        <div class="card">
            <h3>🔧 API Endpoints</h3>
            <ul>
                <li><strong>GET /api/v1/documents/config/upload-limits</strong> - Upload configuration</li>
                <li><strong>POST /api/v1/documents/upload</strong> - Upload documents</li>
                <li><strong>GET /api/v1/documents/demo-status</strong> - Demo status</li>
            </ul>
        </div>
        
        <div class="card">
            <h3>✨ Features Implemented</h3>
            <ul>
                <li>✅ Drag & drop file upload interface</li>
                <li>✅ Italian tax document support (PDF, Excel, CSV)</li>
                <li>✅ File validation and security checks</li>
                <li>✅ Document processing services (PDF, Excel, CSV)</li>
                <li>✅ AI-powered document analysis</li>
                <li>✅ Secure encrypted storage</li>
                <li>✅ GDPR-compliant document handling</li>
                <li>✅ Italian language interface</li>
            </ul>
        </div>
        
        <div class="card">
            <h3>📊 Supported Documents</h3>
            <ul>
                <li><strong>PDF:</strong> Fatture Elettroniche, F24, Dichiarazioni Fiscali</li>
                <li><strong>Excel:</strong> Bilanci, Registri IVA, Contabilità</li>
                <li><strong>CSV:</strong> Registri IVA, Estratti Conto, Dati Contabili</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "pratikoai-document-demo"}

if __name__ == "__main__":
    print("🚀 Starting PratikoAI Document Processing Demo...")
    print("📄 Document Upload Demo: http://localhost:8001/api/v1/demo/document-upload")
    print("📚 API Documentation: http://localhost:8001/docs")
    print("🏠 Home Page: http://localhost:8001/")
    
    uvicorn.run(
        "demo_app:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )