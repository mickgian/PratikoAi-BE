import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FeedbackButtons } from '../FeedbackButtons';
import type { Message } from '../../types/chat';
import * as expertFeedbackApi from '@/lib/api/expertFeedback';

// Mock the expert feedback API
jest.mock('@/lib/api/expertFeedback', () => ({
  submitFeedback: jest.fn(),
}));

describe('FeedbackButtons', () => {
  const mockMessage: Message = {
    id: 'msg-123',
    type: 'ai',
    content: 'Test AI response',
    timestamp: new Date().toISOString(),
  };

  const mockUserMessage: Message = {
    id: 'msg-user-1',
    type: 'user',
    content: 'What is the capital of France?',
    timestamp: new Date().toISOString(),
  };

  const mockSessionMessages: Message[] = [mockUserMessage, mockMessage];

  const mockSessionId = 'session-456';
  const mockOnFeedbackSubmitted = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders feedback buttons', () => {
    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    expect(screen.getByText(/Valuta questa risposta/i)).toBeInTheDocument();
    expect(screen.getByText('Corretta')).toBeInTheDocument();
    expect(screen.getByText('Incompleta')).toBeInTheDocument();
    expect(screen.getByText('Errata')).toBeInTheDocument();
  });

  it('submits feedback immediately for "Corretta" without details input', async () => {
    const mockSubmitFeedback = jest
      .spyOn(expertFeedbackApi, 'submitFeedback')
      .mockResolvedValue({
        id: 1,
        message: 'Feedback submitted successfully',
        feedback_type: 'correct',
      });

    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    const correttaButton = screen.getByText('Corretta');
    fireEvent.click(correttaButton);

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        expect.objectContaining({
          feedback_type: 'correct',
          query_text: mockUserMessage.content,
          original_answer: mockMessage.content,
          confidence_score: 0.8,
          additional_details: undefined,
        })
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(/Grazie per il tuo feedback!/i)
      ).toBeInTheDocument();
    });

    expect(mockOnFeedbackSubmitted).toHaveBeenCalled();
  });

  it('shows details input for "Incompleta" feedback', () => {
    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    const incompletaButton = screen.getByText('Incompleta');
    fireEvent.click(incompletaButton);

    expect(screen.getByTestId('feedback-details-input')).toBeInTheDocument();
    expect(screen.getByLabelText(/Dettagli aggiuntivi/i)).toBeInTheDocument();
    expect(screen.getByText('Invia Feedback')).toBeInTheDocument();
    expect(screen.getByText('Annulla')).toBeInTheDocument();
  });

  it('shows details input for "Errata" feedback', () => {
    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    const errataButton = screen.getByText('Errata');
    fireEvent.click(errataButton);

    expect(screen.getByTestId('feedback-details-input')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Spiega perché la risposta è errata/i)
    ).toBeInTheDocument();
  });

  it('validates required details for "Incompleta" feedback', async () => {
    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    // Click Incompleta button
    const incompletaButton = screen.getByText('Incompleta');
    fireEvent.click(incompletaButton);

    // Try to submit without entering details
    const submitButton = screen.getByText('Invia Feedback');

    // Submit button should be disabled when textarea is empty
    expect(submitButton).toBeDisabled();

    // Should NOT call API
    expect(expertFeedbackApi.submitFeedback).not.toHaveBeenCalled();
  });

  it('submits feedback with details for "Incompleta"', async () => {
    const mockSubmitFeedback = jest
      .spyOn(expertFeedbackApi, 'submitFeedback')
      .mockResolvedValue({
        id: 2,
        message: 'Feedback submitted successfully',
        feedback_type: 'incomplete',
      });

    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    // Click Incompleta button
    const incompletaButton = screen.getByText('Incompleta');
    fireEvent.click(incompletaButton);

    // Enter details
    const textarea = screen.getByLabelText(/Dettagli aggiuntivi/i);
    fireEvent.change(textarea, {
      target: { value: 'Missing tax calculation details' },
    });

    // Submit
    const submitButton = screen.getByText('Invia Feedback');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        expect.objectContaining({
          feedback_type: 'incomplete',
          query_text: mockUserMessage.content,
          original_answer: mockMessage.content,
          confidence_score: 0.8,
          additional_details: 'Missing tax calculation details',
        })
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(/Grazie per il tuo feedback!/i)
      ).toBeInTheDocument();
    });

    // Should show task creation message for incompleta/errata
    expect(
      screen.getByText(/È stato creato automaticamente un task/i)
    ).toBeInTheDocument();
  });

  it('submits feedback with details for "Errata"', async () => {
    const mockSubmitFeedback = jest
      .spyOn(expertFeedbackApi, 'submitFeedback')
      .mockResolvedValue({
        id: 3,
        message: 'Feedback submitted successfully',
        feedback_type: 'incorrect',
      });

    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    // Click Errata button
    const errataButton = screen.getByText('Errata');
    fireEvent.click(errataButton);

    // Enter details
    const textarea = screen.getByLabelText(/Dettagli aggiuntivi/i);
    fireEvent.change(textarea, {
      target: { value: 'The tax rate is incorrect' },
    });

    // Submit
    const submitButton = screen.getByText('Invia Feedback');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        expect.objectContaining({
          feedback_type: 'incorrect',
          query_text: mockUserMessage.content,
          original_answer: mockMessage.content,
          confidence_score: 0.8,
          additional_details: 'The tax rate is incorrect',
        })
      );
    });
  });

  it('handles cancel action', () => {
    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    // Click Incompleta button
    const incompletaButton = screen.getByText('Incompleta');
    fireEvent.click(incompletaButton);

    // Details input should be visible
    expect(screen.getByTestId('feedback-details-input')).toBeInTheDocument();

    // Click Cancel
    const cancelButton = screen.getByText('Annulla');
    fireEvent.click(cancelButton);

    // Details input should be hidden
    expect(
      screen.queryByTestId('feedback-details-input')
    ).not.toBeInTheDocument();

    // Should NOT call API
    expect(expertFeedbackApi.submitFeedback).not.toHaveBeenCalled();
  });

  it('handles API errors gracefully', async () => {
    const _mockSubmitFeedback = jest
      .spyOn(expertFeedbackApi, 'submitFeedback')
      .mockRejectedValue(new Error('Network error'));

    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    const correttaButton = screen.getByText('Corretta');
    fireEvent.click(correttaButton);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Network error');
    });

    // Should NOT call onFeedbackSubmitted on error
    expect(mockOnFeedbackSubmitted).not.toHaveBeenCalled();
  });

  it('shows readonly state for messages that already have feedback', () => {
    const messageWithFeedback: Message = {
      ...mockMessage,
      feedback: {
        rating: 'up',
        comment: 'Already provided',
      },
    };

    render(
      <FeedbackButtons
        message={messageWithFeedback}
        sessionId={mockSessionId}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    expect(screen.getByText('Feedback inviato')).toBeInTheDocument();
    expect(screen.queryByText('Corretta')).not.toBeInTheDocument();
    expect(screen.queryByText('Incompleta')).not.toBeInTheDocument();
    expect(screen.queryByText('Errata')).not.toBeInTheDocument();
  });

  it('disables buttons while submitting', async () => {
    // Mock a slow API call
    const mockSubmitFeedback = jest
      .spyOn(expertFeedbackApi, 'submitFeedback')
      .mockImplementation(
        () =>
          new Promise(resolve =>
            setTimeout(
              () =>
                resolve({
                  id: 1,
                  message: 'Feedback submitted successfully',
                  feedback_type: 'correct',
                }),
              100
            )
          )
      );

    render(
      <FeedbackButtons
        message={mockMessage}
        sessionId={mockSessionId}
        sessionMessages={mockSessionMessages}
        onFeedbackSubmitted={mockOnFeedbackSubmitted}
      />
    );

    const correttaButton = screen.getByRole('button', {
      name: /Risposta corretta/i,
    });
    fireEvent.click(correttaButton);

    // Button should be disabled during submission
    expect(correttaButton).toBeDisabled();

    // Wait for submission to complete
    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalled();
    });

    // After submission, success message should appear
    await waitFor(() => {
      expect(
        screen.getByText(/Grazie per il tuo feedback!/i)
      ).toBeInTheDocument();
    });
  });
});
