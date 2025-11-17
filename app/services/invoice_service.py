"""Italian Invoice Service with Fattura Elettronica Support.

This service generates invoices compliant with Italian regulations including
electronic invoice (fattura elettronica) XML generation for SDI transmission.
"""

import asyncio
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.subscription import Invoice, Subscription, SubscriptionPlan
from app.services.cache import get_redis_client


@dataclass
class InvoiceData:
    """Invoice data structure for Italian invoices"""

    invoice_number: str
    invoice_date: datetime
    due_date: datetime

    # Supplier data (PratikoAI)
    supplier_name: str
    supplier_partita_iva: str
    supplier_address: str
    supplier_cap: str
    supplier_city: str
    supplier_province: str

    # Customer data
    customer_name: str
    customer_partita_iva: str | None
    customer_codice_fiscale: str | None
    customer_address: str
    customer_cap: str
    customer_city: str
    customer_province: str
    customer_sdi_code: str | None
    customer_pec_email: str | None

    # Invoice lines
    lines: list[dict[str, Any]]

    # Totals
    subtotal: Decimal  # Imponibile
    iva_amount: Decimal  # IVA 22%
    total_amount: Decimal  # Totale

    # Payment info
    payment_method: str = "MP05"  # Bonifico

    @property
    def is_business_customer(self) -> bool:
        """Check if customer is business (has Partita IVA)"""
        return bool(self.customer_partita_iva)


class ItalianInvoiceService:
    """Service for generating Italian invoices with fattura elettronica support.

    Handles:
    - PDF invoice generation
    - Electronic invoice XML generation (fattura elettronica)
    - SDI (Sistema di Interscambio) compliance
    - Invoice numbering and sequencing
    - Italian tax regulations compliance
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.redis = get_redis_client()

        # Company information (PratikoAI)
        self.company_info = {
            "denominazione": "PratikoAI SRL",
            "partita_iva": settings.COMPANY_PARTITA_IVA or "12345678901",  # Configure in settings
            "codice_fiscale": settings.COMPANY_CODICE_FISCALE or "12345678901",
            "indirizzo": "Via dell'Innovazione 123",
            "cap": "00100",
            "comune": "Roma",
            "provincia": "RM",
            "nazione": "IT",
            "telefono": "+39 06 12345678",
            "email": "fatture@pratikoai.it",
            "pec": "fatture@pec.pratikoai.it",
        }

        # Invoice configuration
        self.invoice_config = {
            "numero_progressivo_anno": datetime.now().year,
            "formato_trasmissione": "FPR12",  # B2B format
            "codice_destinatario_default": "0000000",  # For individuals
            "tipo_documento": "TD01",  # Standard invoice
            "divisa": "EUR",
            "aliquota_iva": Decimal("22.00"),
        }

    async def generate_invoice(
        self, subscription: Subscription, payment_amount: Decimal, invoice_date: datetime | None = None
    ) -> tuple[InvoiceData, bytes]:
        """Generate complete invoice (PDF + XML if business customer).

        Args:
            subscription: Subscription object
            payment_amount: Total payment amount including IVA
            invoice_date: Invoice date (defaults to now)

        Returns:
            Tuple of (InvoiceData, PDF bytes)
        """
        if not invoice_date:
            invoice_date = datetime.now()

        # Generate invoice number
        invoice_number = await self.get_next_invoice_number()

        # Create invoice data
        invoice_data = await self._create_invoice_data(
            subscription=subscription,
            payment_amount=payment_amount,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
        )

        # Generate PDF
        pdf_content = await self._generate_pdf_invoice(invoice_data)

        # Create database record
        invoice_record = Invoice(
            subscription_id=subscription.id,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=invoice_date + timedelta(days=30),
            subtotal=invoice_data.subtotal,
            iva_amount=invoice_data.iva_amount,
            total_amount=invoice_data.total_amount,
            payment_status="pending",
        )

        # Generate XML for business customers
        if subscription.is_business:
            xml_content = await self._generate_fattura_elettronica_xml(invoice_data)
            invoice_record.fattura_elettronica_xml = xml_content

            # Queue for SDI transmission (would be handled by background job)
            await self._queue_for_sdi_transmission(invoice_record, xml_content)

        # Save invoice
        self.db.add(invoice_record)
        await self.db.commit()

        logger.info(f"Generated invoice {invoice_number} for subscription {subscription.id}")

        return invoice_data, pdf_content

    async def generate_fattura_elettronica_xml(
        self, subscription: Subscription, payment_amount: Decimal, invoice_number: str | None = None
    ) -> str:
        """Generate electronic invoice XML for SDI transmission.

        Args:
            subscription: Subscription object
            payment_amount: Total payment amount
            invoice_number: Invoice number (generated if not provided)

        Returns:
            XML content as string
        """
        if not invoice_number:
            invoice_number = await self.get_next_invoice_number()

        invoice_data = await self._create_invoice_data(
            subscription=subscription,
            payment_amount=payment_amount,
            invoice_number=invoice_number,
            invoice_date=datetime.now(),
        )

        return await self._generate_fattura_elettronica_xml(invoice_data)

    async def get_next_invoice_number(self) -> str:
        """Get next invoice number in sequence.

        Returns:
            Invoice number in format YYYY/NNNN
        """
        year = datetime.now().year

        # Get last invoice number for current year
        stmt = select(func.max(Invoice.invoice_number)).where(Invoice.invoice_number.like(f"{year}/%"))
        result = await self.db.execute(stmt)
        last_number = result.scalar()

        if last_number:
            # Extract sequence number and increment
            sequence = int(last_number.split("/")[1]) + 1
        else:
            # First invoice of the year
            sequence = 1

        return f"{year}/{sequence:04d}"

    async def _create_invoice_data(
        self, subscription: Subscription, payment_amount: Decimal, invoice_number: str, invoice_date: datetime
    ) -> InvoiceData:
        """Create structured invoice data"""
        # Calculate amounts
        if subscription.plan.billing_period.value == "annual":
            base_price = Decimal("599.00")
            description = "Abbonamento Professionale Annuale"
        else:
            base_price = Decimal("69.00")
            description = "Abbonamento Professionale Mensile"

        iva_amount = base_price * self.invoice_config["aliquota_iva"] / 100
        total_amount = base_price + iva_amount

        # Create invoice lines
        lines = [
            {
                "numero_riga": 1,
                "descrizione": description,
                "quantita": 1,
                "unita_misura": "pz",
                "prezzo_unitario": base_price,
                "prezzo_totale": base_price,
                "aliquota_iva": self.invoice_config["aliquota_iva"],
                "natura": None,  # No exemption
            }
        ]

        return InvoiceData(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=invoice_date + timedelta(days=30),
            # Supplier (PratikoAI)
            supplier_name=self.company_info["denominazione"],
            supplier_partita_iva=self.company_info["partita_iva"],
            supplier_address=self.company_info["indirizzo"],
            supplier_cap=self.company_info["cap"],
            supplier_city=self.company_info["comune"],
            supplier_province=self.company_info["provincia"],
            # Customer
            customer_name=subscription.invoice_name,
            customer_partita_iva=subscription.partita_iva,
            customer_codice_fiscale=subscription.codice_fiscale,
            customer_address=subscription.invoice_address,
            customer_cap=subscription.invoice_cap,
            customer_city=subscription.invoice_city,
            customer_province=subscription.invoice_province,
            customer_sdi_code=subscription.sdi_code,
            customer_pec_email=subscription.pec_email,
            # Invoice details
            lines=lines,
            subtotal=base_price,
            iva_amount=iva_amount,
            total_amount=total_amount,
        )

    async def _generate_pdf_invoice(self, invoice_data: InvoiceData) -> bytes:
        """Generate PDF invoice.

        Args:
            invoice_data: Invoice data structure

        Returns:
            PDF content as bytes
        """
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center
        )

        story = []

        # Header
        story.append(Paragraph("FATTURA", title_style))
        story.append(Spacer(1, 20))

        # Company info
        company_data = [
            ["FORNITORE:", ""],
            [invoice_data.supplier_name, ""],
            [f"P.IVA: {invoice_data.supplier_partita_iva}", ""],
            [invoice_data.supplier_address, ""],
            [f"{invoice_data.supplier_cap} {invoice_data.supplier_city} ({invoice_data.supplier_province})", ""],
        ]

        # Customer info
        customer_data = [
            ["CLIENTE:", ""],
            [invoice_data.customer_name, ""],
        ]

        if invoice_data.customer_partita_iva:
            customer_data.append([f"P.IVA: {invoice_data.customer_partita_iva}", ""])
        if invoice_data.customer_codice_fiscale:
            customer_data.append([f"C.F.: {invoice_data.customer_codice_fiscale}", ""])

        customer_data.extend(
            [
                [invoice_data.customer_address, ""],
                [f"{invoice_data.customer_cap} {invoice_data.customer_city} ({invoice_data.customer_province})", ""],
            ]
        )

        # Create header table
        header_data = []
        max_rows = max(len(company_data), len(customer_data))

        for i in range(max_rows):
            row = []
            row.extend(company_data[i] if i < len(company_data) else ["", ""])
            row.extend(customer_data[i] if i < len(customer_data) else ["", ""])
            header_data.append(row)

        header_table = Table(header_data, colWidths=[8 * cm, 1 * cm, 8 * cm, 1 * cm])
        header_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, 0), "Helvetica-Bold"),
                ]
            )
        )

        story.append(header_table)
        story.append(Spacer(1, 30))

        # Invoice details
        details_data = [
            ["Numero:", invoice_data.invoice_number, "Data:", invoice_data.invoice_date.strftime("%d/%m/%Y")],
            ["Scadenza:", invoice_data.due_date.strftime("%d/%m/%Y"), "", ""],
        ]

        details_table = Table(details_data, colWidths=[3 * cm, 5 * cm, 3 * cm, 5 * cm])
        details_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ]
            )
        )

        story.append(details_table)
        story.append(Spacer(1, 30))

        # Invoice lines
        lines_data = [["Descrizione", "Qta", "Prezzo Unit.", "IVA%", "Totale"]]

        for line in invoice_data.lines:
            lines_data.append(
                [
                    line["descrizione"],
                    str(line["quantita"]),
                    f"€{line['prezzo_unitario']:.2f}",
                    f"{line['aliquota_iva']:.0f}%",
                    f"€{line['prezzo_totale']:.2f}",
                ]
            )

        lines_table = Table(lines_data, colWidths=[8 * cm, 2 * cm, 3 * cm, 2 * cm, 3 * cm])
        lines_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(lines_table)
        story.append(Spacer(1, 30))

        # Totals
        totals_data = [
            ["", "", "Imponibile:", f"€{invoice_data.subtotal:.2f}"],
            ["", "", f"IVA {self.invoice_config['aliquota_iva']:.0f}%:", f"€{invoice_data.iva_amount:.2f}"],
            ["", "", "TOTALE:", f"€{invoice_data.total_amount:.2f}"],
        ]

        totals_table = Table(totals_data, colWidths=[6 * cm, 4 * cm, 4 * cm, 4 * cm])
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (2, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (2, -1), (-1, -1), 14),
                    ("BACKGROUND", (2, -1), (-1, -1), colors.lightblue),
                ]
            )
        )

        story.append(totals_table)
        story.append(Spacer(1, 30))

        # Payment info
        payment_info = Paragraph(
            f"<b>Modalità di pagamento:</b> Bonifico bancario<br/>"
            f"<b>Scadenza:</b> {invoice_data.due_date.strftime('%d/%m/%Y')}",
            styles["Normal"],
        )
        story.append(payment_info)

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        return buffer.getvalue()

    async def _generate_fattura_elettronica_xml(self, invoice_data: InvoiceData) -> str:
        """Generate electronic invoice XML for SDI.

        Args:
            invoice_data: Invoice data structure

        Returns:
            XML content as string
        """
        # Create root element
        root = ET.Element("p:FatturaElettronica")
        root.set("versione", self.invoice_config["formato_trasmissione"])
        root.set("xmlns:ds", "http://www.w3.org/2000/09/xmldsig#")
        root.set("xmlns:p", "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set(
            "xsi:schemaLocation",
            "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd",
        )

        # Header
        header = ET.SubElement(root, "FatturaElettronicaHeader")

        # Transmission data
        transmission_data = ET.SubElement(header, "DatiTrasmissione")
        progressive_id = ET.SubElement(transmission_data, "IdTrasmittente")
        ET.SubElement(progressive_id, "IdPaese").text = "IT"
        ET.SubElement(progressive_id, "IdCodice").text = self.company_info["partita_iva"]
        ET.SubElement(transmission_data, "ProgressivoInvio").text = str(uuid.uuid4().hex[:5]).upper()
        ET.SubElement(transmission_data, "FormatoTrasmissione").text = self.invoice_config["formato_trasmissione"]
        ET.SubElement(transmission_data, "CodiceDestinatario").text = (
            invoice_data.customer_sdi_code or self.invoice_config["codice_destinatario_default"]
        )

        if invoice_data.customer_pec_email:
            ET.SubElement(transmission_data, "PECDestinatario").text = invoice_data.customer_pec_email

        # Supplier data (Cedente/Prestatore)
        supplier = ET.SubElement(header, "CedentePrestatore")
        supplier_data = ET.SubElement(supplier, "DatiAnagrafici")
        supplier_id = ET.SubElement(supplier_data, "IdFiscaleIVA")
        ET.SubElement(supplier_id, "IdPaese").text = "IT"
        ET.SubElement(supplier_id, "IdCodice").text = self.company_info["partita_iva"]
        ET.SubElement(supplier_data, "CodiceFiscale").text = self.company_info["codice_fiscale"]

        supplier_anagrafica = ET.SubElement(supplier_data, "Anagrafica")
        ET.SubElement(supplier_anagrafica, "Denominazione").text = self.company_info["denominazione"]

        ET.SubElement(supplier_data, "RegimeFiscale").text = "RF01"  # Ordinary regime

        supplier_address = ET.SubElement(supplier, "Sede")
        ET.SubElement(supplier_address, "Indirizzo").text = self.company_info["indirizzo"]
        ET.SubElement(supplier_address, "CAP").text = self.company_info["cap"]
        ET.SubElement(supplier_address, "Comune").text = self.company_info["comune"]
        ET.SubElement(supplier_address, "Provincia").text = self.company_info["provincia"]
        ET.SubElement(supplier_address, "Nazione").text = self.company_info["nazione"]

        # Customer data (Cessionario/Committente)
        customer = ET.SubElement(header, "CessionarioCommittente")
        customer_data = ET.SubElement(customer, "DatiAnagrafici")

        if invoice_data.customer_partita_iva:
            customer_id = ET.SubElement(customer_data, "IdFiscaleIVA")
            ET.SubElement(customer_id, "IdPaese").text = "IT"
            ET.SubElement(customer_id, "IdCodice").text = invoice_data.customer_partita_iva

        if invoice_data.customer_codice_fiscale:
            ET.SubElement(customer_data, "CodiceFiscale").text = invoice_data.customer_codice_fiscale

        customer_anagrafica = ET.SubElement(customer_data, "Anagrafica")
        ET.SubElement(customer_anagrafica, "Denominazione").text = invoice_data.customer_name

        customer_address = ET.SubElement(customer, "Sede")
        ET.SubElement(customer_address, "Indirizzo").text = invoice_data.customer_address
        ET.SubElement(customer_address, "CAP").text = invoice_data.customer_cap
        ET.SubElement(customer_address, "Comune").text = invoice_data.customer_city
        ET.SubElement(customer_address, "Provincia").text = invoice_data.customer_province
        ET.SubElement(customer_address, "Nazione").text = "IT"

        # Body
        body = ET.SubElement(root, "FatturaElettronicaBody")

        # General data
        general_data = ET.SubElement(body, "DatiGenerali")
        document_data = ET.SubElement(general_data, "DatiGeneraliDocumento")
        ET.SubElement(document_data, "TipoDocumento").text = self.invoice_config["tipo_documento"]
        ET.SubElement(document_data, "Divisa").text = self.invoice_config["divisa"]
        ET.SubElement(document_data, "Data").text = invoice_data.invoice_date.strftime("%Y-%m-%d")
        ET.SubElement(document_data, "Numero").text = invoice_data.invoice_number
        ET.SubElement(document_data, "ImportoTotaleDocumento").text = f"{invoice_data.total_amount:.2f}"

        # Lines
        lines_data = ET.SubElement(body, "DatiBeni")
        for line in invoice_data.lines:
            line_detail = ET.SubElement(lines_data, "DettaglioLinee")
            ET.SubElement(line_detail, "NumeroLinea").text = str(line["numero_riga"])
            ET.SubElement(line_detail, "Descrizione").text = line["descrizione"]
            ET.SubElement(line_detail, "Quantita").text = f"{line['quantita']:.2f}"
            ET.SubElement(line_detail, "UnitaMisura").text = line["unita_misura"]
            ET.SubElement(line_detail, "PrezzoUnitario").text = f"{line['prezzo_unitario']:.2f}"
            ET.SubElement(line_detail, "PrezzoTotale").text = f"{line['prezzo_totale']:.2f}"
            ET.SubElement(line_detail, "AliquotaIVA").text = f"{line['aliquota_iva']:.2f}"

        # Summary
        summary_data = ET.SubElement(body, "DatiRiepilogo")
        summary = ET.SubElement(summary_data, "DatiRiepilogo")
        ET.SubElement(summary, "AliquotaIVA").text = f"{self.invoice_config['aliquota_iva']:.2f}"
        ET.SubElement(summary, "ImponibileImporto").text = f"{invoice_data.subtotal:.2f}"
        ET.SubElement(summary, "Imposta").text = f"{invoice_data.iva_amount:.2f}"

        # Payment data
        payment_data = ET.SubElement(body, "DatiPagamento")
        ET.SubElement(payment_data, "CondizioniPagamento").text = "TP02"  # Complete payment

        payment_detail = ET.SubElement(payment_data, "DettaglioPagamento")
        ET.SubElement(payment_detail, "ModalitaPagamento").text = invoice_data.payment_method
        ET.SubElement(payment_detail, "DataScadenzaPagamento").text = invoice_data.due_date.strftime("%Y-%m-%d")
        ET.SubElement(payment_detail, "ImportoPagamento").text = f"{invoice_data.total_amount:.2f}"

        # Convert to string
        ET.indent(root, space="  ", level=0)
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    async def _queue_for_sdi_transmission(self, invoice: Invoice, xml_content: str):
        """Queue invoice for SDI transmission.

        Args:
            invoice: Invoice database record
            xml_content: XML content to transmit
        """
        # In a real implementation, this would queue the invoice for background processing
        # to transmit to the SDI (Sistema di Interscambio)

        transmission_data = {
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "xml_content": xml_content,
            "timestamp": datetime.now().isoformat(),
            "status": "queued",
        }

        # Queue in Redis for background job processing
        await self.redis.lpush("sdi_transmission_queue", str(transmission_data))

        logger.info(f"Queued invoice {invoice.invoice_number} for SDI transmission")

    async def process_sdi_transmission_queue(self):
        """Process queued invoices for SDI transmission.
        This would typically run as a background job.
        """
        while True:
            try:
                # Get next item from queue
                item = await self.redis.brpop("sdi_transmission_queue", timeout=10)
                if not item:
                    continue

                transmission_data = eval(item[1])  # In production, use proper JSON parsing

                # Simulate SDI transmission
                success = await self._transmit_to_sdi(
                    transmission_data["xml_content"], transmission_data["invoice_number"]
                )

                if success:
                    # Update invoice status
                    stmt = select(Invoice).where(Invoice.id == transmission_data["invoice_id"])
                    result = await self.db.execute(stmt)
                    invoice = result.scalar_one_or_none()

                    if invoice:
                        invoice.sdi_status = "sent"
                        invoice.sdi_sent_at = datetime.now()
                        await self.db.commit()

                logger.info(f"Processed SDI transmission for invoice {transmission_data['invoice_number']}")

            except Exception as e:
                logger.error(f"Error processing SDI transmission: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _transmit_to_sdi(self, xml_content: str, invoice_number: str) -> bool:
        """Simulate SDI transmission.
        In production, this would integrate with the actual SDI system.

        Args:
            xml_content: XML content to transmit
            invoice_number: Invoice number for logging

        Returns:
            True if transmission successful
        """
        # This would implement actual SDI transmission
        # For now, just simulate success
        logger.info(f"Simulating SDI transmission for invoice {invoice_number}")
        await asyncio.sleep(1)  # Simulate network delay
        return True
