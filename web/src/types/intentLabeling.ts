/**
 * Intent Labeling Types
 *
 * Types for the expert intent labeling system that allows SUPER_USER/ADMIN role users
 * to label low-confidence HF classifications for training data.
 *
 * Mirrors backend schemas in app/schemas/intent_labeling.py
 */

export const INTENT_LABELS = [
  'chitchat',
  'theoretical_definition',
  'technical_research',
  'calculator',
  'normative_reference',
] as const;

export type IntentLabel = (typeof INTENT_LABELS)[number];

export const INTENT_DISPLAY_NAMES: Record<IntentLabel, string> = {
  chitchat: 'Chiacchierata',
  theoretical_definition: 'Definizione Teorica',
  technical_research: 'Ricerca Tecnica',
  calculator: 'Calcolatore',
  normative_reference: 'Riferimento Normativo',
};

export const INTENT_COLORS: Record<IntentLabel, string> = {
  chitchat: '#6B7280',
  theoretical_definition: '#8B5CF6',
  technical_research: '#2A5D67',
  calculator: '#D4A574',
  normative_reference: '#d4183d',
};

/**
 * Single item in the labeling queue
 */
export interface QueueItem {
  id: string;
  query: string;
  predicted_intent: string;
  confidence: number;
  all_scores: Record<string, number>;
  expert_intent: string | null;
  skip_count: number;
  created_at: string;
}

/**
 * Paginated labeling queue response
 */
export interface QueueResponse {
  total_count: number;
  page: number;
  page_size: number;
  items: QueueItem[];
}

/**
 * Request payload for submitting an expert label
 */
export interface LabelSubmission {
  query_id: string;
  expert_intent: string;
  notes?: string;
}

/**
 * Response after submitting a label
 */
export interface LabeledQueryResponse {
  id: string;
  query: string;
  predicted_intent: string;
  expert_intent: string;
  labeled_by: number;
  labeled_at: string;
  labeling_notes: string | null;
}

/**
 * Response when skipping a query
 */
export interface SkipResponse {
  id: string;
  skip_count: number;
  message: string;
}

/**
 * Labeling progress statistics
 */
export interface LabelingStatsResponse {
  total_queries: number;
  labeled_queries: number;
  pending_queries: number;
  completion_percentage: number;
  labels_by_intent: Record<string, number>;
  new_since_export: number;
}
