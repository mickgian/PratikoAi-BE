'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';

/**
 * Structured source from the backend API.
 * DEV-242: Parsed from INDICE DELLE FONTI table.
 */
export interface StructuredSource {
  numero: number;
  data: string;
  ente: string;
  tipo: string;
  riferimento: string;
  url?: string;
}

export interface SourcesIndexProps {
  /** List of structured sources to display */
  sources: StructuredSource[];
  /** Additional CSS classes */
  className?: string;
  /** Whether the component is collapsed by default */
  defaultCollapsed?: boolean;
}

/**
 * SourcesIndex Component
 *
 * DEV-242: Renders structured source citations in a clean, accessible table.
 * Replaces the raw ASCII table from LLM output with proper styling.
 *
 * Features:
 * - Collapsible section to save space
 * - Responsive design
 * - PratikoAI color palette
 * - Accessible table markup
 */
export function SourcesIndex({
  sources,
  className,
  defaultCollapsed = true,
}: SourcesIndexProps) {
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
      data-testid="sources-index"
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
        aria-controls="sources-index-content"
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Indice delle Fonti ({sources.length})
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
          id="sources-index-content"
          className="px-3 py-2"
          role="region"
          aria-label="Elenco delle fonti normative"
        >
          {/* Mobile: Card layout */}
          <div className="md:hidden space-y-2">
            {sources.map(source => (
              <SourceCard key={source.numero} source={source} />
            ))}
          </div>

          {/* Desktop: Table layout */}
          <div className="hidden md:block overflow-x-auto">
            <table
              className="w-full text-sm"
              aria-label="Indice delle fonti normative"
            >
              <thead>
                <tr className="text-left text-[#2A5D67] border-b border-[#C4BDB4]">
                  <th className="py-2 px-2 font-medium w-8">#</th>
                  <th className="py-2 px-2 font-medium w-24">Data</th>
                  <th className="py-2 px-2 font-medium w-20">Ente</th>
                  <th className="py-2 px-2 font-medium w-24">Tipo</th>
                  <th className="py-2 px-2 font-medium">Riferimento</th>
                </tr>
              </thead>
              <tbody>
                {sources.map(source => (
                  <tr
                    key={source.numero}
                    className="border-b border-[#C4BDB4]/50 last:border-0 hover:bg-[#F8F5F1]/50"
                  >
                    <td className="py-2 px-2 text-[#64748B]">
                      {source.numero}
                    </td>
                    <td className="py-2 px-2 text-[#1E293B]">
                      {source.data || '-'}
                    </td>
                    <td className="py-2 px-2 text-[#1E293B]">
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-[#2A5D67]/10 text-[#2A5D67]">
                        {source.ente || '-'}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-[#1E293B]">
                      {source.tipo || '-'}
                    </td>
                    <td className="py-2 px-2 text-[#1E293B]">
                      {source.url ? (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#2A5D67] hover:underline"
                        >
                          {source.riferimento}
                        </a>
                      ) : (
                        source.riferimento
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * SourceCard Component
 *
 * Mobile-friendly card view for a single source.
 */
function SourceCard({ source }: { source: StructuredSource }) {
  return (
    <div className={cn('p-2 rounded border border-[#C4BDB4]/50', 'bg-white')}>
      <div className="flex items-start gap-2">
        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#2A5D67]/10 text-[#2A5D67] text-xs font-medium flex items-center justify-center">
          {source.numero}
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-sm text-[#1E293B] font-medium truncate">
            {source.riferimento}
          </div>
          <div className="flex flex-wrap gap-1 mt-1">
            {source.ente && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#2A5D67]/10 text-[#2A5D67]">
                {source.ente}
              </span>
            )}
            {source.tipo && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#64748B]/10 text-[#64748B]">
                {source.tipo}
              </span>
            )}
            {source.data && (
              <span className="text-[10px] text-[#64748B]">{source.data}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SourcesIndex;
