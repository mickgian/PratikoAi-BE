'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';

/**
 * Web verification result from Brave Search API.
 * DEV-245: Post-LLM web verification to detect contradictions.
 */
export interface WebVerificationData {
  caveats?: string[];
  has_caveats?: boolean;
  web_sources_checked?: number;
  verification_performed?: boolean;
  brave_ai_summary?: string;
  synthesized_response?: string;
  has_synthesized_response?: boolean;
}

export interface WebVerificationProps {
  /** Web verification results */
  data: WebVerificationData;
  /** Additional CSS classes */
  className?: string;
  /** Whether the component is collapsed by default */
  defaultCollapsed?: boolean;
}

/**
 * WebVerification Component
 *
 * DEV-245: Renders web verification results from Brave Search.
 * Shows:
 * - Number of web sources checked
 * - Brave AI summary (if available)
 * - Caveats/contradictions found
 *
 * Features:
 * - Collapsible section to save space
 * - Responsive design
 * - PratikoAI color palette
 * - Accessible markup
 */
export function WebVerification({
  data,
  className,
  defaultCollapsed = false,
}: WebVerificationProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  // Don't render if no verification was performed
  if (!data || !data.verification_performed) {
    return null;
  }

  const sourcesChecked = data.web_sources_checked || 0;
  const hasSummary = data.brave_ai_summary || data.synthesized_response;
  const hasCaveats =
    data.has_caveats && data.caveats && data.caveats.length > 0;

  // Don't render if no useful data
  if (sourcesChecked === 0 && !hasSummary && !hasCaveats) {
    return null;
  }

  return (
    <div
      className={cn(
        'mt-4 border border-[#3B82F6]/30 rounded-lg overflow-hidden',
        'bg-[#EFF6FF]/50',
        className
      )}
      data-testid="web-verification"
    >
      {/* Header - Always visible */}
      <button
        type="button"
        onClick={() => setIsCollapsed(!isCollapsed)}
        className={cn(
          'w-full flex items-center justify-between',
          'px-3 py-2 text-left',
          'bg-[#EFF6FF] hover:bg-[#DBEAFE]',
          'transition-colors duration-200',
          'focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:ring-inset'
        )}
        aria-expanded={!isCollapsed}
        aria-controls="web-verification-content"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-[#1E40AF]">
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
              d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
            />
          </svg>
          Verifica Web ({sourcesChecked} fonti)
        </span>
        <svg
          className={cn(
            'w-4 h-4 text-[#1E40AF] transition-transform duration-200',
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
          id="web-verification-content"
          className="px-3 py-2 space-y-3"
          role="region"
          aria-label="Verifica fonti web"
        >
          {/* Brave AI Summary or Synthesized Response */}
          {hasSummary && (
            <div className="text-sm text-[#374151]">
              <p className="text-xs font-medium text-[#1E40AF] mb-1">
                Sintesi dal web:
              </p>
              <p className="leading-relaxed">
                {data.synthesized_response || data.brave_ai_summary}
              </p>
            </div>
          )}

          {/* Caveats/Contradictions */}
          {hasCaveats && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-[#DC2626] flex items-center gap-1">
                <svg
                  className="w-3 h-3"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                Avvertenze:
              </p>
              <ul className="space-y-1">
                {data.caveats!.map((caveat, index) => (
                  <li
                    key={index}
                    className="text-sm text-[#7F1D1D] bg-[#FEE2E2] px-2 py-1 rounded"
                  >
                    {caveat}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Status indicator when no issues found */}
          {!hasSummary && !hasCaveats && sourcesChecked > 0 && (
            <div className="flex items-center gap-2 text-sm text-[#059669]">
              <svg
                className="w-4 h-4"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              Nessuna contraddizione rilevata
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default WebVerification;
