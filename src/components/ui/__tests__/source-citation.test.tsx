/**
 * SourceCitation Component Tests
 * TDD approach - Tests written FIRST before implementation
 *
 * Test Coverage:
 * 1. Rendering citation text
 * 2. Rendering as anchor with href
 * 3. Rendering as button with onClick
 * 4. Size variants (xs, sm, md)
 * 5. Click handler functionality
 * 6. Accessibility (aria-label)
 * 7. Keyboard accessibility
 * 8. Long text handling
 * 9. Italian labels in aria
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { SourceCitation } from '../source-citation';

describe('SourceCitation Component', () => {
  describe('1. Rendering Citation Text', () => {
    it('should render the citation text correctly', () => {
      render(<SourceCitation citation="Art. 119 D.L. 34/2020" />);

      const citation = screen.getByText('Art. 119 D.L. 34/2020');
      expect(citation).toBeInTheDocument();
    });

    it('should render with default styling', () => {
      render(<SourceCitation citation="Circolare 15/E/2024" />);

      const citation = screen.getByText('Circolare 15/E/2024');
      expect(citation).toHaveClass(
        'border',
        'rounded-md',
        'text-xs',
        'font-medium'
      );
    });
  });

  describe('2. Rendering as Anchor with href', () => {
    it('should render as anchor tag when href is provided', () => {
      render(
        <SourceCitation
          citation="Circolare 15/E/2024"
          href="https://example.com/circolare-15e-2024"
        />
      );

      const link = screen.getByRole('link', { name: /Circolare 15\/E\/2024/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute(
        'href',
        'https://example.com/circolare-15e-2024'
      );
    });

    it('should open link in new tab with proper security attributes', () => {
      render(
        <SourceCitation
          citation="Art. 16-bis TUIR"
          href="https://example.com/art-16bis"
        />
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  describe('3. Rendering as Button with onClick', () => {
    it('should render as button when onClick is provided without href', () => {
      const handleClick = jest.fn();
      render(
        <SourceCitation citation="D.Lgs. 241/1997" onClick={handleClick} />
      );

      const button = screen.getByRole('button', {
        name: /D\.Lgs\. 241\/1997/i,
      });
      expect(button).toBeInTheDocument();
    });

    it('should prefer href over onClick when both are provided', () => {
      const handleClick = jest.fn();
      render(
        <SourceCitation
          citation="L. 234/2021"
          href="https://example.com/legge-234"
          onClick={handleClick}
        />
      );

      // Should render as link, not button
      const link = screen.getByRole('link');
      expect(link).toBeInTheDocument();
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('4. Size Variants (xs, sm, md)', () => {
    it('should apply extra-small size classes', () => {
      render(<SourceCitation citation="Test" size="xs" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('px-1.5', 'py-0.5', 'text-[10px]');
    });

    it('should apply small size classes (default)', () => {
      render(<SourceCitation citation="Test" size="sm" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('px-2', 'py-0.5', 'text-xs');
    });

    it('should apply medium size classes', () => {
      render(<SourceCitation citation="Test" size="md" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('px-2.5', 'py-1', 'text-sm');
    });

    it('should default to "sm" size when not specified', () => {
      render(<SourceCitation citation="Test" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('px-2', 'py-0.5', 'text-xs');
    });
  });

  describe('5. Click Handler Functionality', () => {
    it('should call onClick handler when button is clicked', () => {
      const handleClick = jest.fn();
      render(
        <SourceCitation
          citation="Risoluzione 42/E/2023"
          onClick={handleClick}
        />
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not call onClick when href is provided', () => {
      const handleClick = jest.fn();
      render(
        <SourceCitation
          citation="Test"
          href="https://example.com"
          onClick={handleClick}
        />
      );

      const link = screen.getByRole('link');
      fireEvent.click(link);

      // onClick should not be called when href is present
      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe('6. Accessibility (aria-label)', () => {
    it('should use custom aria-label when provided', () => {
      render(
        <SourceCitation
          citation="Art. 119"
          ariaLabel="Vai all'articolo 119 del decreto legge 34/2020"
          href="https://example.com"
        />
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'aria-label',
        "Vai all'articolo 119 del decreto legge 34/2020"
      );
    });

    it('should use default Italian aria-label for links without custom label', () => {
      render(
        <SourceCitation
          citation="Circolare 15/E/2024"
          href="https://example.com"
        />
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'aria-label',
        'Fonte normativa: Circolare 15/E/2024'
      );
    });

    it('should use default Italian aria-label for buttons without custom label', () => {
      render(<SourceCitation citation="D.Lgs. 241/1997" onClick={jest.fn()} />);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute(
        'aria-label',
        'Fonte normativa: D.Lgs. 241/1997'
      );
    });
  });

  describe('7. Keyboard Accessibility', () => {
    it('should be focusable with keyboard (Tab)', async () => {
      const user = userEvent.setup();
      render(<SourceCitation citation="Art. 119" href="https://example.com" />);

      const link = screen.getByRole('link');

      await user.tab();
      expect(link).toHaveFocus();
    });

    it('should trigger onClick with Enter key on button', async () => {
      const user = userEvent.setup();
      const handleClick = jest.fn();
      render(<SourceCitation citation="Test" onClick={handleClick} />);

      const button = screen.getByRole('button');
      await user.tab();
      await user.keyboard('{Enter}');

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should trigger onClick with Space key on button', async () => {
      const user = userEvent.setup();
      const handleClick = jest.fn();
      render(<SourceCitation citation="Test" onClick={handleClick} />);

      const button = screen.getByRole('button');
      await user.tab();
      await user.keyboard(' ');

      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('8. Long Text Handling', () => {
    it('should truncate text longer than 60 characters with ellipsis', () => {
      const longCitation =
        'Circolare Agenzia delle Entrate numero 15/E del 24 giugno 2024 riguardante le detrazioni';
      // 60 chars max, so text should be truncated at 59 chars + "…"
      const expectedTruncated =
        'Circolare Agenzia delle Entrate numero 15/E del 24 giugno 2…';
      render(<SourceCitation citation={longCitation} />);

      // Should render truncated text
      const citation = screen.getByText(expectedTruncated);
      expect(citation).toBeInTheDocument();

      // Should preserve full text in title for hover
      expect(citation).toHaveAttribute('title', longCitation);
    });

    it('should not truncate text 60 characters or less', () => {
      const shortCitation = 'Circolare 15/E del 24 giugno 2024'; // 33 chars
      render(<SourceCitation citation={shortCitation} />);

      const citation = screen.getByText(shortCitation);
      expect(citation).toBeInTheDocument();
      expect(citation.textContent).toBe(shortCitation); // No truncation
    });

    it('should show full text on hover via title attribute', () => {
      const longCitation = 'Circolare 15/E del 24 giugno 2024';
      render(<SourceCitation citation={longCitation} />);

      const citation = screen.getByText(longCitation);
      expect(citation).toHaveAttribute('title', longCitation);
    });
  });

  describe('9. Italian Labels and Localization', () => {
    it('should use Italian for all default labels', () => {
      render(<SourceCitation citation="Art. 119" href="https://example.com" />);

      const link = screen.getByRole('link');
      const ariaLabel = link.getAttribute('aria-label');
      expect(ariaLabel).toContain('Fonte normativa:');
    });

    it('should allow custom Italian aria labels', () => {
      render(
        <SourceCitation
          citation="L. 234/2021"
          ariaLabel="Leggi la normativa completa sulla legge 234 del 2021"
          href="https://example.com"
        />
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'aria-label',
        'Leggi la normativa completa sulla legge 234 del 2021'
      );
    });
  });

  describe('10. PratikoAI Color Palette', () => {
    it('should use blu-petrolio color for text', () => {
      render(<SourceCitation citation="Test" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('text-[#2A5D67]');
    });

    it('should use grigio-tortora for border', () => {
      render(<SourceCitation citation="Test" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('border-[#C4BDB4]');
    });

    it('should apply hover state with avorio background', () => {
      render(<SourceCitation citation="Test" href="https://example.com" />);

      const link = screen.getByRole('link');
      expect(link).toHaveClass('hover:bg-[#F8F5F1]');
    });
  });

  describe('11. Custom className', () => {
    it('should merge custom className with default classes', () => {
      render(<SourceCitation citation="Test" className="ml-4 custom-class" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('ml-4', 'custom-class');
      expect(citation).toHaveClass('border', 'rounded-md'); // Still has default classes
    });
  });

  describe('12. Interactive State', () => {
    it('should apply cursor-pointer when interactive', () => {
      render(<SourceCitation citation="Test" onClick={jest.fn()} />);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('cursor-pointer');
    });

    it('should apply cursor-default when not interactive', () => {
      render(<SourceCitation citation="Test" />);

      const citation = screen.getByText('Test');
      expect(citation).toHaveClass('cursor-default');
    });
  });
});
