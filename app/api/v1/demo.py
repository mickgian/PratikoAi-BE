"""Demo endpoints for document upload functionality.

Provides a simple web interface to demonstrate the drag & drop
document upload and analysis capabilities.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Get templates directory
templates_dir = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/document-upload", response_class=HTMLResponse)
async def demo_document_upload(request: Request):
    """Demo page for document upload functionality.

    Shows the drag & drop interface for Italian tax document upload and analysis.
    """
    return templates.TemplateResponse("document_upload.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def demo_index(request: Request):
    """Demo index page with links to all demo features."""
    html_content = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PratikoAI - Demo Features</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        .content {
            padding: 40px;
        }
        .feature-card {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }
        .feature-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        .feature-title {
            font-size: 1.4em;
            color: #333;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }
        .feature-icon {
            font-size: 1.8em;
            margin-right: 15px;
        }
        .feature-description {
            color: #666;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        .feature-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
        }
        .feature-link:hover {
            color: #764ba2;
        }
        .status-badge {
            background: #d4edda;
            color: #155724;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 PratikoAI Demo</h1>
            <p>Esplora le funzionalità avanzate per professionisti fiscali italiani</p>
        </div>

        <div class="content">
            <div class="feature-card" onclick="window.open('/api/v1/demo/document-upload', '_blank')">
                <div class="feature-title">
                    <span class="feature-icon">📄</span>
                    Caricamento Documenti con AI
                    <span class="status-badge">✅ Implementato</span>
                </div>
                <div class="feature-description">
                    Interfaccia drag & drop per caricare e analizzare documenti fiscali italiani.
                    Supporta fatture elettroniche, F24, bilanci e registri IVA con analisi AI automatica.
                </div>
                <a href="/api/v1/demo/document-upload" class="feature-link" target="_blank">
                    🔗 Prova la Demo →
                </a>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    <span class="feature-icon">💬</span>
                    Chat Intelligente per Consulenza Fiscale
                    <span class="status-badge">✅ Attivo</span>
                </div>
                <div class="feature-description">
                    Sistema di chat avanzato con conoscenza specializzata della normativa fiscale italiana.
                    Risponde a domande su IVA, imposte, adempimenti e pianificazione fiscale.
                </div>
                <a href="/docs#/chatbot" class="feature-link">
                    🔗 Vedi API Docs →
                </a>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    <span class="feature-icon">🔍</span>
                    Ricerca Normativa Avanzata
                    <span class="status-badge">✅ Attivo</span>
                </div>
                <div class="feature-description">
                    Ricerca intelligente attraverso circolari, risoluzioni e normative dell'Agenzia delle Entrate.
                    Risultati contestualizzati e aggiornati in tempo reale.
                </div>
                <a href="/docs#/regulatory" class="feature-link">
                    🔗 Vedi API Docs →
                </a>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    <span class="feature-icon">🏛️</span>
                    Calcolo Imposte Regionali
                    <span class="status-badge">✅ Attivo</span>
                </div>
                <div class="feature-description">
                    Calcolo automatico di IMU, TASI e altre imposte regionali per tutti i comuni italiani.
                    Supporta aliquote aggiornate e detrazioni specifiche per regione.
                </div>
                <a href="/docs#/regional-taxes" class="feature-link">
                    🔗 Vedi API Docs →
                </a>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    <span class="feature-icon">📊</span>
                    Sistema di Monitoraggio e Analytics
                    <span class="status-badge">✅ Attivo</span>
                </div>
                <div class="feature-description">
                    Dashboard di monitoraggio delle performance del sistema con metriche dettagliate,
                    monitoring degli errori e analisi dell'utilizzo.
                </div>
                <a href="/docs#/monitoring" class="feature-link">
                    🔗 Vedi API Docs →
                </a>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    <span class="feature-icon">🔒</span>
                    Sistema GDPR e Privacy
                    <span class="status-badge">✅ Attivo</span>
                </div>
                <div class="feature-description">
                    Gestione completa dei dati personali conforme GDPR con export automatico,
                    cancellazione sicura e audit trail completo.
                </div>
                <a href="/docs#/data-export" class="feature-link">
                    🔗 Vedi API Docs →
                </a>
            </div>

            <div style="margin-top: 40px; padding-top: 30px; border-top: 1px solid #e0e0e0; text-align: center; color: #666;">
                <p><strong>API Documentation:</strong> <a href="/docs" style="color: #667eea;">FastAPI Interactive Docs</a></p>
                <p><strong>Health Check:</strong> <a href="/api/v1/health" style="color: #667eea;">System Status</a></p>
            </div>
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html_content)
