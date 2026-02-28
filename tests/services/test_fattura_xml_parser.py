"""DEV-411: Tests for Fattura Elettronica XML Parser.

Tests: valid FatturaPA XML, multi-line items, split-payment,
ritenuta d'acconto, malformed XML, missing fields.
"""

import pytest

from app.services.document_parsers.fattura_xml_parser import FatturaXmlParser

SAMPLE_FATTURA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
                       versione="FPR12">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>01234567890</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Fornitore SRL</Denominazione>
        </Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <CodiceFiscale>RSSMRA80A01H501Z</CodiceFiscale>
        <Anagrafica>
          <Nome>Mario</Nome>
          <Cognome>Rossi</Cognome>
        </Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Divisa>EUR</Divisa>
        <Data>2026-01-15</Data>
        <Numero>FT-2026/001</Numero>
        <ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Consulenza fiscale</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>1000.00</PrezzoUnitario>
        <PrezzoTotale>1000.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>1000.00</ImponibileImporto>
        <Imposta>220.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""

SAMPLE_MULTI_LINE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
                       versione="FPR12">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>09876543210</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>Azienda ABC</Denominazione></Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <CodiceFiscale>BNCGPP85B02F205X</CodiceFiscale>
        <Anagrafica><Denominazione>Studio Bianchi</Denominazione></Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Divisa>EUR</Divisa>
        <Data>2026-02-01</Data>
        <Numero>001/2026</Numero>
        <ImportoTotaleDocumento>366.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Servizio A</Descrizione>
        <Quantita>2.00</Quantita>
        <PrezzoUnitario>100.00</PrezzoUnitario>
        <PrezzoTotale>200.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DettaglioLinee>
        <NumeroLinea>2</NumeroLinea>
        <Descrizione>Servizio B</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>100.00</PrezzoUnitario>
        <PrezzoTotale>100.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>300.00</ImponibileImporto>
        <Imposta>66.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


@pytest.fixture
def parser():
    return FatturaXmlParser()


class TestFatturaXmlParser:
    def test_parse_valid_fattura(self, parser):
        result = parser.parse(SAMPLE_FATTURA_XML)
        assert result["numero_fattura"] == "FT-2026/001"
        assert result["data_emissione"] == "2026-01-15"
        assert result["tipo_documento"] == "TD01"
        assert result["divisa"] == "EUR"
        assert result["importo_totale"] == 1220.0

    def test_parse_fornitore(self, parser):
        result = parser.parse(SAMPLE_FATTURA_XML)
        assert result["fornitore"]["partita_iva"] == "01234567890"
        assert result["fornitore"]["denominazione"] == "Fornitore SRL"

    def test_parse_cliente(self, parser):
        result = parser.parse(SAMPLE_FATTURA_XML)
        assert result["cliente"]["codice_fiscale"] == "RSSMRA80A01H501Z"

    def test_parse_line_items(self, parser):
        result = parser.parse(SAMPLE_FATTURA_XML)
        assert len(result["linee"]) == 1
        assert result["linee"][0]["descrizione"] == "Consulenza fiscale"
        assert result["linee"][0]["prezzo_totale"] == 1000.0

    def test_parse_riepilogo_iva(self, parser):
        result = parser.parse(SAMPLE_FATTURA_XML)
        assert len(result["riepilogo_iva"]) == 1
        assert result["riepilogo_iva"][0]["aliquota"] == 22.0
        assert result["riepilogo_iva"][0]["imponibile"] == 1000.0
        assert result["riepilogo_iva"][0]["imposta"] == 220.0

    def test_parse_multi_line_items(self, parser):
        result = parser.parse(SAMPLE_MULTI_LINE_XML)
        assert len(result["linee"]) == 2
        assert result["linee"][0]["descrizione"] == "Servizio A"
        assert result["linee"][1]["descrizione"] == "Servizio B"
        assert result["importo_totale"] == 366.0

    def test_malformed_xml_raises(self, parser):
        with pytest.raises(ValueError, match="XML"):
            parser.parse("<not-valid-xml")

    def test_empty_xml_raises(self, parser):
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("")

    def test_missing_body_raises(self, parser):
        xml = """<?xml version="1.0"?>
        <p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
          <FatturaElettronicaHeader></FatturaElettronicaHeader>
        </p:FatturaElettronica>"""
        with pytest.raises(ValueError, match="Body"):
            parser.parse(xml)

    def test_whitespace_only_raises(self, parser):
        with pytest.raises(ValueError, match="vuoto"):
            parser.parse("   \n  ")


FATTURA_WITH_RITENUTA = """\
<FatturaElettronica>
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <Anagrafica>
          <Nome>Mario</Nome>
          <Cognome>Rossi</Cognome>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <Anagrafica>
          <Nome>Laura</Nome>
          <Cognome>Bianchi</Cognome>
        </Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD06</TipoDocumento>
        <Data>2024-06-01</Data>
        <Numero>2024/099</Numero>
        <ImportoTotaleDocumento>500.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
      <DatiRitenuta>
        <TipoRitenuta>RT01</TipoRitenuta>
        <ImportoRitenuta>100.00</ImportoRitenuta>
        <AliquotaRitenuta>20.00</AliquotaRitenuta>
        <CausalePagamento>A</CausalePagamento>
      </DatiRitenuta>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Prestazione professionale</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>500.00</PrezzoUnitario>
        <PrezzoTotale>500.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>500.00</ImponibileImporto>
        <Imposta>110.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</FatturaElettronica>"""


class TestRitenuta:
    """Tests for fattura with ritenuta d'acconto."""

    def test_ritenuta_present(self, parser):
        result = parser.parse(FATTURA_WITH_RITENUTA)
        assert "ritenuta_acconto" in result

    def test_ritenuta_fields(self, parser):
        result = parser.parse(FATTURA_WITH_RITENUTA)
        rit = result["ritenuta_acconto"]
        assert rit["tipo_ritenuta"] == "RT01"
        assert rit["importo_ritenuta"] == 100.0
        assert rit["aliquota_ritenuta"] == 20.0
        assert rit["causale_pagamento"] == "A"

    def test_nome_cognome_fornitore(self, parser):
        result = parser.parse(FATTURA_WITH_RITENUTA)
        assert result["fornitore"]["nome"] == "Mario"
        assert result["fornitore"]["cognome"] == "Rossi"

    def test_nome_cognome_cliente(self, parser):
        result = parser.parse(FATTURA_WITH_RITENUTA)
        assert result["cliente"]["nome"] == "Laura"
        assert result["cliente"]["cognome"] == "Bianchi"


class TestHelperFunctions:
    """Tests for _find_text and _find_all helpers."""

    def test_find_text_none_element(self):
        from app.services.document_parsers.fattura_xml_parser import _find_text

        assert _find_text(None, "Foo") == ""

    def test_find_text_custom_default(self):
        from app.services.document_parsers.fattura_xml_parser import _find_text

        assert _find_text(None, "Foo", "bar") == "bar"

    def test_find_text_strips_whitespace(self):
        import xml.etree.ElementTree as ET

        from app.services.document_parsers.fattura_xml_parser import _find_text

        root = ET.fromstring("<Root><A>  hello  </A></Root>")
        assert _find_text(root, "A") == "hello"

    def test_find_all_none_element(self):
        from app.services.document_parsers.fattura_xml_parser import _find_all

        assert _find_all(None, "Foo") == []


class TestNoHeaderEdgeCases:
    """Tests for fattura without header or missing sections."""

    def test_missing_header_gives_empty_dicts(self, parser):
        xml = """\
<FatturaElettronica>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Numero>1</Numero>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi/>
  </FatturaElettronicaBody>
</FatturaElettronica>"""
        result = parser.parse(xml)
        assert result["fornitore"] == {}
        assert result["cliente"] == {}

    def test_missing_dati_generali_defaults(self, parser):
        xml = """\
<FatturaElettronica>
  <FatturaElettronicaBody>
    <DatiBeniServizi/>
  </FatturaElettronicaBody>
</FatturaElettronica>"""
        result = parser.parse(xml)
        assert result["tipo_documento"] == ""
        assert result["divisa"] == "EUR"
        assert result["importo_totale"] == 0.0

    def test_no_ritenuta_in_simple_fattura(self, parser):
        result = parser.parse(SAMPLE_FATTURA_XML)
        assert "ritenuta_acconto" not in result

    def test_header_without_cedente(self, parser):
        xml = """\
<FatturaElettronica>
  <FatturaElettronicaHeader>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <Anagrafica><Denominazione>Test</Denominazione></Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Numero>1</Numero>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi/>
  </FatturaElettronicaBody>
</FatturaElettronica>"""
        result = parser.parse(xml)
        assert result["fornitore"] == {}
        assert result["cliente"]["denominazione"] == "Test"

    def test_header_without_cessionario(self, parser):
        xml = """\
<FatturaElettronica>
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <Anagrafica><Denominazione>Fornitore</Denominazione></Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Numero>1</Numero>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi/>
  </FatturaElettronicaBody>
</FatturaElettronica>"""
        result = parser.parse(xml)
        assert result["fornitore"]["denominazione"] == "Fornitore"
        assert result["cliente"] == {}


class TestSingleton:
    """Tests for singleton instance."""

    def test_singleton_exists(self):
        from app.services.document_parsers.fattura_xml_parser import fattura_xml_parser

        assert fattura_xml_parser is not None

    def test_singleton_is_parser(self):
        from app.services.document_parsers.fattura_xml_parser import fattura_xml_parser

        assert isinstance(fattura_xml_parser, FatturaXmlParser)
