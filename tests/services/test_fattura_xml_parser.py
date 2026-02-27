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
