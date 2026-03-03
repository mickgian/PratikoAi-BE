import { SuggestionResponse } from '@/lib/api/matching';

export type UrgencyLevel = 'critical' | 'high' | 'medium' | 'informational';
export type MatchType = 'NORMATIVA' | 'SCADENZA' | 'OPPORTUNITA';
export type MatchStatus = 'new' | 'reviewed' | 'handled' | 'ignored';

export interface NormativeMatch {
  id: string;
  title: string;
  type: MatchType;
  urgency: UrgencyLevel;
  relevanceScore: number;
  matchReason: string;
  actionRequired: string;
  deadline?: string;
  sourceLink?: string;
  sourceName?: string;
  publishDate: string;
  matchedAttributes: string[];
  status: MatchStatus;
}

export type FilterType = MatchType | 'all';
export type FilterUrgency = UrgencyLevel | 'all';
export type FilterStatus = MatchStatus | 'all';

/**
 * Derive MatchStatus from backend is_read/is_dismissed flags.
 */
function deriveStatus(s: SuggestionResponse): MatchStatus {
  if (s.is_dismissed) return 'ignored';
  if (s.is_read) return 'reviewed';
  return 'new';
}

/**
 * Derive UrgencyLevel from match_score.
 *   score >= 0.9  -> critical
 *   score >= 0.75 -> high
 *   score >= 0.5  -> medium
 *   otherwise     -> informational
 */
function deriveUrgency(score: number): UrgencyLevel {
  if (score >= 0.9) return 'critical';
  if (score >= 0.75) return 'high';
  if (score >= 0.5) return 'medium';
  return 'informational';
}

/**
 * Map a backend SuggestionResponse to the frontend NormativeMatch shape.
 */
export function mapSuggestionToMatch(s: SuggestionResponse): NormativeMatch {
  const title =
    s.suggestion_text.length > 80
      ? s.suggestion_text.slice(0, 80) + '...'
      : s.suggestion_text;

  // match_score comes as 0-1 from the backend
  const relevanceScore = Math.round(s.match_score * 100);

  return {
    id: s.id,
    title,
    type: 'NORMATIVA',
    urgency: deriveUrgency(s.match_score),
    relevanceScore,
    matchReason: s.suggestion_text,
    actionRequired: s.suggestion_text,
    publishDate: s.created_at,
    matchedAttributes:
      s.matched_client_ids.length > 0
        ? s.matched_client_ids.map(cid => `Cliente ID: ${cid}`)
        : [],
    status: deriveStatus(s),
  };
}
