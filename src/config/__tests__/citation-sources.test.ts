/**
 * Citation Sources Configuration Tests
 * TDD approach - Tests written FIRST before implementation
 *
 * Test Coverage:
 * 1. isCitationUrl function for all supported domains
 * 2. Non-citation URLs return false
 * 3. Edge cases (invalid URLs, empty strings, undefined)
 * 4. Subdomain handling (www.domain.it, subdomain.domain.it)
 */

import { isCitationUrl, CITATION_DOMAINS } from '../citation-sources';

describe('Citation Sources Configuration', () => {
  describe('CITATION_DOMAINS constant', () => {
    it('should contain all expected Italian institutional domains (only monitored sources)', () => {
      // Tax & Finance (RSS + Scrapers)
      expect(CITATION_DOMAINS).toContain('agenziaentrate.gov.it');
      expect(CITATION_DOMAINS).toContain('agenziaentrateriscossione.gov.it');
      expect(CITATION_DOMAINS).toContain('mef.gov.it');
      expect(CITATION_DOMAINS).toContain('finanze.gov.it');
      // Social Security & Insurance (RSS)
      expect(CITATION_DOMAINS).toContain('inps.it');
      expect(CITATION_DOMAINS).toContain('inail.it');
      // Official Publications (RSS + Scrapers)
      expect(CITATION_DOMAINS).toContain('gazzettaufficiale.it');
      // Government Portals (RSS)
      expect(CITATION_DOMAINS).toContain('lavoro.gov.it');
      // Jurisprudence (Scrapers)
      expect(CITATION_DOMAINS).toContain('cortedicassazione.it');
    });

    it('should contain government and legislation domains', () => {
      // Government portals and legislation database
      expect(CITATION_DOMAINS).toContain('normattiva.it');
      expect(CITATION_DOMAINS).toContain('governo.it');
    });

    it('should have exactly 11 domains (monitored sources)', () => {
      expect(CITATION_DOMAINS.length).toBe(11);
    });
  });

  describe('isCitationUrl function', () => {
    describe('1. Agenzia delle Entrate URLs', () => {
      it('should return true for agenziaentrate.gov.it URLs', () => {
        expect(
          isCitationUrl(
            'https://www.agenziaentrate.gov.it/portale/documents/circolare-15-e-2024'
          )
        ).toBe(true);
      });

      it('should return true for agenziaentrate.gov.it with idrss parameter', () => {
        expect(
          isCitationUrl(
            'https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4'
          )
        ).toBe(true);
      });

      it('should return true for agenziaentrate.gov.it without www', () => {
        expect(
          isCitationUrl('https://agenziaentrate.gov.it/portale/normativa')
        ).toBe(true);
      });
    });

    describe('2. Agenzia delle Entrate-Riscossione (AdER) URLs', () => {
      it('should return true for agenziaentrateriscossione.gov.it URLs', () => {
        expect(
          isCitationUrl(
            'https://www.agenziaentrateriscossione.gov.it/it/il-gruppo/lagenzia-comunica/novita/Legge-di-Bilancio-2026-in-arrivo-la-Rottamazione-quinquies/'
          )
        ).toBe(true);
      });

      it('should return true for agenziaentrateriscossione.gov.it without www', () => {
        expect(
          isCitationUrl(
            'https://agenziaentrateriscossione.gov.it/it/definizione-agevolata'
          )
        ).toBe(true);
      });
    });

    describe('3. INAIL URLs', () => {
      it('should return true for www.inail.it URLs', () => {
        expect(
          isCitationUrl('https://www.inail.it/portale/it.rss.news.xml')
        ).toBe(true);
      });

      it('should return true for inail.it URLs without www', () => {
        expect(isCitationUrl('https://inail.it/portale/news/123')).toBe(true);
      });

      it('should return true for inail.it eventi feed', () => {
        expect(
          isCitationUrl('https://www.inail.it/portale/it.rss.eventi.xml')
        ).toBe(true);
      });
    });

    describe('3. INPS URLs', () => {
      it('should return true for www.inps.it URLs', () => {
        expect(isCitationUrl('https://www.inps.it/it/it.rss.news.xml')).toBe(
          true
        );
      });

      it('should return true for inps.it circolari feed', () => {
        expect(
          isCitationUrl('https://www.inps.it/it/it.rss.circolari.xml')
        ).toBe(true);
      });

      it('should return true for inps.it messaggi feed', () => {
        expect(
          isCitationUrl('https://www.inps.it/it/it.rss.messaggi.xml')
        ).toBe(true);
      });
    });

    describe('4. Gazzetta Ufficiale URLs', () => {
      it('should return true for gazzettaufficiale.it URLs', () => {
        expect(isCitationUrl('https://www.gazzettaufficiale.it/rss/SG')).toBe(
          true
        );
      });

      it('should return true for gazzettaufficiale.it Serie Generale', () => {
        expect(
          isCitationUrl('https://www.gazzettaufficiale.it/atto/serie_generale')
        ).toBe(true);
      });
    });

    describe('5. Corte di Cassazione URLs', () => {
      it('should return true for cortedicassazione.it URLs', () => {
        expect(
          isCitationUrl(
            'https://www.cortedicassazione.it/it/civile_dettaglio.page?contentId=STC12345'
          )
        ).toBe(true);
      });

      it('should return true for cortedicassazione.it without www', () => {
        expect(
          isCitationUrl(
            'https://cortedicassazione.it/it/giurisprudenza_civile.page'
          )
        ).toBe(true);
      });

      it('should return true for cortedicassazione.it tributaria section', () => {
        expect(
          isCitationUrl(
            'https://www.cortedicassazione.it/it/tributaria_dettaglio.page?contentId=STC67890'
          )
        ).toBe(true);
      });
    });

    describe('6. MEF (Ministero Economia e Finanze) URLs', () => {
      it('should return true for mef.gov.it URLs', () => {
        expect(isCitationUrl('https://www.mef.gov.it/rss/rss.asp?t=5')).toBe(
          true
        );
      });

      it('should return true for finanze.gov.it URLs', () => {
        expect(isCitationUrl('https://www.finanze.gov.it/it/rss.xml')).toBe(
          true
        );
      });
    });

    describe('7. Ministero del Lavoro URLs', () => {
      it('should return true for lavoro.gov.it URLs', () => {
        expect(
          isCitationUrl(
            'https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS'
          )
        ).toBe(true);
      });

      it('should return true for lavoro.gov.it without www', () => {
        expect(isCitationUrl('https://lavoro.gov.it/notizie/')).toBe(true);
      });
    });

    describe('8. Normattiva and Governo URLs', () => {
      it('should return true for normattiva.it (legislation database)', () => {
        expect(isCitationUrl('https://www.normattiva.it/uri-res/N2Ls')).toBe(
          true
        );
        expect(isCitationUrl('https://normattiva.it/atto/originario')).toBe(
          true
        );
      });

      it('should return true for governo.it (government portal)', () => {
        expect(isCitationUrl('https://www.governo.it/it/articolo')).toBe(true);
        expect(isCitationUrl('https://governo.it/decreto')).toBe(true);
      });
    });

    describe('9. Non-citation URLs (should return false)', () => {
      it('should return false for example.com', () => {
        expect(isCitationUrl('https://example.com')).toBe(false);
      });

      it('should return false for google.com', () => {
        expect(isCitationUrl('https://www.google.com/search?q=test')).toBe(
          false
        );
      });

      it('should return false for other .it domains', () => {
        expect(isCitationUrl('https://www.corriere.it/economia')).toBe(false);
      });

      it('should return false for similar but different domains', () => {
        expect(isCitationUrl('https://fake-agenziaentrate.com')).toBe(false);
        expect(isCitationUrl('https://inail-fake.com')).toBe(false);
      });
    });

    describe('10. Edge cases', () => {
      it('should return false for undefined', () => {
        expect(isCitationUrl(undefined)).toBe(false);
      });

      it('should return false for empty string', () => {
        expect(isCitationUrl('')).toBe(false);
      });

      it('should return false for invalid URL format', () => {
        expect(isCitationUrl('not-a-url')).toBe(false);
      });

      it('should handle URLs with different protocols', () => {
        expect(isCitationUrl('http://www.inail.it/news')).toBe(true);
        expect(isCitationUrl('https://www.inail.it/news')).toBe(true);
      });

      it('should handle URLs with query parameters', () => {
        expect(
          isCitationUrl('https://www.inps.it/it?id=123&type=circolare')
        ).toBe(true);
      });

      it('should handle URLs with fragments', () => {
        expect(isCitationUrl('https://www.inps.it/articolo#section-1')).toBe(
          true
        );
      });

      it('should handle URLs with ports', () => {
        expect(isCitationUrl('https://www.inail.it:443/portale')).toBe(true);
      });

      it('should be case insensitive for domain matching', () => {
        expect(isCitationUrl('https://www.INAIL.IT/portale')).toBe(true);
        expect(isCitationUrl('https://WWW.CORTEDICASSAZIONE.IT/sentenza')).toBe(
          true
        );
      });
    });

    describe('11. Subdomain handling', () => {
      it('should match www subdomain', () => {
        expect(isCitationUrl('https://www.inail.it/news')).toBe(true);
        expect(isCitationUrl('https://www.inps.it/circolari')).toBe(true);
      });

      it('should match other subdomains', () => {
        expect(isCitationUrl('https://portale.inail.it/news')).toBe(true);
        expect(isCitationUrl('https://servizi.inps.it/api')).toBe(true);
      });

      it('should match naked domain (no subdomain)', () => {
        expect(isCitationUrl('https://inail.it/news')).toBe(true);
        expect(isCitationUrl('https://cortedicassazione.it/sentenza')).toBe(
          true
        );
      });
    });
  });
});
