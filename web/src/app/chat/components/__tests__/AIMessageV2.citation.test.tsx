/**
 * AIMessageV2 Citation Rendering Tests
 * TDD approach - Tests written FIRST before implementation
 *
 * Test Coverage:
 * 1. Citation links from all RSS sources render as SourceCitation
 * 2. Non-citation links render as regular <a> tags
 * 3. Multiple citations in single response
 * 4. Mixed citation and non-citation links
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import type { Message } from '../../types/chat';

// Mock react-markdown (ESM module)
jest.mock('react-markdown', () => {
  return function MockReactMarkdown({
    children,
    components,
  }: {
    children: string;
    components?: {
      a?: React.ComponentType<{ href?: string; children?: React.ReactNode }>;
    };
  }) {
    // Simple markdown link parser: [text](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;
    let key = 0;

    while ((match = linkRegex.exec(children)) !== null) {
      // Add text before the link
      if (match.index > lastIndex) {
        parts.push(children.slice(lastIndex, match.index));
      }

      const [, linkText, linkUrl] = match;
      const LinkComponent = components?.a;

      if (LinkComponent) {
        parts.push(
          <LinkComponent key={key++} href={linkUrl}>
            {linkText}
          </LinkComponent>
        );
      } else {
        parts.push(
          <a key={key++} href={linkUrl}>
            {linkText}
          </a>
        );
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < children.length) {
      parts.push(children.slice(lastIndex));
    }

    return <div data-testid="markdown-content">{parts}</div>;
  };
});

// Mock the useExpertStatus hook
jest.mock('@/hooks/useExpertStatus', () => ({
  useExpertStatus: () => ({ isExpert: false, isLoading: false }),
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

// Import AIMessageV2 after mocks are set up
import { AIMessageV2 } from '../AIMessageV2';

// Helper to create a message with markdown content
const createMessage = (content: string, id?: string): Message => ({
  id: id || 'test-msg-1',
  type: 'ai',
  content,
  timestamp: new Date().toISOString(),
});

describe('AIMessageV2 Citation Rendering', () => {
  describe('1. Agenzia delle Entrate Citations (Regression)', () => {
    it('should render Agenzia Entrate link as SourceCitation', () => {
      const message = createMessage(
        'Secondo la [Circolare 15/E](https://www.agenziaentrate.gov.it/portale/documents/circolare-15-e-2024), si applica la detrazione.'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      // Should render as SourceCitation (link with aria-label containing "Fonte normativa")
      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
      expect(citation).toHaveAttribute(
        'href',
        'https://www.agenziaentrate.gov.it/portale/documents/circolare-15-e-2024'
      );
      expect(citation).toHaveTextContent('Circolare 15/E');
    });

    it('should render Agenzia Entrate RSS feed link as SourceCitation', () => {
      const message = createMessage(
        'Fonte: [Normativa AdE](https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
      expect(citation).toHaveTextContent('Normativa AdE');
    });
  });

  describe('2. INAIL Citations (NEW - Previously broken)', () => {
    it('should render INAIL news link as SourceCitation', () => {
      const message = createMessage(
        'Come indicato nella [Circolare INAIL 25/2024](https://www.inail.it/portale/it/notizie/circolare-25-2024), i contributi sono aggiornati.'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
      expect(citation).toHaveAttribute(
        'href',
        'https://www.inail.it/portale/it/notizie/circolare-25-2024'
      );
      expect(citation).toHaveTextContent('Circolare INAIL 25/2024');
    });

    it('should render INAIL RSS feed link as SourceCitation', () => {
      const message = createMessage(
        'Aggiornamento: [INAIL News](https://www.inail.it/portale/it.rss.news.xml)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
    });
  });

  describe('3. INPS Citations (Regression)', () => {
    it('should render INPS circolare link as SourceCitation', () => {
      const message = createMessage(
        'La [Circolare INPS 82/2024](https://www.inps.it/it/it.rss.circolari/circolare-82-2024) chiarisce le procedure.'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
      expect(citation).toHaveTextContent('Circolare INPS 82/2024');
    });

    it('should render INPS messaggio link as SourceCitation', () => {
      const message = createMessage(
        'Vedi [Messaggio INPS 1234](https://www.inps.it/it/it.rss.messaggi/messaggio-1234)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
    });
  });

  describe('4. Gazzetta Ufficiale Citations (Regression)', () => {
    it('should render Gazzetta Ufficiale link as SourceCitation', () => {
      const message = createMessage(
        'Pubblicato in [GU Serie Generale n. 250](https://www.gazzettaufficiale.it/atto/serie_generale/250)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
      expect(citation).toHaveTextContent('GU Serie Generale n. 250');
    });
  });

  describe('5. Normattiva Citations (Regression)', () => {
    it('should render Normattiva link as SourceCitation', () => {
      const message = createMessage(
        "Ai sensi dell'[Art. 119 DL 34/2020](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:2020-05-19;34)"
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
      expect(citation).toHaveTextContent('Art. 119 DL 34/2020');
    });
  });

  describe('6. MEF Citations (Regression)', () => {
    it('should render MEF link as SourceCitation', () => {
      const message = createMessage(
        'Il [Comunicato MEF](https://www.mef.gov.it/rss/rss.asp?t=5) indica le nuove aliquote.'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
    });

    it('should render Finanze link as SourceCitation', () => {
      const message = createMessage(
        'Fonte: [Dipartimento Finanze](https://www.finanze.gov.it/it/rss.xml)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
    });
  });

  describe('7. Ministero del Lavoro Citations (NEW)', () => {
    it('should render Ministero Lavoro link as SourceCitation', () => {
      const message = createMessage(
        'Come da [Comunicato Min. Lavoro](https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
    });
  });

  describe('8. Governo Citations (NEW)', () => {
    it('should render Governo.it link as SourceCitation', () => {
      const message = createMessage(
        'Il [DPCM 15/2024](https://www.governo.it/it/articolo/dpcm-15-2024) stabilisce le regole.'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citation = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(citation).toBeInTheDocument();
    });
  });

  describe('9. Non-Citation Links (Should render as regular links)', () => {
    it('should render external links as regular anchors', () => {
      const message = createMessage(
        'Per maggiori informazioni visita [Wikipedia](https://www.wikipedia.org/fiscal)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      // Should NOT have aria-label with "Fonte normativa"
      const link = screen.getByRole('link', { name: 'Wikipedia' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://www.wikipedia.org/fiscal');
      expect(link).not.toHaveAttribute(
        'aria-label',
        expect.stringContaining('Fonte normativa')
      );
      // Regular links have underline class
      expect(link).toHaveClass('underline');
    });

    it('should render other .it domain links as regular anchors', () => {
      const message = createMessage(
        "Leggi l'articolo su [Il Sole 24 Ore](https://www.ilsole24ore.com/art/fisco)"
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const link = screen.getByRole('link', { name: 'Il Sole 24 Ore' });
      expect(link).toBeInTheDocument();
      expect(link).not.toHaveAttribute(
        'aria-label',
        expect.stringContaining('Fonte normativa')
      );
      expect(link).toHaveClass('underline');
    });
  });

  describe('10. Multiple Citations in Single Response', () => {
    it('should render multiple citations from different sources', () => {
      const message = createMessage(
        'Secondo la [Circolare AdE 15/E](https://www.agenziaentrate.gov.it/circolare-15) e la ' +
          '[Circolare INAIL 25](https://www.inail.it/circolare-25), nonché il ' +
          '[Messaggio INPS 100](https://www.inps.it/messaggio-100), si applicano le seguenti regole.'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const citations = screen.getAllByRole('link', {
        name: /Fonte normativa/i,
      });
      expect(citations).toHaveLength(3);

      // Verify each citation
      expect(citations[0]).toHaveTextContent('Circolare AdE 15/E');
      expect(citations[1]).toHaveTextContent('Circolare INAIL 25');
      expect(citations[2]).toHaveTextContent('Messaggio INPS 100');
    });

    it('should correctly mix citations and regular links', () => {
      const message = createMessage(
        'La [Circolare INAIL](https://www.inail.it/circolare) è disponibile. ' +
          'Per approfondimenti vedi [questo articolo](https://www.example.com/article).'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      // Citation link
      const citationLink = screen.getByRole('link', {
        name: /Fonte normativa/i,
      });
      expect(citationLink).toHaveTextContent('Circolare INAIL');

      // Regular link
      const regularLink = screen.getByRole('link', { name: 'questo articolo' });
      expect(regularLink).toHaveClass('underline');
      expect(regularLink).not.toHaveAttribute(
        'aria-label',
        expect.stringContaining('Fonte normativa')
      );
    });
  });

  describe('11. Citation Link Attributes', () => {
    it('should open citation links in new tab', () => {
      const message = createMessage(
        '[Circolare INAIL](https://www.inail.it/circolare)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('should have correct accessibility attributes', () => {
      const message = createMessage(
        '[Circolare 15/E](https://www.agenziaentrate.gov.it/circolare-15)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const link = screen.getByRole('link');
      // SourceCitation uses aria-label with "Fonte normativa: {citation}"
      expect(link).toHaveAttribute(
        'aria-label',
        expect.stringContaining('Circolare 15/E')
      );
    });
  });

  describe('12. Edge Cases', () => {
    it('should handle message with no links', () => {
      const message = createMessage(
        'La detrazione fiscale si applica secondo le normative vigenti.'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      expect(screen.queryByRole('link')).not.toBeInTheDocument();
    });

    it('should handle empty message content', () => {
      const message = createMessage('');

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const container = screen.getByTestId('ai-message-v2');
      expect(container).toBeInTheDocument();
    });

    it('should handle links with special characters in URL', () => {
      const message = createMessage(
        '[Circolare](https://www.inail.it/portale?q=test&id=123#section)'
      );

      render(<AIMessageV2 message={message} isStreaming={false} />);

      const link = screen.getByRole('link', { name: /Fonte normativa/i });
      expect(link).toHaveAttribute(
        'href',
        'https://www.inail.it/portale?q=test&id=123#section'
      );
    });
  });
});
