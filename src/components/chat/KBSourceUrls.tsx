'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { SourceCitation } from '@/components/ui/source-citation';
import { isCitationUrl } from '@/config/citation-sources';

/**
 * KB source URL from backend KB retrieval.
 * DEV-244: Deterministic source URLs (independent of LLM output).
 */
export interface KBSourceUrl {
  title: string;
  url: string;
  type: string;
  date?: string; // Optional - may not be available for all sources
}

export interface KBSourceUrlsProps {
  /** List of KB source URLs to display */
  sources: KBSourceUrl[];
  /** Additional CSS classes */
  className?: string;
  /** Whether the component is collapsed by default */
  defaultCollapsed?: boolean;
}

/**
 * KBSourceUrls Component
 *
 * DEV-244: Renders deterministic KB source URLs.
 * These URLs come directly from KB retrieval, not from LLM parsing.
 * This ensures users ALWAYS see the source links, regardless of LLM output.
 *
 * Features:
 * - Collapsible section to save space
 * - Responsive design
 * - PratikoAI color palette
 * - Accessible markup
 */
export function KBSourceUrls({
  sources,
  className,
  defaultCollapsed = false,
}: KBSourceUrlsProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        'mt-4 border border-[#C4BDB4] rounded-lg overflow-hidden',
        'bg-[#F8F5F1]/50',
        className
      )}
      data-testid="kb-source-urls"
    >
      {/* Header - Always visible */}
      <button
        type="button"
        onClick={() => setIsCollapsed(!isCollapsed)}
        className={cn(
          'w-full flex items-center justify-between',
          'px-3 py-2 text-left',
          'bg-[#F8F5F1] hover:bg-[#F8F5F1]/80',
          'transition-colors duration-200',
          'focus:outline-none focus:ring-2 focus:ring-[#2A5D67] focus:ring-inset'
        )}
        aria-expanded={!isCollapsed}
        aria-controls="kb-source-urls-content"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-[#2A5D67]">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
            />
          </svg>
          Fonti ({sources.length})
        </span>
        <svg
          className={cn(
            'w-4 h-4 text-[#2A5D67] transition-transform duration-200',
            isCollapsed ? '' : 'rotate-180'
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Content - Collapsible */}
      {!isCollapsed && (
        <div
          id="kb-source-urls-content"
          className="px-3 py-2"
          role="region"
          aria-label="Fonti della knowledge base"
        >
          <ul className="space-y-2">
            {sources.map((source, index) => {
              // DEV-244: Use SourceCitation badge for institutional sources
              const isInstitutional = isCitationUrl(source.url);

              return (
                <li
                  key={`${source.url}-${index}`}
                  className="flex items-start gap-2"
                >
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#2A5D67]/10 text-[#2A5D67] text-xs font-medium flex items-center justify-center">
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    {isInstitutional ? (
                      // Institutional source: render with SourceCitation badge
                      <SourceCitation
                        citation={source.title}
                        href={source.url}
                        size="sm"
                        className="mb-0.5"
                      />
                    ) : (
                      // Non-institutional source: render as regular link
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-[#2A5D67] hover:underline font-medium"
                      >
                        {source.title}
                      </a>
                    )}
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {source.type && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#2A5D67]/10 text-[#2A5D67]">
                          {source.type}
                        </span>
                      )}
                      {source.date && (
                        <span className="text-[10px] text-[#64748B]">
                          {source.date}
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

export default KBSourceUrls;
