"""DEV-411: Fattura Elettronica XML Parser.

Parses FatturaPA XML (SDI format) extracting:
- Fornitore/cliente anagrafica
- Line items
- Imponibili per aliquota, IVA split
- Totale documento, data emissione, numero fattura
- Ritenuta d'acconto if present

Handles both FatturaPA 1.2 schema and FatturaOrdinaria.
"""

import xml.etree.ElementTree as ET
from typing import Any

from app.core.logging import logger

# Namespace for FatturaPA 1.2
NS = {"p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"}


def _find_text(element: ET.Element | None, path: str, default: str = "") -> str:
    """Find text in element, searching with and without namespace."""
    if element is None:
        return default
    # Try without namespace first (most common in practice)
    el = element.find(path)
    if el is not None and el.text:
        return el.text.strip()
    # Try with namespace
    ns_path = "/".join(f"p:{p}" if p else p for p in path.split("/"))
    el = element.find(ns_path, NS)
    if el is not None and el.text:
        return el.text.strip()
    return default


def _find_all(element: ET.Element | None, path: str) -> list[ET.Element]:
    """Find all elements, searching with and without namespace."""
    if element is None:
        return []
    results = element.findall(path)
    if not results:
        ns_path = "/".join(f"p:{p}" if p else p for p in path.split("/"))
        results = element.findall(ns_path, NS)
    return results


class FatturaXmlParser:
    """Parser for Fattura Elettronica XML (SDI FatturaPA format)."""

    def parse(self, xml_content: str) -> dict[str, Any]:
        """Parse a Fattura Elettronica XML string.

        Args:
            xml_content: XML content as string.

        Returns:
            Parsed invoice data dictionary.

        Raises:
            ValueError: If XML is invalid or missing required elements.
        """
        if not xml_content or not xml_content.strip():
            raise ValueError("Il contenuto XML è vuoto")

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"XML non valido: {e}")

        # Find header and body
        header = root.find("FatturaElettronicaHeader")
        if header is None:
            header = root.find("p:FatturaElettronicaHeader", NS)
            if header is None:
                header = root.find(
                    "{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}FatturaElettronicaHeader"
                )

        body = root.find("FatturaElettronicaBody")
        if body is None:
            body = root.find("p:FatturaElettronicaBody", NS)
            if body is None:
                body = root.find(
                    "{http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2}FatturaElettronicaBody"
                )

        if body is None:
            raise ValueError("Elemento FatturaElettronicaBody non trovato nel XML")

        # Parse sections
        fornitore = self._parse_fornitore(header)
        cliente = self._parse_cliente(header)
        dati_generali = self._parse_dati_generali(body)
        linee = self._parse_linee(body)
        riepilogo = self._parse_riepilogo(body)
        ritenuta = self._parse_ritenuta(body)

        result: dict[str, Any] = {
            "fornitore": fornitore,
            "cliente": cliente,
            **dati_generali,
            "linee": linee,
            "riepilogo_iva": riepilogo,
        }

        if ritenuta:
            result["ritenuta_acconto"] = ritenuta

        logger.info(
            "fattura_xml_parsed",
            numero=dati_generali.get("numero_fattura"),
            linee_count=len(linee),
        )

        return result

    def _parse_fornitore(self, header: ET.Element | None) -> dict[str, Any]:
        """Parse CedentePrestatore (supplier) data."""
        if header is None:
            return {}

        cp = header.find(".//CedentePrestatore")
        if cp is None:
            return {}

        return {
            "partita_iva": _find_text(cp, ".//IdFiscaleIVA/IdCodice"),
            "paese": _find_text(cp, ".//IdFiscaleIVA/IdPaese"),
            "codice_fiscale": _find_text(cp, ".//DatiAnagrafici/CodiceFiscale"),
            "denominazione": _find_text(cp, ".//Anagrafica/Denominazione"),
            "nome": _find_text(cp, ".//Anagrafica/Nome"),
            "cognome": _find_text(cp, ".//Anagrafica/Cognome"),
            "regime_fiscale": _find_text(cp, ".//RegimeFiscale"),
        }

    def _parse_cliente(self, header: ET.Element | None) -> dict[str, Any]:
        """Parse CessionarioCommittente (customer) data."""
        if header is None:
            return {}

        cc = header.find(".//CessionarioCommittente")
        if cc is None:
            return {}

        return {
            "partita_iva": _find_text(cc, ".//IdFiscaleIVA/IdCodice"),
            "codice_fiscale": _find_text(cc, ".//DatiAnagrafici/CodiceFiscale"),
            "denominazione": _find_text(cc, ".//Anagrafica/Denominazione"),
            "nome": _find_text(cc, ".//Anagrafica/Nome"),
            "cognome": _find_text(cc, ".//Anagrafica/Cognome"),
        }

    def _parse_dati_generali(self, body: ET.Element) -> dict[str, Any]:
        """Parse DatiGeneraliDocumento."""
        dg = body.find(".//DatiGeneraliDocumento")
        if dg is None:
            return {
                "tipo_documento": "",
                "divisa": "EUR",
                "data_emissione": "",
                "numero_fattura": "",
                "importo_totale": 0.0,
            }

        importo_str = _find_text(dg, "ImportoTotaleDocumento", "0")
        return {
            "tipo_documento": _find_text(dg, "TipoDocumento"),
            "divisa": _find_text(dg, "Divisa", "EUR"),
            "data_emissione": _find_text(dg, "Data"),
            "numero_fattura": _find_text(dg, "Numero"),
            "importo_totale": float(importo_str) if importo_str else 0.0,
        }

    def _parse_linee(self, body: ET.Element) -> list[dict[str, Any]]:
        """Parse DettaglioLinee (line items)."""
        linee = []
        for linea in _find_all(body, ".//DettaglioLinee"):
            linee.append(
                {
                    "numero_linea": int(_find_text(linea, "NumeroLinea", "0")),
                    "descrizione": _find_text(linea, "Descrizione"),
                    "quantita": float(_find_text(linea, "Quantita", "0")),
                    "prezzo_unitario": float(_find_text(linea, "PrezzoUnitario", "0")),
                    "prezzo_totale": float(_find_text(linea, "PrezzoTotale", "0")),
                    "aliquota_iva": float(_find_text(linea, "AliquotaIVA", "0")),
                }
            )
        return linee

    def _parse_riepilogo(self, body: ET.Element) -> list[dict[str, Any]]:
        """Parse DatiRiepilogo (IVA summary)."""
        riepilogo = []
        for dr in _find_all(body, ".//DatiRiepilogo"):
            riepilogo.append(
                {
                    "aliquota": float(_find_text(dr, "AliquotaIVA", "0")),
                    "imponibile": float(_find_text(dr, "ImponibileImporto", "0")),
                    "imposta": float(_find_text(dr, "Imposta", "0")),
                    "esigibilita_iva": _find_text(dr, "EsigibilitaIVA"),
                }
            )
        return riepilogo

    def _parse_ritenuta(self, body: ET.Element) -> dict[str, Any] | None:
        """Parse DatiRitenuta (withholding tax) if present."""
        dr = body.find(".//DatiRitenuta")
        if dr is None:
            return None
        return {
            "tipo_ritenuta": _find_text(dr, "TipoRitenuta"),
            "importo_ritenuta": float(_find_text(dr, "ImportoRitenuta", "0")),
            "aliquota_ritenuta": float(_find_text(dr, "AliquotaRitenuta", "0")),
            "causale_pagamento": _find_text(dr, "CausalePagamento"),
        }


fattura_xml_parser = FatturaXmlParser()
