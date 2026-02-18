/**
 * Model Comparison Types (DEV-256)
 *
 * Types for the multi-model LLM comparison feature that allows SUPER_USER role users
 * to compare responses from multiple LLM models and vote for the best one.
 */

/**
 * Response status for individual model responses
 */
export type ResponseStatus = 'success' | 'error' | 'timeout';

/**
 * Model provider identifiers
 */
export type ModelProvider = 'openai' | 'anthropic' | 'gemini' | 'mistral';

/**
 * Individual model response within a comparison
 */
export interface ModelResponseInfo {
  model_id: string;
  provider: ModelProvider;
  model_name: string;
  response_text: string;
  latency_ms: number;
  cost_eur: number | null;
  cost_usd: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  status: ResponseStatus;
  error_message?: string;
  trace_id: string;
}

/**
 * Request to run a comparison
 */
export interface ComparisonRequest {
  query: string;
  model_ids?: string[];
}

/**
 * Response from the current model (from main chat) to be reused in comparison
 */
export interface ExistingModelResponse {
  model_id: string;
  response_text: string;
  latency_ms: number;
  cost_eur: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  trace_id: string | null;
}

/**
 * Request for comparison with an existing response from main chat
 */
export interface ComparisonWithExistingRequest {
  query: string;
  existing_response: ExistingModelResponse;
  /** DEV-256: Full prompt sent to LLM including KB context, web results, etc. */
  enriched_prompt?: string;
  /** DEV-257: User-selected model IDs from chat. If undefined, uses default best models. */
  model_ids?: string[];
}

/**
 * Response from running a comparison
 */
export interface ComparisonResponse {
  batch_id: string;
  query: string;
  responses: ModelResponseInfo[];
  created_at: string;
}

/**
 * Request to submit a vote
 */
export interface VoteRequest {
  batch_id: string;
  winner_model_id: string;
  comment?: string;
}

/**
 * Response after submitting a vote
 */
export interface VoteResponse {
  success: boolean;
  message: string;
  winner_model_id: string;
  elo_changes: Record<string, number>;
}

/**
 * Available model for selection
 */
export interface AvailableModel {
  model_id: string;
  provider: ModelProvider;
  model_name: string;
  display_name: string;
  is_enabled: boolean;
  is_best: boolean;
  is_current: boolean;
  is_disabled: boolean;
  elo_rating: number;
  total_comparisons: number;
  wins: number;
}

/**
 * Response containing available models
 */
export interface AvailableModelsResponse {
  models: AvailableModel[];
}

/**
 * Model ranking in leaderboard
 */
export interface ModelRanking {
  rank: number;
  model_id: string;
  provider: ModelProvider;
  model_name: string;
  display_name: string;
  elo_rating: number;
  total_comparisons: number;
  wins: number;
  win_rate: number;
}

/**
 * Leaderboard response
 */
export interface LeaderboardResponse {
  rankings: ModelRanking[];
  last_updated: string;
}

/**
 * User comparison statistics
 */
export interface ComparisonStats {
  total_comparisons: number;
  total_votes: number;
  comparisons_this_week: number;
  votes_this_week: number;
  favorite_model: string | null;
  favorite_model_vote_count: number | null;
}

/**
 * Response containing user stats
 */
export interface ComparisonStatsResponse {
  stats: ComparisonStats;
}

/**
 * Request to update model preferences
 */
export interface ModelPreferencesRequest {
  enabled_model_ids: string[];
}

/**
 * Request to create a pending comparison from main chat
 */
export interface CreatePendingComparisonRequest {
  query: string;
  response: string;
  model_id: string;
  /** DEV-256: Full prompt sent to LLM including KB context, web results, etc. */
  enriched_prompt?: string;
  /** DEV-256: Response latency in milliseconds */
  latency_ms?: number;
  /** DEV-256: Estimated cost in EUR */
  cost_eur?: number;
  /** DEV-256: Number of input tokens */
  input_tokens?: number;
  /** DEV-256: Number of output tokens */
  output_tokens?: number;
  /** DEV-256: Langfuse trace ID */
  trace_id?: string;
}

/**
 * Response after creating a pending comparison
 */
export interface PendingComparisonResponse {
  pending_id: string;
}

/**
 * Data retrieved from a pending comparison
 */
export interface PendingComparisonData {
  query: string;
  response: string;
  model_id: string;
  /** DEV-256: Full prompt sent to LLM including KB context, web results, etc. */
  enriched_prompt?: string;
  /** DEV-256: Response latency in milliseconds */
  latency_ms?: number;
  /** DEV-256: Estimated cost in EUR */
  cost_eur?: number;
  /** DEV-256: Number of input tokens */
  input_tokens?: number;
  /** DEV-256: Number of output tokens */
  output_tokens?: number;
  /** DEV-256: Langfuse trace ID */
  trace_id?: string;
}
