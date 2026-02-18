/**
 * SourceCitation Component
 *
 * A specialized component for displaying source citations in PratikoAI.
 * Designed for legal/fiscal document references with Italian localization.
 *
 * Features:
 * - PratikoAI color palette (blu-petrolio, grigio-tortora, avorio)
 * - Size variants (xs, sm, md)
 * - Interactive states (link or button)
 * - Accessibility (ARIA labels, keyboard navigation)
 * - Italian language support
 *
 * @example
 * ```tsx
 * // As a static citation
 * <SourceCitation citation="Circolare 15/E/2024" />
 *
 * // As a clickable link
 * <SourceCitation
 *   citation="Art. 119 D.L. 34/2020"
 *   href="https://example.com/art-119"
 * />
 *
 * // As a button with click handler
 * <SourceCitation
 *   citation="D.Lgs. 241/1997"
 *   onClick={() => showDocument('dlgs-241-1997')}
 * />
 * ```
 */

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

/**
 * Maximum character length for citation text display.
 * Longer text will be truncated with "…" suffix.
 */
const MAX_CITATION_LENGTH = 60;

/**
 * Truncates citation text to a maximum length with ellipsis.
 * Preserves full text for title/aria attributes.
 */
function truncateCitation(
  text: string,
  maxLength: number = MAX_CITATION_LENGTH
): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 1).trim() + '…';
}

/**
 * Size variants for the citation component
 * - xs: Extra small (10px font, minimal padding)
 * - sm: Small (12px font, default)
 * - md: Medium (14px font, more padding)
 */
const sourceCitationVariants = cva(
  [
    // Base styles - PratikoAI palette
    'inline-flex items-center',
    'border border-[#C4BDB4]', // grigio-tortora
    'text-[#2A5D67]', // blu-petrolio
    'bg-transparent',
    'rounded-md',
    'font-medium',
    'transition-colors duration-200',
    'focus:outline-none focus:ring-2 focus:ring-[#2A5D67] focus:ring-offset-2',
  ],
  {
    variants: {
      size: {
        xs: 'px-1.5 py-0.5 text-[10px]',
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2.5 py-1 text-sm',
      },
      interactive: {
        true: [
          'cursor-pointer',
          'hover:bg-[#F8F5F1]', // avorio
          'hover:border-[#2A5D67]', // blu-petrolio
          'active:bg-[#C4BDB4]/20',
        ],
        false: 'cursor-default',
      },
    },
    defaultVariants: {
      size: 'sm',
      interactive: false,
    },
  }
);

export interface SourceCitationProps
  extends Omit<React.HTMLAttributes<HTMLElement>, 'onClick'>,
    VariantProps<typeof sourceCitationVariants> {
  /**
   * The citation text to display (e.g., "Circolare 15/E/2024")
   */
  citation: string;

  /**
   * Optional URL for the source document
   * When provided, renders as an anchor tag (<a>)
   */
  href?: string;

  /**
   * Optional click handler for non-link citations
   * When provided without href, renders as a button
   */
  onClick?: () => void;

  /**
   * Size variant of the citation
   * @default "sm"
   */
  size?: 'xs' | 'sm' | 'md';

  /**
   * Custom CSS classes to merge with default styles
   */
  className?: string;

  /**
   * Custom ARIA label for accessibility
   * If not provided, defaults to "Fonte normativa: {citation}"
   */
  ariaLabel?: string;

  /**
   * Whether the citation is interactive (clickable)
   * Auto-determined based on href/onClick presence
   */
  interactive?: boolean;
}

/**
 * SourceCitation Component
 *
 * Displays legal/fiscal source citations with proper styling and accessibility.
 * Can be static, a link, or a button depending on props.
 */
export function SourceCitation({
  citation,
  href,
  onClick,
  size = 'sm',
  className,
  ariaLabel,
  interactive: interactiveProp,
  ...props
}: SourceCitationProps) {
  // Determine if component is interactive
  const isInteractive = interactiveProp ?? (!!href || !!onClick);

  // Truncate citation text for display, keep full text for title/aria
  const displayText = truncateCitation(citation);

  // Generate default Italian aria-label if not provided
  const defaultAriaLabel = `Fonte normativa: ${citation}`;
  const effectiveAriaLabel = ariaLabel || defaultAriaLabel;

  // Common props for all variants
  const commonProps = {
    className: cn(
      sourceCitationVariants({ size, interactive: isInteractive }),
      className
    ),
    title: citation, // Show full text on hover
    'aria-label': effectiveAriaLabel,
    ...props,
  };

  // Render as link if href is provided (href takes precedence over onClick)
  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...commonProps}>
        {displayText}
      </a>
    );
  }

  // Render as button if onClick is provided (without href)
  if (onClick) {
    return (
      <button type="button" onClick={onClick} {...commonProps}>
        {displayText}
      </button>
    );
  }

  // Render as static span (non-interactive)
  return <span {...commonProps}>{displayText}</span>;
}

export { sourceCitationVariants };
