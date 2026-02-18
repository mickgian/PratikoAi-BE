/**
 * ReasoningTrace Component (DEV-241)
 *
 * Expandable component for displaying AI reasoning traces in chat responses.
 * Shows the step-by-step logic used by PratikoAI to reach conclusions.
 *
 * Features:
 * - Expandable "Visualizza Ragionamento" (Show Reasoning) UI
 * - Displays tema_identificato, fonti_utilizzate, elementi_chiave, conclusione
 * - Performance optimized (<50ms render, 60fps animations)
 * - Italian localization for professional users
 * - PratikoAI color palette (blu-petrolio, grigio-tortora, avorio)
 * - Accessibility (ARIA labels, keyboard navigation)
 *
 * @example
 * ```tsx
 * <ReasoningTrace
 *   reasoning={{
 *     tema_identificato: "Regime forfettario",
 *     fonti_utilizzate: ["Legge 190/2014"],
 *     elementi_chiave: ["Aliquota ridotta 35%"],
 *     conclusione: "L'agevolazione è applicabile"
 *   }}
 * />
 * ```
 */

'use client';

import React, { memo, useState, useCallback } from 'react';
import {
  ChevronDownIcon,
  AlertTriangleIcon,
  BookOpenIcon,
  LightbulbIcon,
  CheckCircleIcon,
  FileTextIcon,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { SourceCitation } from '../ui/source-citation';

/**
 * Reasoning data structure from backend API (DEV-214)
 */
export interface ReasoningData {
  /** Main topic/theme identified */
  tema_identificato: string;
  /** List of normative sources used */
  fonti_utilizzate: string[];
  /** Key elements extracted from sources */
  elementi_chiave: string[];
  /** Final conclusion reached */
  conclusione: string;
  /** Optional confidence label (alta, media, bassa) */
  confidence_label?: string;
  /** Optional risk warning message */
  risk_warning?: string;
}

export interface ReasoningTraceProps {
  /** The reasoning data to display */
  reasoning: ReasoningData;
  /** Whether to start in expanded state */
  defaultExpanded?: boolean;
  /** Callback when expand/collapse state changes */
  onExpandChange?: (expanded: boolean) => void;
  /** Custom CSS classes */
  className?: string;
  /** Whether to render sources as SourceCitation components */
  useSourceCitations?: boolean;
}

/**
 * Get confidence badge styles based on level
 */
function getConfidenceBadgeStyles(level: string): string {
  switch (level.toLowerCase()) {
    case 'alta':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'media':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'bassa':
      return 'bg-red-100 text-red-800 border-red-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

/**
 * Section header component for reasoning sections
 */
const SectionHeader = memo(function SectionHeader({
  icon: Icon,
  title,
}: {
  icon: React.ElementType;
  title: string;
}) {
  return (
    <h4 className="flex items-center gap-2 text-sm font-semibold text-[#2A5D67] mb-2">
      <Icon className="w-4 h-4" />
      {title}
    </h4>
  );
});

/**
 * ReasoningTrace Component
 *
 * Displays an expandable reasoning trace for AI responses.
 * Optimized for performance and accessibility.
 */
export const ReasoningTrace = memo(function ReasoningTrace({
  reasoning,
  defaultExpanded = false,
  onExpandChange,
  className,
  useSourceCitations = false,
}: ReasoningTraceProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Handle toggle with callback
  const handleToggle = useCallback(() => {
    const newState = !isExpanded;
    setIsExpanded(newState);
    onExpandChange?.(newState);
  }, [isExpanded, onExpandChange]);

  // Return null if no reasoning data
  if (!reasoning || typeof reasoning !== 'object') {
    return null;
  }

  const {
    tema_identificato,
    fonti_utilizzate = [],
    elementi_chiave = [],
    conclusione,
    confidence_label,
    risk_warning,
  } = reasoning;

  // Don't render if no meaningful data
  if (!tema_identificato && !conclusione) {
    return null;
  }

  return (
    <div
      data-testid="reasoning-trace-container"
      className={cn(
        'rounded-lg border border-[#C4BDB4] bg-[#F8F5F1] overflow-hidden',
        'transition-all duration-200 ease-in-out',
        className
      )}
    >
      {/* Trigger Button */}
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-label={
          isExpanded ? 'Nascondi ragionamento' : 'Visualizza ragionamento'
        }
        className={cn(
          'w-full flex items-center justify-between gap-3 p-3',
          'text-sm font-medium text-[#2A5D67]',
          'hover:bg-[#C4BDB4]/20 transition-colors duration-150',
          'focus:outline-none focus:ring-2 focus:ring-[#2A5D67]/50 focus:ring-inset'
        )}
      >
        <span className="flex items-center gap-2">
          <BookOpenIcon className="w-4 h-4" />
          {isExpanded ? 'Nascondi Ragionamento' : 'Visualizza Ragionamento'}
        </span>
        <ChevronDownIcon
          className={cn(
            'w-4 h-4 transition-transform duration-200',
            isExpanded && 'rotate-180'
          )}
        />
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div
          className={cn(
            'px-4 pb-4 pt-2 space-y-4',
            'animate-in fade-in slide-in-from-top-2 duration-200'
          )}
        >
          {/* Confidence Badge */}
          {confidence_label && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#64748B]">Affidabilità:</span>
              <span
                className={cn(
                  'px-2 py-0.5 text-xs font-medium rounded-full border',
                  getConfidenceBadgeStyles(confidence_label)
                )}
              >
                {confidence_label.charAt(0).toUpperCase() +
                  confidence_label.slice(1)}
              </span>
            </div>
          )}

          {/* Risk Warning */}
          {risk_warning && (
            <div className="flex items-start gap-2 p-3 rounded-md bg-red-50 border border-red-200 text-red-800">
              <AlertTriangleIcon className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <p className="text-sm">{risk_warning}</p>
            </div>
          )}

          {/* Tema Identificato */}
          {tema_identificato && (
            <div>
              <SectionHeader icon={LightbulbIcon} title="Tema Identificato" />
              <p className="text-sm text-[#1E293B] pl-6">{tema_identificato}</p>
            </div>
          )}

          {/* Fonti Utilizzate */}
          {fonti_utilizzate.length > 0 ? (
            <div>
              <SectionHeader icon={FileTextIcon} title="Fonti Utilizzate" />
              <ul className="space-y-1.5 pl-6">
                {fonti_utilizzate.map((fonte, index) => (
                  <li key={index} className="text-sm text-[#1E293B]">
                    {useSourceCitations ? (
                      <SourceCitation citation={fonte} size="sm" />
                    ) : (
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#2A5D67]" />
                        {fonte}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div>
              <SectionHeader icon={FileTextIcon} title="Fonti Utilizzate" />
              <p className="text-sm text-[#64748B] italic pl-6">
                Nessuna fonte specificata
              </p>
            </div>
          )}

          {/* Elementi Chiave */}
          {elementi_chiave.length > 0 ? (
            <div>
              <SectionHeader icon={LightbulbIcon} title="Elementi Chiave" />
              <ul className="space-y-1.5 pl-6">
                {elementi_chiave.map((elemento, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 text-sm text-[#1E293B]"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2A5D67] mt-1.5 flex-shrink-0" />
                    {elemento}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div>
              <SectionHeader icon={LightbulbIcon} title="Elementi Chiave" />
              <p className="text-sm text-[#64748B] italic pl-6">
                Nessun elemento chiave identificato
              </p>
            </div>
          )}

          {/* Conclusione */}
          {conclusione && (
            <div className="pt-2 border-t border-[#C4BDB4]">
              <SectionHeader icon={CheckCircleIcon} title="Conclusione" />
              <p className="text-sm text-[#1E293B] pl-6 font-medium">
                {conclusione}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default ReasoningTrace;
