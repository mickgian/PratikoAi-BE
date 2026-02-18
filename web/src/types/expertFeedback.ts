/**
 * Expert Feedback Types
 *
 * Types for the expert feedback system that allows SUPER_USER role users
 * to provide feedback on AI responses for quality improvement.
 */

/**
 * Feedback type UI labels (Italian)
 * Used in the frontend button labels
 */
export type FeedbackTypeUI = 'corretta' | 'incompleta' | 'errata';

/**
 * Feedback type for backend API (English)
 * Maps to database enum values
 */
export type FeedbackType = 'correct' | 'incomplete' | 'incorrect';

/**
 * Expert feedback submission payload
 */
export interface ExpertFeedbackPayload {
  query_id: string;
  feedback_type: FeedbackType;
  query_text: string;
  original_answer: string;
  confidence_score?: number;
  time_spent_seconds?: number;
  additional_details?: string;
}

/**
 * Expert feedback submission response
 */
export interface ExpertFeedbackResponse {
  id: number;
  message: string;
  feedback_type: FeedbackType;
}

/**
 * User role enum (matches backend UserRole enum)
 */
export type UserRole = 'super_user' | 'regular_user' | 'expert' | 'admin';

/**
 * Expert profile information
 */
export interface ExpertProfile {
  user_id: number;
  email: string;
  role: UserRole;
  total_feedbacks: number;
  accepted_feedbacks: number;
  trust_score: number;
}

/**
 * Submit feedback request (alias for ExpertFeedbackPayload)
 */
export type SubmitFeedbackRequest = ExpertFeedbackPayload;

/**
 * Submit feedback response (alias for ExpertFeedbackResponse)
 */
export type SubmitFeedbackResponse = ExpertFeedbackResponse;

/**
 * Feedback history item for displaying past feedback
 */
export interface FeedbackHistoryItem {
  id: number;
  query_id: string;
  feedback_type: FeedbackType;
  query_text: string;
  original_answer: string;
  confidence_score: number;
  created_at: string;
  status: 'pending' | 'accepted' | 'rejected';
}
