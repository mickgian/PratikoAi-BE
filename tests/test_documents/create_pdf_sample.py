#!/usr/bin/env python3
"""
Create sample PDF document for Italian tax document testing.

This creates a simple PDF that simulates an Italian tax document.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_sample_tax_pdf():
    """Create a sample Italian tax document PDF"""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "sample_dichiarazione_redditi.pdf")
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Container for elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'], 
        fontSize=12,
        alignment=TA_LEFT,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    # Title
    title = Paragraph("DICHIARAZIONE DEI REDDITI PERSONE FISICHE", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    subtitle = Paragraph("MODELLO 730/2024 - ANNO D'IMPOSTA 2023", title_style)
    elements.append(subtitle)
    elements.append(Spacer(1, 1*cm))
    
    # Taxpayer information
    taxpayer_header = Paragraph("DATI DEL CONTRIBUENTE", header_style)
    elements.append(taxpayer_header)
    elements.append(Spacer(1, 0.3*cm))
    
    taxpayer_info = [
        ["Cognome e Nome:", "ROSSI MARIO"],
        ["Codice Fiscale:", "RSSMRA85M01H501Z"],
        ["Data di nascita:", "01/09/1985"],
        ["Luogo di nascita:", "Roma (RM)"],
        ["Residenza:", "Via Giuseppe Verdi 123, 00100 Roma (RM)"],
        ["Partita IVA:", "01234567890"]
    ]
    
    taxpayer_table = Table(taxpayer_info, colWidths=[4*cm, 10*cm])
    taxpayer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(taxpayer_table)
    elements.append(Spacer(1, 1*cm))
    
    # Income data
    income_header = Paragraph("REDDITI DICHIARATI", header_style)
    elements.append(income_header)
    elements.append(Spacer(1, 0.3*cm))
    
    income_data = [
        ["Rigo", "Descrizione", "Importo (€)"],
        ["RN1", "Redditi da lavoro dipendente", "35.000,00"],
        ["RN3", "Redditi da lavoro autonomo", "12.000,00"],
        ["RN5", "Redditi di capitale", "850,00"],
        ["RN6", "Redditi diversi", "200,00"],
        ["", "TOTALE REDDITI COMPLESSIVI", "48.050,00"],
    ]
    
    income_table = Table(income_data, colWidths=[2*cm, 8*cm, 4*cm])
    income_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightyellow),
    ]))
    elements.append(income_table)
    elements.append(Spacer(1, 1*cm))
    
    # Tax calculation
    tax_header = Paragraph("CALCOLO DELL'IMPOSTA", header_style)
    elements.append(tax_header)
    elements.append(Spacer(1, 0.3*cm))
    
    tax_data = [
        ["Voce", "Importo (€)"],
        ["Reddito imponibile", "48.050,00"],
        ["Imposta lorda IRPEF", "11.285,00"],
        ["Detrazioni per lavoro dipendente", "1.200,00"],
        ["Detrazioni per carichi di famiglia", "800,00"],
        ["Imposta netta", "9.285,00"],
        ["Ritenute d'acconto", "8.500,00"],
        ["Crediti d'imposta", "250,00"],
        ["SALDO A DEBITO", "535,00"],
    ]
    
    tax_table = Table(tax_data, colWidths=[10*cm, 4*cm])
    tax_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightcoral),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(tax_table)
    elements.append(Spacer(1, 1*cm))
    
    # Footer
    footer_text = f"""
    <para>
    Dichiarazione compilata in data: {datetime.now().strftime('%d/%m/%Y')}<br/>
    Firma del contribuente: _________________________<br/><br/>
    
    <i>Documento generato automaticamente per scopi di test.<br/>
    Tutti i dati sono fittizi e utilizzati esclusivamente per testing del sistema PratikoAI.</i>
    </para>
    """
    
    footer = Paragraph(footer_text, normal_style)
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    return pdf_path

def main():
    """Create the sample PDF"""
    try:
        pdf_path = create_sample_tax_pdf()
        filename = os.path.basename(pdf_path)
        print(f"✅ Successfully created PDF: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        return False

if __name__ == "__main__":
    print("Creating sample Italian tax PDF document...")
    main()