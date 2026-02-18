/**
 * Citation Sources Configuration
 *
 * Centralized configuration for Italian government and institutional source URLs
 * that should be rendered as source citation badges in AI responses.
 *
 * These domains correspond to RSS feed sources configured in the backend:
 * - Agenzia delle Entrate (tax authority)
 * - INPS (social security)
 * - INAIL (workplace insurance)
 * - Gazzetta Ufficiale (official gazette)
 * - Ministero del Lavoro (labor ministry)
 * - MEF/Finanze (economy/finance ministry)
 * - Normattiva (legislation database)
 * - Governo (government portal)
 *
 * @see /Users/micky/PycharmProjects/PratikoAi-BE/alembic/versions/20251204_add_expanded_rss_feeds.py
 */

/**
 * List of domain patterns for recognized Italian institutional sources.
 * Used to identify URLs that should render with SourceCitation component styling.
 *
 * IMPORTANT: This list should match ONLY the sources actively monitored by the backend:
 * - RSS feeds: alembic/versions/20251204_add_expanded_rss_feeds.py (16 feeds)
 * - Web scrapers: app/services/scrapers/ (AdER, Cassazione, Gazzetta)
 */
export const CITATION_DOMAINS = [
  // Tax & Finance (RSS + Scrapers)
  'agenziaentrate.gov.it', // 2 RSS feeds
  'agenziaentrateriscossione.gov.it', // AdER scraper
  'mef.gov.it', // 1 RSS feed
  'finanze.gov.it', // 1 RSS feed

  // Social Security & Insurance (RSS)
  'inps.it', // 5 RSS feeds
  'inail.it', // 2 RSS feeds

  // Official Publications (RSS + Scrapers)
  'gazzettaufficiale.it', // 4 RSS feeds + scraper

  // Government Portals (RSS)
  'lavoro.gov.it', // 1 RSS feed
  'governo.it', // Government portal

  // Legislation Database
  'normattiva.it', // Official legislation database

  // Jurisprudence (Scrapers)
  'cortedicassazione.it', // Cassazione scraper
] as const;

export type CitationDomain = (typeof CITATION_DOMAINS)[number];

/**
 * Checks if a given URL is from a recognized Italian institutional source.
 *
 * @param href - The URL to check
 * @returns true if the URL is from a known citation source, false otherwise
 *
 * @example
 * isCitationUrl('https://www.agenziaentrate.gov.it/circolare/15') // true
 * isCitationUrl('https://www.inail.it/news/123') // true
 * isCitationUrl('https://example.com') // false
 */
export function isCitationUrl(href: string | undefined): boolean {
  if (!href) return false;

  try {
    const url = new URL(href);
    const hostname = url.hostname.toLowerCase();

    return CITATION_DOMAINS.some(
      domain => hostname === domain || hostname.endsWith(`.${domain}`)
    );
  } catch {
    // Invalid URL - fallback to simple string matching for partial URLs
    const hrefLower = href.toLowerCase();
    return CITATION_DOMAINS.some(domain => hrefLower.includes(domain));
  }
}
